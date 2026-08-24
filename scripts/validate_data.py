import json
import math
import re
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
NON_STANDARD_NUMBER = re.compile(
    r'(?<![A-Za-z0-9_])(?:NaN|Infinity|-Infinity)(?![A-Za-z0-9_])'
)


def reject_constant(value):
    raise ValueError(f'Non-standard JSON number: {value}')


def load_strict_json(path):
    raw = path.read_text(encoding='utf-8')
    match = NON_STANDARD_NUMBER.search(raw)
    if match:
        raise ValueError(f'{path}: found non-standard token {match.group(0)}')
    return json.loads(raw, parse_constant=reject_constant)


def validate_countries(countries):
    if not isinstance(countries, list):
        raise ValueError('countries.json must contain a list')
    if len(countries) != 217:
        raise ValueError(f'Expected 217 countries, found {len(countries)}')

    required_country = {
        'country_code', 'country_name', 'region', 'iso_numeric', 'years'
    }
    required_year = {
        'gdp_per_capita', 'school_enrollment_secondary',
        'enrollment_missing', 'enrollment_source',
        'human_development_index', 'life_expectancy', 'population'
    }
    codes = set()
    year_values = []
    record_count = 0

    for country in countries:
        if not required_country.issubset(country):
            raise ValueError('Country object is missing required fields')
        code = country['country_code']
        if code in codes:
            raise ValueError(f'Duplicate country code: {code}')
        codes.add(code)

        years = country['years']
        if not isinstance(years, dict):
            raise ValueError(f'{code}: years must be an object')
        for year, record in years.items():
            numeric_year = int(year)
            year_values.append(numeric_year)
            record_count += 1
            if not required_year.issubset(record):
                raise ValueError(f'{code} {year}: missing required fields')
            for key, value in record.items():
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f'{code} {year} {key}: non-finite value')

    if record_count != 4548:
        raise ValueError(f'Expected 4548 country-year records, found {record_count}')
    if min(year_values) != 2000 or max(year_values) != 2020:
        raise ValueError('Expected year coverage from 2000 through 2020')

    return record_count


def main():
    json_paths = sorted(DATA_DIR.glob('*.json'))
    if not json_paths:
        raise ValueError(f'No JSON files found in {DATA_DIR}')

    loaded = {path.name: load_strict_json(path) for path in json_paths}
    records = validate_countries(loaded['countries.json'])
    print(f'Validated {len(json_paths)} strict JSON files')
    print(f'countries.json: {len(loaded["countries.json"])} countries, {records} country-year records')


if __name__ == '__main__':
    main()
