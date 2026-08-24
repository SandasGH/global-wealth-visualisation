import argparse
import json
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser(
    description='Build the derived visualisation dataset from coursework CSV inputs.'
)
parser.add_argument('--source-dir', type=Path, default=Path('.'))
parser.add_argument('--output', type=Path, default=Path('data/countries.json'))
args = parser.parse_args()

# ── 1. LOAD ───────────────────────────────────────────────────────────────────
# Primary source: Global Development Indicators (GDP, HDI, life expectancy, population, region)
df = pd.read_csv(args.source_dir / 'Global_Development_Indicators_2000_2020.csv')
print(f"Loaded {len(df)} rows from Global_Development_Indicators_2000_2020.csv")

cols = [
    "year", "country_code", "country_name", "region",
    "gdp_per_capita", "school_enrollment_secondary",
    "human_development_index", "life_expectancy", "population"
]
df = df[cols].copy()

# Secondary source: world-education-data.csv (primary enrollment source)
edu = pd.read_csv(args.source_dir / 'world-education-data.csv')
print(f"Loaded {len(edu)} rows from world-education-data.csv")
edu = edu[["country_code", "year", "school_enrol_secondary_pct"]].copy()

# ── 2. FILTER TO VALID ISO3 CODES ─────────────────────────────────────────────
iso3_mask = df["country_code"].str.match(r"^[A-Z]{3}$", na=False)
print(f"Dropping {(~iso3_mask).sum()} rows with non-ISO3 codes")
df = df[iso3_mask].copy()

# ── 3. FILTER YEARS ───────────────────────────────────────────────────────────
df  = df[df["year"].between(2000, 2020)].copy()
edu = edu[edu["year"].between(2000, 2020)].copy()
print(f"After year filter: {len(df)} rows (GDI), {len(edu)} rows (world-education)")

# ── 4. MERGE ENROLLMENT DATA ──────────────────────────────────────────────────
df = df.merge(edu, on=["country_code", "year"], how="left")
print(f"After merge: {len(df)} rows, {df['country_code'].nunique()} unique country codes")
matched = df["school_enrol_secondary_pct"].notna().sum()
print(f"Rows matched with world-education enrollment data: {matched}")

# ── 5. HANDLE MISSING REGION ──────────────────────────────────────────────────
print(f"Rows with missing region: {df['region'].isna().sum()}")
df["region"] = df["region"].fillna("Unknown")

# ── 6. RESOLVE ENROLLMENT WITH SOURCE TRACKING ────────────────────────────────
# Priority: world-education-data > GDI fallback > missing
def resolve_enrollment(row):
    if pd.notna(row["school_enrol_secondary_pct"]):
        return row["school_enrol_secondary_pct"], "provided", False
    elif pd.notna(row["school_enrollment_secondary"]):
        return row["school_enrollment_secondary"], "supplementary", False
    else:
        return None, "missing", True

resolved = df.apply(resolve_enrollment, axis=1, result_type="expand")
df["school_enrollment_secondary"] = resolved[0]
df["enrollment_source"]           = resolved[1]
df["enrollment_missing"]          = resolved[2]

n_provided      = (df["enrollment_source"] == "provided").sum()
n_supplementary = (df["enrollment_source"] == "supplementary").sum()
n_missing       = (df["enrollment_source"] == "missing").sum()
print(f"Enrollment source breakdown:")
print(f"  provided (world-education):  {n_provided}")
print(f"  supplementary (GDI fallback): {n_supplementary}")
print(f"  missing (both null):          {n_missing}")

