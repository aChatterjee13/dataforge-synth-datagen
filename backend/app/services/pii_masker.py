"""
PII Detection & Masking Service - Detects and anonymizes personally identifiable information.
Uses LLM-first detection (sends column samples to GPT for classification) with regex fallback.
"""

import re
import hashlib
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Canonical PII types the system understands
# Direct PII: uniquely identifies an individual on its own
DIRECT_PII_TYPES = {
    'email', 'ssn', 'phone', 'credit_card', 'ip', 'name',
    'address', 'date_of_birth', 'passport', 'drivers_license',
    'bank_account', 'medical_record', 'national_id', 'tax_id',
    'username', 'password', 'biometric', 'license_plate',
    'geolocation', 'ethnicity', 'religion', 'political_opinion',
}

# Indirect PII (quasi-identifiers): can re-identify when combined
INDIRECT_PII_TYPES = {
    'age', 'gender', 'salary', 'occupation', 'marital_status',
    'education', 'nationality', 'employee_id', 'device_id',
    'vehicle_vin', 'zip_code',
}

KNOWN_PII_TYPES = DIRECT_PII_TYPES | INDIRECT_PII_TYPES

STRATEGY_MAP = {
    # Direct PII
    'email': 'synthetic',
    'ssn': 'hash',
    'phone': 'synthetic',
    'credit_card': 'hash',
    'ip': 'synthetic',
    'name': 'synthetic',
    'address': 'synthetic',
    'date_of_birth': 'synthetic',
    'passport': 'hash',
    'drivers_license': 'hash',
    'bank_account': 'hash',
    'medical_record': 'hash',
    'national_id': 'hash',
    'tax_id': 'hash',
    'username': 'synthetic',
    'password': 'redact',
    'biometric': 'redact',
    'license_plate': 'hash',
    'geolocation': 'generalize',
    'ethnicity': 'redact',
    'religion': 'redact',
    'political_opinion': 'redact',
    # Indirect PII (quasi-identifiers)
    'age': 'generalize',
    'gender': 'generalize',
    'salary': 'generalize',
    'occupation': 'generalize',
    'marital_status': 'generalize',
    'education': 'generalize',
    'nationality': 'generalize',
    'employee_id': 'hash',
    'device_id': 'hash',
    'vehicle_vin': 'hash',
    'zip_code': 'generalize',
}


class PIIDetector:
    """Detect PII columns using LLM-first approach with regex fallback."""

    # Regex patterns for common PII types (used as fallback)
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'ssn': re.compile(r'^\d{3}-?\d{2}-?\d{4}$'),
        'phone': re.compile(r'^[\+]?[(]?\d{1,4}[)]?[-\s.]?\d{1,4}[-\s.]?\d{1,9}$'),
        'credit_card': re.compile(r'^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$'),
        'ip': re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'),
    }

    NAME_HINTS = {
        # Direct PII
        'name': ['name', 'first_name', 'last_name', 'full_name', 'firstname', 'lastname',
                 'fname', 'lname', 'customer_name', 'user_name', 'username', 'patient_name'],
        'email': ['email', 'e_mail', 'email_address', 'mail', 'user_email'],
        'phone': ['phone', 'telephone', 'tel', 'mobile', 'cell', 'phone_number',
                  'contact_number', 'phone_no'],
        'ssn': ['ssn', 'social_security', 'social_security_number', 'sin'],
        'address': ['address', 'street', 'street_address', 'addr', 'home_address',
                    'mailing_address'],
        'credit_card': ['credit_card', 'card_number', 'cc_number', 'card_no', 'ccn'],
        'ip': ['ip', 'ip_address', 'ipaddress', 'source_ip', 'dest_ip', 'client_ip'],
        'date_of_birth': ['dob', 'date_of_birth', 'birth_date', 'birthday', 'birthdate'],
        # Indirect PII (quasi-identifiers)
        'age': ['age', 'customer_age', 'patient_age', 'user_age'],
        'gender': ['gender', 'sex', 'biological_sex'],
        'salary': ['salary', 'income', 'compensation', 'annual_salary', 'wage',
                   'pay', 'earnings', 'annual_income'],
        'occupation': ['occupation', 'job_title', 'job', 'position', 'role', 'title',
                       'profession', 'designation'],
        'marital_status': ['marital_status', 'marital', 'marriage_status', 'relationship_status'],
        'education': ['education', 'degree', 'education_level', 'qualification',
                      'highest_education', 'school'],
        'nationality': ['nationality', 'country_of_origin', 'citizenship', 'country_of_birth'],
        'employee_id': ['employee_id', 'emp_id', 'staff_id', 'worker_id', 'personnel_id',
                        'student_id', 'member_id', 'badge_id'],
        'device_id': ['device_id', 'mac_address', 'imei', 'serial_number', 'hardware_id',
                      'uuid', 'device_uuid'],
        'vehicle_vin': ['vin', 'vehicle_vin', 'vehicle_identification', 'chassis_number'],
        'zip_code': ['zip', 'zipcode', 'zip_code', 'postal_code', 'postcode', 'pin_code'],
    }

    @staticmethod
    def detect_pii_columns(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect PII columns using LLM-first approach.
        Sends all column names + sample values to the LLM for classification.
        Falls back to regex if LLM is unavailable.
        """
        try:
            return PIIDetector._detect_with_llm(df)
        except Exception as e:
            logger.warning(f"LLM PII detection failed ({e}), falling back to regex")
            return PIIDetector._detect_with_regex(df)

    @staticmethod
    def _detect_with_llm(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Use LLM to classify every column for PII."""
        from app.services.llm_client import LLMClient

        llm = LLMClient()

        # Build column summaries for the LLM
        column_summaries = []
        for col in df.columns:
            series = df[col].dropna().astype(str)
            if len(series) == 0:
                continue
            samples = series.head(10).tolist()
            unique_count = series.nunique()
            column_summaries.append({
                'column_name': col,
                'dtype': str(df[col].dtype),
                'sample_values': samples,
                'unique_values': int(unique_count),
                'total_non_null': int(len(series)),
            })

        if not column_summaries:
            return []

        system_prompt = """You are a PII (Personally Identifiable Information) detection expert.
Analyze the provided dataset columns and classify each one for PII risk.

Detect BOTH direct PII and indirect PII (quasi-identifiers):

DIRECT PII (uniquely identifies a person):
email, ssn, phone, credit_card, ip, name, address, date_of_birth, passport, drivers_license,
bank_account, medical_record, national_id, tax_id, username, password, biometric,
license_plate, geolocation, ethnicity, religion, political_opinion

INDIRECT PII (quasi-identifiers that can re-identify when combined):
age, gender, salary, occupation, marital_status, education, nationality,
employee_id, device_id, vehicle_vin, zip_code

Consider:
- Column names (even abbreviated or coded)
- Sample value patterns and content
- Context clues from surrounding columns
- Free-text fields that may contain embedded PII
- Quasi-identifiers that could re-identify individuals when combined (e.g., age + zip + gender)

For the "pii_category" field:
- "direct": Column alone can identify a person (name, email, SSN, etc.)
- "indirect": Column is a quasi-identifier that aids re-identification when combined with others

For confidence scoring:
- 0.95+: Clear PII (e.g., column named "email" with email addresses)
- 0.80-0.94: Strong indicators (e.g., column named "contact" with phone numbers)
- 0.60-0.79: Moderate indicators (e.g., age column, zip code, gender)
- Below 0.60: Weak indicators (only flag if the data clearly looks like PII)

Respond with JSON only. Use this exact schema:
{
  "detections": [
    {
      "column_name": "exact column name from input",
      "pii_type": "type from the lists above",
      "pii_category": "direct or indirect",
      "confidence": 0.95,
      "reasoning": "brief explanation of why this is PII"
    }
  ]
}

Include BOTH direct PII and indirect quasi-identifier columns. Omit truly non-PII columns (like order_id, amount, timestamps)."""

        user_prompt = f"""Analyze these {len(column_summaries)} columns for PII:

{json.dumps(column_summaries, indent=2, default=str)}"""

        result = llm.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            expect_json=True,
            retry_count=2,
        )

        detections = []
        llm_detections = result.get('detections', [])

        for det in llm_detections:
            col_name = det.get('column_name', '')
            pii_type = det.get('pii_type', '').lower().strip()
            confidence = float(det.get('confidence', 0.0))

            # Validate column exists in the dataframe
            if col_name not in df.columns:
                logger.warning(f"LLM returned unknown column: {col_name}")
                continue

            # Normalize PII type
            if pii_type not in KNOWN_PII_TYPES:
                # Try to map common LLM variations
                type_aliases = {
                    'social_security': 'ssn',
                    'social_security_number': 'ssn',
                    'telephone': 'phone',
                    'mobile': 'phone',
                    'cell_phone': 'phone',
                    'full_name': 'name',
                    'first_name': 'name',
                    'last_name': 'name',
                    'person_name': 'name',
                    'credit_card_number': 'credit_card',
                    'card_number': 'credit_card',
                    'ip_address': 'ip',
                    'ipv4': 'ip',
                    'date_birth': 'date_of_birth',
                    'dob': 'date_of_birth',
                    'birthday': 'date_of_birth',
                    'street_address': 'address',
                    'home_address': 'address',
                    'mailing_address': 'address',
                    'passport_number': 'passport',
                    'driver_license': 'drivers_license',
                    'bank_account_number': 'bank_account',
                    'iban': 'bank_account',
                    'gps': 'geolocation',
                    'coordinates': 'geolocation',
                    'latitude': 'geolocation',
                    'longitude': 'geolocation',
                    # Indirect PII aliases
                    'sex': 'gender',
                    'income': 'salary',
                    'annual_salary': 'salary',
                    'compensation': 'salary',
                    'wage': 'salary',
                    'earnings': 'salary',
                    'job_title': 'occupation',
                    'job': 'occupation',
                    'position': 'occupation',
                    'profession': 'occupation',
                    'zipcode': 'zip_code',
                    'postal_code': 'zip_code',
                    'postcode': 'zip_code',
                    'marriage_status': 'marital_status',
                    'degree': 'education',
                    'education_level': 'education',
                    'qualification': 'education',
                    'citizenship': 'nationality',
                    'country_of_origin': 'nationality',
                    'emp_id': 'employee_id',
                    'staff_id': 'employee_id',
                    'worker_id': 'employee_id',
                    'student_id': 'employee_id',
                    'member_id': 'employee_id',
                    'mac_address': 'device_id',
                    'imei': 'device_id',
                    'serial_number': 'device_id',
                    'vin': 'vehicle_vin',
                    'chassis_number': 'vehicle_vin',
                }
                pii_type = type_aliases.get(pii_type, pii_type)

            if pii_type not in KNOWN_PII_TYPES:
                logger.warning(f"LLM returned unknown PII type '{pii_type}' for column '{col_name}', skipping")
                continue

            # Determine category
            pii_category = det.get('pii_category', '').lower().strip()
            if pii_category not in ('direct', 'indirect'):
                pii_category = 'indirect' if pii_type in INDIRECT_PII_TYPES else 'direct'

            # Clamp confidence
            confidence = max(0.0, min(1.0, confidence))

            series = df[col_name].dropna().astype(str)
            sample = series.head(5).tolist() if len(series) > 0 else []

            detections.append({
                'column_name': col_name,
                'pii_type': pii_type,
                'pii_category': pii_category,
                'confidence': round(confidence, 2),
                'sample_values': sample[:3],
                'suggested_strategy': STRATEGY_MAP.get(pii_type, 'redact'),
            })

        logger.info(f"LLM detected {len(detections)} PII columns out of {len(df.columns)} total")
        return detections

    @staticmethod
    def _detect_with_regex(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Fallback: detect PII columns using regex patterns and column name heuristics."""
        detections = []

        for col in df.columns:
            col_lower = col.lower().strip().replace(' ', '_')
            series = df[col].dropna().astype(str)

            if len(series) == 0:
                continue

            sample = series.head(5).tolist()
            best_type = None
            best_confidence = 0.0

            # Check column name heuristics first
            for pii_type, hints in PIIDetector.NAME_HINTS.items():
                if col_lower in hints or any(h in col_lower for h in hints):
                    best_type = pii_type
                    best_confidence = 0.8
                    break

            # Check regex patterns against sample values
            test_sample = series.head(100)
            for pii_type, pattern in PIIDetector.PATTERNS.items():
                match_count = test_sample.apply(lambda v: bool(pattern.match(str(v).strip()))).sum()
                match_rate = match_count / len(test_sample) if len(test_sample) > 0 else 0

                if match_rate > 0.5 and match_rate > best_confidence:
                    best_type = pii_type
                    best_confidence = min(match_rate, 1.0)

            if best_type:
                pii_category = 'indirect' if best_type in INDIRECT_PII_TYPES else 'direct'
                detections.append({
                    'column_name': col,
                    'pii_type': best_type,
                    'pii_category': pii_category,
                    'confidence': round(best_confidence, 2),
                    'sample_values': sample[:3],
                    'suggested_strategy': STRATEGY_MAP.get(best_type, 'redact'),
                })

        return detections

    @staticmethod
    def get_non_pii_columns(df: pd.DataFrame, pii_columns: List[str]) -> List[str]:
        """Return columns that are not PII."""
        return [c for c in df.columns if c not in pii_columns]


class PIIMasker:
    """Mask PII columns using various strategies."""

    @staticmethod
    def mask_column(series: pd.Series, pii_type: str, strategy: str) -> pd.Series:
        """Mask a single column based on PII type and strategy."""
        from faker import Faker
        fake = Faker()

        if strategy == 'synthetic':
            return PIIMasker._synthetic_replace(series, pii_type, fake)
        elif strategy == 'hash':
            return PIIMasker._hash_replace(series, pii_type)
        elif strategy == 'redact':
            return PIIMasker._redact_replace(series, pii_type)
        elif strategy == 'generalize':
            return PIIMasker._generalize_replace(series, pii_type)
        else:
            return PIIMasker._redact_replace(series, pii_type)

    # Common date format patterns for auto-detection
    _DATE_FORMATS = [
        ('%Y-%m-%d',       r'^\d{4}-\d{2}-\d{2}$'),              # 1985-03-15
        ('%m/%d/%Y',       r'^\d{1,2}/\d{1,2}/\d{4}$'),          # 03/15/1985
        ('%d/%m/%Y',       None),                                  # handled via heuristic
        ('%m-%d-%Y',       r'^\d{1,2}-\d{1,2}-\d{4}$'),          # 03-15-1985
        ('%d-%b-%Y',       r'^\d{1,2}-[A-Za-z]{3}-\d{4}$'),      # 15-Mar-1985
        ('%B %d, %Y',      r'^[A-Za-z]+ \d{1,2}, \d{4}$'),       # March 15, 1985
        ('%b %d, %Y',      r'^[A-Za-z]{3} \d{1,2}, \d{4}$'),     # Mar 15, 1985
        ('%d %B %Y',       r'^\d{1,2} [A-Za-z]+ \d{4}$'),        # 15 March 1985
        ('%Y/%m/%d',       r'^\d{4}/\d{2}/\d{2}$'),              # 1985/03/15
        ('%d.%m.%Y',       r'^\d{1,2}\.\d{1,2}\.\d{4}$'),        # 15.03.1985
        ('%m.%d.%Y',       None),                                  # handled via heuristic
        ('%Y%m%d',         r'^\d{8}$'),                            # 19850315
    ]

    @staticmethod
    def _detect_date_format(series: pd.Series) -> str:
        """Detect the most common date format in a series."""
        import re as _re

        sample = series.dropna().astype(str).head(50)
        if len(sample) == 0:
            return '%Y-%m-%d'

        # Score each format by how many sample values it can parse
        best_fmt = '%Y-%m-%d'
        best_score = 0

        for fmt, pattern in PIIMasker._DATE_FORMATS:
            if pattern is not None:
                regex = _re.compile(pattern)
                match_count = sum(1 for v in sample if regex.match(v.strip()))
                if match_count > best_score:
                    # Verify parsing actually works
                    parse_ok = 0
                    for v in sample:
                        try:
                            datetime.strptime(v.strip(), fmt)
                            parse_ok += 1
                        except ValueError:
                            pass
                    if parse_ok > best_score:
                        best_score = parse_ok
                        best_fmt = fmt

        # If no regex matched well, try brute-force parsing with all formats
        if best_score < len(sample) * 0.3:
            for fmt, _ in PIIMasker._DATE_FORMATS:
                parse_ok = 0
                for v in sample:
                    try:
                        datetime.strptime(v.strip(), fmt)
                        parse_ok += 1
                    except ValueError:
                        pass
                if parse_ok > best_score:
                    best_score = parse_ok
                    best_fmt = fmt

        return best_fmt

    @staticmethod
    def _synthetic_replace(series: pd.Series, pii_type: str, fake) -> pd.Series:
        """Replace with realistic synthetic data using Faker."""
        import random

        # For date_of_birth: detect original format, then generate dates in that format
        if pii_type == 'date_of_birth':
            date_fmt = PIIMasker._detect_date_format(series)

            def _gen_dob(original_value):
                if pd.isna(original_value):
                    return original_value
                # Try to parse the original date to determine a realistic age range
                original_str = str(original_value).strip()
                parsed = None
                try:
                    parsed = datetime.strptime(original_str, date_fmt)
                except ValueError:
                    # Fallback: let pandas parse it
                    try:
                        parsed = pd.to_datetime(original_str).to_pydatetime()
                    except Exception:
                        pass

                if parsed is not None:
                    # Shift by a random offset (±30 to ±730 days) to preserve
                    # rough age distribution while anonymizing
                    offset_days = random.randint(30, 730) * random.choice([-1, 1])
                    from datetime import timedelta
                    new_date = parsed + timedelta(days=offset_days)
                    # Clamp to reasonable range (1930 – 2010)
                    if new_date.year < 1930:
                        new_date = new_date.replace(year=1930 + random.randint(0, 10))
                    elif new_date.year > 2010:
                        new_date = new_date.replace(year=2000 + random.randint(0, 10))
                    try:
                        return new_date.strftime(date_fmt)
                    except ValueError:
                        return new_date.strftime('%Y-%m-%d')
                else:
                    # Cannot parse original — generate a fresh date in detected format
                    new_date = fake.date_of_birth(minimum_age=18, maximum_age=90)
                    try:
                        return new_date.strftime(date_fmt)
                    except ValueError:
                        return new_date.isoformat()

            return series.apply(_gen_dob)

        generators = {
            # Direct PII
            'email': lambda: fake.email(),
            'phone': lambda: fake.numerify('###-###-####'),
            'name': lambda: fake.name(),
            'address': lambda: fake.street_address() + ', ' + fake.city() + ', ' + fake.state_abbr() + ' ' + fake.zipcode(),
            'ssn': lambda: fake.numerify('###-##-####'),
            'credit_card': lambda: fake.credit_card_number(card_type='visa16'),
            'ip': lambda: fake.ipv4(),
            'username': lambda: fake.user_name(),
            'passport': lambda: fake.bothify('??######').upper(),
            'drivers_license': lambda: fake.bothify('?-########').upper(),
            'bank_account': lambda: fake.numerify('####-####-####-####'),
            'medical_record': lambda: 'MRN-' + fake.numerify('#######'),
            'national_id': lambda: fake.numerify('###-##-####'),
            'tax_id': lambda: fake.numerify('##-#######'),
            'license_plate': lambda: fake.license_plate(),
            'geolocation': lambda: f"{fake.latitude()}, {fake.longitude()}",
            # Indirect PII (quasi-identifiers)
            'age': lambda: str(random.randint(18, 85)),
            'gender': lambda: random.choice(['Male', 'Female', 'Non-binary']),
            'salary': lambda: str(round(random.uniform(30000, 200000), 2)),
            'occupation': lambda: fake.job(),
            'marital_status': lambda: random.choice(['Single', 'Married', 'Divorced', 'Widowed']),
            'education': lambda: random.choice(['High School', 'Associate', 'Bachelor', 'Master', 'Doctorate']),
            'nationality': lambda: fake.country(),
            'employee_id': lambda: 'EMP-' + fake.numerify('######'),
            'device_id': lambda: fake.hexify('^^:^^:^^:^^:^^:^^', upper=True),
            'vehicle_vin': lambda: fake.bothify('?##??#??#?#######').upper(),
            'zip_code': lambda: fake.zipcode(),
        }

        gen = generators.get(pii_type, lambda: fake.text(max_nb_chars=20))
        return series.apply(lambda v: gen() if pd.notna(v) else v)

    @staticmethod
    def _hash_to_digits(value: str, length: int) -> str:
        """Convert a hash of value into a string of digits with the given length."""
        h = hashlib.sha256(str(value).encode()).hexdigest()
        # Map hex chars to digits deterministically
        digits = ''.join(str(int(c, 16) % 10) for c in h)
        return digits[:length]

    @staticmethod
    def _hash_to_alpha(value: str, length: int, upper: bool = True) -> str:
        """Convert a hash of value into alphabetic characters."""
        h = hashlib.sha256(str(value).encode()).hexdigest()
        chars = ''.join(chr(65 + int(c, 16) % 26) for c in h)
        result = chars[:length]
        return result if upper else result.lower()

    @staticmethod
    def _hash_replace(series: pd.Series, pii_type: str) -> pd.Series:
        """Format-preserving hash: output looks like the original PII type."""

        def _format_preserving_mask(value):
            if pd.isna(value):
                return value
            val = str(value)
            d = PIIMasker._hash_to_digits
            a = PIIMasker._hash_to_alpha

            if pii_type == 'ssn':
                # SSN: 123-45-6789
                digits = d(val, 9)
                return f"{digits[:3]}-{digits[3:5]}-{digits[5:9]}"

            elif pii_type == 'credit_card':
                # Credit card: 4XXX-XXXX-XXXX-XXXX (starts with valid prefix)
                digits = d(val, 15)
                return f"4{digits[:3]}-{digits[3:7]}-{digits[7:11]}-{digits[11:15]}"

            elif pii_type == 'phone':
                # Phone: 555-XXX-XXXX (555 prefix = clearly fake)
                digits = d(val, 7)
                return f"555-{digits[:3]}-{digits[3:7]}"

            elif pii_type == 'passport':
                # Passport: AB1234567
                letters = a(val, 2)
                digits = d(val, 7)
                return f"{letters}{digits}"

            elif pii_type == 'drivers_license':
                # Driver's license: X-12345678
                letter = a(val, 1)
                digits = d(val, 8)
                return f"{letter}-{digits}"

            elif pii_type == 'bank_account':
                # Bank account: XXXX-XXXX-XXXX-XXXX
                digits = d(val, 16)
                return f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"

            elif pii_type == 'medical_record':
                # Medical record: MRN-XXXXXXX
                digits = d(val, 7)
                return f"MRN-{digits}"

            elif pii_type == 'national_id':
                # National ID: XXX-XX-XXXX (same as SSN format)
                digits = d(val, 9)
                return f"{digits[:3]}-{digits[3:5]}-{digits[5:9]}"

            elif pii_type == 'tax_id':
                # Tax ID / EIN: XX-XXXXXXX
                digits = d(val, 9)
                return f"{digits[:2]}-{digits[2:9]}"

            elif pii_type == 'license_plate':
                # License plate: ABC-1234
                letters = a(val, 3)
                digits = d(val, 4)
                return f"{letters}-{digits}"

            elif pii_type == 'email':
                # Email: user1234@masked.example.com
                digits = d(val, 4)
                letters = a(val, 6, upper=False)
                return f"{letters}{digits}@masked.example.com"

            elif pii_type == 'ip':
                # IP: X.X.X.X with valid octets
                h = hashlib.sha256(val.encode()).digest()
                octets = [str(b % 224 + 1) for b in h[:4]]  # 1-224 range
                return '.'.join(octets)

            elif pii_type == 'employee_id':
                # Employee ID: EMP-XXXXXX
                digits = d(val, 6)
                return f"EMP-{digits}"

            elif pii_type == 'device_id':
                # MAC address: XX:XX:XX:XX:XX:XX
                h = hashlib.sha256(val.encode()).hexdigest()[:12]
                return ':'.join(h[i:i+2].upper() for i in range(0, 12, 2))

            elif pii_type == 'vehicle_vin':
                # VIN: 17 chars alphanumeric
                letters = a(val, 5)
                digits = d(val, 12)
                return f"{letters[0]}{digits[:2]}{letters[1:3]}{digits[2]}{letters[3:5]}{digits[3]}{digits[4:12]}"

            elif pii_type == 'zip_code':
                # ZIP code: XXXXX
                digits = d(val, 5)
                return digits

            else:
                # Generic fallback: hex hash (16 chars)
                return hashlib.sha256(val.encode()).hexdigest()[:16]

        return series.apply(_format_preserving_mask)

    @staticmethod
    def _redact_replace(series: pd.Series, pii_type: str) -> pd.Series:
        """Replace with redacted markers."""
        redact_map = {
            'email': '***@***.***',
            'ssn': '***-**-****',
            'phone': '***-***-****',
            'credit_card': '****-****-****-****',
            'ip': '***.***.***.***',
            'name': '[REDACTED]',
            'address': '[REDACTED ADDRESS]',
            'date_of_birth': '****-**-**',
            'password': '[REDACTED]',
            'biometric': '[REDACTED]',
            'ethnicity': '[REDACTED]',
            'religion': '[REDACTED]',
            'political_opinion': '[REDACTED]',
        }
        marker = redact_map.get(pii_type, '[REDACTED]')
        return series.apply(lambda v: marker if pd.notna(v) else v)

    @staticmethod
    def _generalize_replace(series: pd.Series, pii_type: str) -> pd.Series:
        """Replace with generalized values (ranges, categories)."""
        if pii_type == 'date_of_birth':
            date_fmt = PIIMasker._detect_date_format(series)

            def generalize_dob(v):
                if pd.isna(v):
                    return v
                v_str = str(v).strip()
                # Try detected format first, then pandas fallback
                parsed = None
                try:
                    parsed = datetime.strptime(v_str, date_fmt)
                except ValueError:
                    try:
                        parsed = pd.to_datetime(v_str).to_pydatetime()
                    except Exception:
                        pass
                if parsed is not None:
                    decade = (parsed.year // 10) * 10
                    return f"{decade}s"
                return "[GENERALIZED]"
            return series.apply(generalize_dob)
        elif pii_type == 'geolocation':
            def generalize_geo(v):
                if pd.isna(v):
                    return v
                try:
                    parts = str(v).split(',')
                    lat = round(float(parts[0].strip()), 1)
                    lon = round(float(parts[1].strip()), 1)
                    return f"{lat}, {lon}"
                except Exception:
                    return "[GENERALIZED]"
            return series.apply(generalize_geo)
        elif pii_type == 'age':
            def generalize_age(v):
                if pd.isna(v):
                    return v
                try:
                    age = int(float(str(v)))
                    decade = (age // 10) * 10
                    return f"{decade}-{decade + 9}"
                except Exception:
                    return "[GENERALIZED]"
            return series.apply(generalize_age)
        elif pii_type == 'salary':
            def generalize_salary(v):
                if pd.isna(v):
                    return v
                try:
                    val = float(str(v).replace(',', '').replace('$', ''))
                    bracket = int(val // 25000) * 25000
                    return f"{bracket}-{bracket + 24999}"
                except Exception:
                    return "[GENERALIZED]"
            return series.apply(generalize_salary)
        elif pii_type == 'zip_code':
            def generalize_zip(v):
                if pd.isna(v):
                    return v
                s = str(v).strip()
                # Keep first 3 digits, mask the rest
                return s[:3] + '**' if len(s) >= 3 else s
            return series.apply(generalize_zip)
        elif pii_type in ('gender', 'marital_status', 'education', 'nationality', 'occupation'):
            # Keep the value as-is (already categorical, low cardinality)
            # but could be suppressed if the user prefers
            return series
        elif pii_type in ('name', 'address', 'email'):
            return series.apply(lambda v: str(v)[0] + '***' if pd.notna(v) and len(str(v)) > 0 else v)
        else:
            return series.apply(lambda v: '[GENERALIZED]' if pd.notna(v) else v)


def generate_pii_mask_background(job_id: str, original_path: str, config: dict):
    """Background task for PII masking."""
    from app.db.database import SessionLocal, Job, JobStatusEnum
    import os

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.progress = 5
        job.message = "Loading dataset..."
        db.commit()

        # Load data
        if original_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(original_path)
        else:
            df = pd.read_csv(original_path)

        job.progress = 10
        job.message = "Analyzing columns with LLM for PII detection..."
        db.commit()

        # Detect PII (LLM-first with regex fallback)
        detections = PIIDetector.detect_pii_columns(df)
        pii_columns = {d['column_name']: d for d in detections}

        # Get strategies from config (user overrides)
        user_strategies = config.get('pii_column_strategies', {})

        # If the user explicitly selected columns, only mask those
        if user_strategies:
            selected_columns = {
                col_name: pii_columns.get(col_name, {
                    'column_name': col_name,
                    'pii_type': 'unknown',
                    'pii_category': 'direct',
                    'confidence': 1.0,
                    'suggested_strategy': strategy,
                })
                for col_name, strategy in user_strategies.items()
                if col_name in df.columns
            }
        else:
            selected_columns = pii_columns

        job.progress = 20
        job.message = f"Detected {len(pii_columns)} PII columns, masking {len(selected_columns)}..."
        db.commit()

        masked_df = df.copy()
        column_reports = []

        for i, (col_name, detection) in enumerate(selected_columns.items()):
            strategy = user_strategies.get(col_name, detection.get('suggested_strategy', 'redact'))
            pii_type = detection.get('pii_type', 'unknown')

            # Get before samples
            before_samples = df[col_name].dropna().head(3).tolist()

            # Mask the column
            masked_df[col_name] = PIIMasker.mask_column(df[col_name], pii_type, strategy)

            # Get after samples
            after_samples = masked_df[col_name].dropna().head(3).tolist()

            column_reports.append({
                'column_name': col_name,
                'pii_type': pii_type,
                'strategy': strategy,
                'confidence': detection['confidence'],
                'before_samples': [str(s) for s in before_samples],
                'after_samples': [str(s) for s in after_samples],
            })

            progress = 20 + (60 * (i + 1) / len(selected_columns))
            job.progress = int(progress)
            job.message = f"Masking column: {col_name} ({i+1}/{len(selected_columns)})"
            db.commit()

        # Save masked data
        job.progress = 85
        job.message = "Saving masked dataset..."
        db.commit()

        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, "masked_data.csv")
        masked_df.to_csv(output_path, index=False)

        # Calculate privacy assessment
        total_cells = len(df) * len(selected_columns)
        masked_cells = total_cells  # All selected PII cells are masked

        privacy_assessment = {
            'total_pii_columns_detected': len(pii_columns),
            'pii_columns_masked': len(selected_columns),
            'total_rows': len(df),
            'total_pii_cells_masked': masked_cells,
            'strategies_used': list(set(r['strategy'] for r in column_reports)),
            'risk_score': max(0.0, 1.0 - (len(selected_columns) / max(len(df.columns), 1))),
            'privacy_score': min(1.0, len(selected_columns) / max(len(df.columns) * 0.5, 1)),
        }

        # Save results
        results = {
            'summary': {
                'total_columns': len(df.columns),
                'pii_columns_detected': len(pii_columns),
                'pii_columns_masked': len(selected_columns),
                'rows_processed': len(df),
                'strategies_applied': {r['strategy'] for r in column_reports} and
                    dict(pd.Series([r['strategy'] for r in column_reports]).value_counts()),
            },
            'column_reports': column_reports,
            'privacy_assessment': privacy_assessment,
        }

        results_path = os.path.join(output_dir, "results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        job.progress = 100
        job.status = JobStatusEnum.COMPLETED
        job.message = f"Masked {len(selected_columns)} PII columns across {len(df)} rows"
        job.rows_generated = len(df)
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"PII masking failed: {e}")
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)[:500]
            job.message = f"Failed: {str(e)[:200]}"
            db.commit()
    finally:
        db.close()