# ── 6. ISO3 → NUMERIC LOOKUP ──────────────────────────────────────────────────
iso3_to_numeric = {
    "AFG":4,"ALB":8,"DZA":12,"AND":20,"AGO":24,"ATG":28,"ARG":32,"ARM":51,
    "AUS":36,"AUT":40,"AZE":31,"BHS":44,"BHR":48,"BGD":50,"BRB":52,"BLR":112,
    "BEL":56,"BLZ":84,"BEN":204,"BTN":64,"BOL":68,"BIH":70,"BWA":72,"BRA":76,
    "BRN":96,"BGR":100,"BFA":854,"BDI":108,"CPV":132,"KHM":116,"CMR":120,
    "CAN":124,"CAF":140,"TCD":148,"CHL":152,"CHN":156,"COL":170,"COM":174,
    "COD":180,"COG":178,"CRI":188,"CIV":384,"HRV":191,"CUB":192,"CYP":196,
    "CZE":203,"DNK":208,"DJI":262,"DOM":214,"ECU":218,"EGY":818,"SLV":222,
    "GNQ":226,"ERI":232,"EST":233,"SWZ":748,"ETH":231,"FJI":242,"FIN":246,
    "FRA":250,"GAB":266,"GMB":270,"GEO":268,"DEU":276,"GHA":288,"GRC":300,
    "GTM":320,"GIN":324,"GNB":624,"GUY":328,"HTI":332,"HND":340,"HUN":348,
    "ISL":352,"IND":356,"IDN":360,"IRN":364,"IRQ":368,"IRL":372,"ISR":376,
    "ITA":380,"JAM":388,"JPN":392,"JOR":400,"KAZ":398,"KEN":404,"KIR":296,
    "PRK":408,"KOR":410,"KWT":414,"KGZ":417,"LAO":418,"LVA":428,"LBN":422,
    "LSO":426,"LBR":430,"LBY":434,"LIE":438,"LTU":440,"LUX":442,"MDG":450,
    "MWI":454,"MYS":458,"MDV":462,"MLI":466,"MLT":470,"MRT":478,"MUS":480,
    "MEX":484,"MDA":498,"MCO":492,"MNG":496,"MNE":499,"MAR":504,"MOZ":508,
    "MMR":104,"NAM":516,"NPL":524,"NLD":528,"NZL":554,"NIC":558,"NER":562,
    "NGA":566,"MKD":807,"NOR":578,"OMN":512,"PAK":586,"PAN":591,"PNG":598,
    "PRY":600,"PER":604,"PHL":608,"POL":616,"PRT":620,"QAT":634,"ROU":642,
    "RUS":643,"RWA":646,"WSM":882,"STP":678,"SAU":682,"SEN":686,"SRB":688,
    "SLE":694,"SGP":702,"SVK":703,"SVN":705,"SLB":90,"SOM":706,"ZAF":710,
    "SSD":728,"ESP":724,"LKA":144,"SDN":729,"SUR":740,"SWE":752,"CHE":756,
    "SYR":760,"TWN":158,"TJK":762,"TZA":834,"THA":764,"TLS":626,"TGO":768,
    "TON":776,"TTO":780,"TUN":788,"TUR":792,"TKM":795,"UGA":800,"UKR":804,
    "ARE":784,"GBR":826,"USA":840,"URY":858,"UZB":860,"VUT":548,"VEN":862,
    "VNM":704,"YEM":887,"ZMB":894,"ZWE":716,
    # Small territories present in the dataset
    "PSE":275,"BMU":60,"SYC":690,"ASM":16,"FSM":583,"GUM":316,"HKG":344,
    "MAC":446,"MHL":584,"MNP":580,"NCL":540,"NRU":520,"PLW":585,"PYF":258,
    "TUV":798,"CHI":832,"FRO":234,"GIB":292,"GRL":304,"IMN":833,"SMR":674,
    "XKX":926,"ABW":533,"CUW":531,"CYM":136,"DMA":212,"GRD":308,"KNA":659,
    "LCA":662,"MAF":663,"PRI":630,"SXM":534,"TCA":796,"VCT":670,"VGB":92,
    "VIR":850,
}

df["iso_numeric"] = df["country_code"].map(iso3_to_numeric)

# ── 7. DROP ROWS STILL UNMAPPED (regional aggregates) ────────────────────────
before = len(df)
df = df[df["iso_numeric"].notna()].copy()
print(f"Dropped {before - len(df)} rows that are regional aggregates (no map geometry)")
print(f"Remaining: {len(df)} rows, {df['country_code'].nunique()} countries")

# ── 8. ROUND FLOATS ───────────────────────────────────────────────────────────
df["gdp_per_capita"]              = df["gdp_per_capita"].round(2)
df["school_enrollment_secondary"] = df["school_enrollment_secondary"].round(2)
df["human_development_index"]     = df["human_development_index"].round(4)
df["life_expectancy"]             = df["life_expectancy"].round(2)
df["iso_numeric"]                 = df["iso_numeric"].astype(int)

# ── 9. BUILD NESTED JSON ──────────────────────────────────────────────────────
df = df.astype(object).where(pd.notnull(df), None)

nested = {}
for _, row in df.iterrows():
    code = row["country_code"]
    if code not in nested:
        nested[code] = {
            "country_code": code,
            "country_name": row["country_name"],
            "region":       row["region"],
            "iso_numeric":  int(row["iso_numeric"]),
            "years": {}
        }
    nested[code]["years"][int(row["year"])] = {
        "gdp_per_capita":              row["gdp_per_capita"],
        "school_enrollment_secondary": row["school_enrollment_secondary"],
        "enrollment_missing":          bool(row["enrollment_missing"]),
        "enrollment_source":           row["enrollment_source"],
        "human_development_index":     row["human_development_index"],
        "life_expectancy":             row["life_expectancy"],
        "population":                  row["population"],
    }

output = list(nested.values())

# ── 10. WRITE OUTPUT ──────────────────────────────────────────────────────────
# Serialise in memory first so allow_nan=False fails before touching the output.
payload = json.dumps(output, separators=(',', ':'), allow_nan=False)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(payload + '\n', encoding='utf-8')

print(f"\nWritten {len(output)} country objects to {args.output}")
sample = output[0]
print(f"Sample: {sample['country_code']} | {sample['country_name']} | region: {sample['region']} | iso_numeric: {sample['iso_numeric']}")
print(f"Years available: {sorted(sample['years'].keys())}")
print("\nDone.")
