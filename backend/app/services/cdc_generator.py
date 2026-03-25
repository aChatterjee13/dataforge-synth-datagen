"""
CDC (Change Data Capture) Pipeline Testing Service - Generate CDC event streams from schemas.

Uses LLM to generate realistic row values (same approach as DBTestDataGenerator),
then wraps them in CDC event envelopes with proper temporal ordering.
"""

import json
import random
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.services.db_test_generator import DBSchemaParser
from app.services.llm_client import LLMClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CDCEventGenerator:
    """Generate CDC event streams from database schemas using LLM for realistic values."""

    SQL_TYPE_MAP = {
        'INT': 'integer', 'INTEGER': 'integer', 'BIGINT': 'integer', 'SMALLINT': 'integer',
        'SERIAL': 'integer', 'BIGSERIAL': 'integer',
        'VARCHAR': 'string', 'CHAR': 'string', 'TEXT': 'string', 'NVARCHAR': 'string',
        'BOOLEAN': 'boolean', 'BOOL': 'boolean',
        'FLOAT': 'float', 'DOUBLE': 'float', 'DECIMAL': 'float', 'NUMERIC': 'float', 'REAL': 'float',
        'DATE': 'date', 'TIMESTAMP': 'timestamp', 'DATETIME': 'timestamp',
        'UUID': 'uuid',
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client
        # Pre-generated row pools per table: { table_name: [ {col: val, ...}, ... ] }
        self._row_pools: Dict[str, List[Dict]] = {}

    def generate_cdc_events(
        self,
        schema: Dict[str, Any],
        config: dict,
        progress_callback=None,
    ) -> List[Dict[str, Any]]:
        """Generate CDC events respecting FK ordering."""
        tables = schema['tables']
        dep_order = schema.get('dependency_order', list(tables.keys()))

        event_count = config.get('cdc_event_count', 500)
        insert_ratio = config.get('cdc_insert_ratio', 0.5)
        update_ratio = config.get('cdc_update_ratio', 0.3)
        delete_ratio = config.get('cdc_delete_ratio', 0.2)
        time_range_hours = config.get('cdc_time_range_hours', 24)

        # Normalize ratios
        total = insert_ratio + update_ratio + delete_ratio
        if total > 0:
            insert_ratio /= total
            update_ratio /= total
            delete_ratio /= total

        now = datetime.utcnow()
        start_time = now - timedelta(hours=time_range_hours)

        # Pre-generate row pools via LLM for each table
        if self.llm:
            pool_size = min(50, max(10, event_count // max(len(tables), 1)))
            for i, table_name in enumerate(dep_order):
                if table_name not in tables:
                    continue
                if progress_callback:
                    pct = 15 + int(30 * (i + 1) / len(dep_order))
                    progress_callback(pct, f"Generating data pool for {table_name}...")
                self._generate_row_pool(tables[table_name], pool_size)

        # Track existing rows per table for updates/deletes
        existing_rows: Dict[str, List[Dict]] = defaultdict(list)
        pk_counters: Dict[str, int] = defaultdict(lambda: 1)
        events = []

        # Phase 1: Seed initial inserts (at least 1 per table in dep order)
        for table_name in dep_order:
            if table_name not in tables:
                continue
            table = tables[table_name]
            row = self._generate_row(table, tables, existing_rows, pk_counters)
            if row:
                existing_rows[table_name].append(row)
                ts = start_time + timedelta(seconds=random.uniform(0, time_range_hours * 60))
                events.append(self._make_event('INSERT', table_name, table, None, row, ts))

        # Phase 2: Generate remaining events
        remaining = event_count - len(events)
        for i in range(remaining):
            ts = start_time + timedelta(seconds=random.uniform(0, time_range_hours * 3600))
            r = random.random()

            if r < insert_ratio:
                # INSERT - pick table weighted by dep order (parents first)
                table_name = random.choice(dep_order)
                if table_name not in tables:
                    continue
                table = tables[table_name]
                row = self._generate_row(table, tables, existing_rows, pk_counters)
                if row:
                    existing_rows[table_name].append(row)
                    events.append(self._make_event('INSERT', table_name, table, None, row, ts))

            elif r < insert_ratio + update_ratio:
                # UPDATE - pick a table with existing rows
                candidates = [t for t in dep_order if existing_rows.get(t)]
                if candidates:
                    table_name = random.choice(candidates)
                    table = tables[table_name]
                    old_row = random.choice(existing_rows[table_name])
                    new_row = self._mutate_row(old_row, table)
                    # Update the existing row reference
                    idx = existing_rows[table_name].index(old_row)
                    existing_rows[table_name][idx] = new_row
                    events.append(self._make_event('UPDATE', table_name, table, old_row, new_row, ts))

            else:
                # DELETE - pick table in reverse dep order (children first)
                candidates = [t for t in reversed(dep_order) if len(existing_rows.get(t, [])) > 1]
                if candidates:
                    table_name = candidates[0]
                    table = tables[table_name]
                    row = existing_rows[table_name].pop(random.randint(0, len(existing_rows[table_name]) - 1))
                    events.append(self._make_event('DELETE', table_name, table, row, None, ts))

        # Sort by timestamp
        events.sort(key=lambda e: e.get('timestamp', ''))

        return events

    def _generate_row_pool(self, table: Dict, pool_size: int):
        """Use LLM to generate a pool of realistic rows for a table."""
        table_name = table['name']

        # Build column descriptions (exclude auto-increment PKs and FK columns)
        columns_desc = []
        value_columns = []
        for col in table.get('columns', []):
            if col.get('auto_increment') or col.get('primary_key'):
                continue
            if col.get('foreign_key'):
                continue

            desc = f"  - {col['name']} ({col.get('data_type', 'TEXT')})"
            if not col.get('nullable'):
                desc += " [NOT NULL]"
            columns_desc.append(desc)
            value_columns.append(col['name'])

        if not value_columns:
            self._row_pools[table_name] = []
            return

        system_prompt = (
            "You are an expert database engineer. Generate realistic, domain-appropriate "
            "data values for database rows. Return valid JSON only."
        )

        user_prompt = f"""Generate {pool_size} realistic data rows for the table `{table_name}`.

Columns to generate values for:
{chr(10).join(columns_desc)}

Requirements:
- Generate exactly {pool_size} rows as a JSON array of objects
- Each object should have keys matching the column names above
- Use realistic, contextually appropriate values (not random strings)
- Infer the domain from table and column names (e.g. "users" table → real names, "orders" → realistic order data)
- Vary the data — don't repeat the same values across rows
- For dates, use ISO format (YYYY-MM-DD)
- For timestamps, use ISO format (YYYY-MM-DDTHH:MM:SSZ)
- For booleans, use true/false
- Match the data type specified for each column

Return JSON:
{{
  "rows": [
    {{{", ".join(f'"{c}": <value>' for c in value_columns)}}},
    ...
  ]
}}"""

        try:
            result = self.llm.call(system_prompt, user_prompt, expect_json=True)
            rows = []
            if isinstance(result, dict):
                rows = result.get('rows', [])
            elif isinstance(result, list):
                rows = result

            # Validate: keep only rows that are dicts with at least some expected keys
            valid_rows = []
            for row in rows:
                if isinstance(row, dict) and any(k in row for k in value_columns):
                    valid_rows.append(row)

            self._row_pools[table_name] = valid_rows
            logger.info(f"Generated {len(valid_rows)} pool rows for table {table_name}")
        except Exception as e:
            logger.warning(f"LLM row pool generation failed for {table_name}: {e}, using fallback")
            self._row_pools[table_name] = []

    def _generate_row(self, table: Dict, all_tables: Dict, existing_rows: Dict, pk_counters: Dict) -> Dict:
        """Generate a row by picking from LLM pool and applying PK/FK overrides."""
        row = {}
        table_name = table['name']
        pool = self._row_pools.get(table_name, [])

        # Pick a random pool row as base values
        pool_row = random.choice(pool) if pool else {}

        for col in table.get('columns', []):
            name = col['name']
            data_type = col.get('data_type', 'TEXT').upper().split('(')[0].strip()

            # Auto-increment / PK: use counter
            if col.get('auto_increment') or col.get('primary_key'):
                row[name] = pk_counters[table_name]
                pk_counters[table_name] += 1
                continue

            # FK: use existing parent row value
            if col.get('foreign_key'):
                fk = col['foreign_key']
                ref_table = fk.get('ref_table', '')
                if existing_rows.get(ref_table):
                    ref_row = random.choice(existing_rows[ref_table])
                    ref_cols = fk.get('ref_columns', [])
                    if ref_cols and ref_cols[0] in ref_row:
                        row[name] = ref_row[ref_cols[0]]
                        continue

            # Use pool value if available
            if name in pool_row:
                row[name] = pool_row[name]
            else:
                # Fallback for columns not in pool
                row[name] = self._fallback_value(data_type, name)

        return row

    def _mutate_row(self, old_row: Dict, table: Dict) -> Dict:
        """Create a mutated version of an existing row (for UPDATE events)."""
        new_row = dict(old_row)
        table_name = table.get('name', '')
        pk_cols = set(table.get('primary_keys', []))
        pool = self._row_pools.get(table_name, [])

        mutable_cols = [
            col for col in table.get('columns', [])
            if col['name'] not in pk_cols and not col.get('auto_increment')
            and not col.get('foreign_key')
        ]

        if mutable_cols:
            # Mutate 1-3 columns
            cols_to_change = random.sample(mutable_cols, min(random.randint(1, 3), len(mutable_cols)))

            # Pick a different pool row to source new values from
            donor_row = random.choice(pool) if pool else {}

            for col in cols_to_change:
                name = col['name']
                if name in donor_row and donor_row[name] != old_row.get(name):
                    new_row[name] = donor_row[name]
                else:
                    # If donor has same value or no value, generate a fallback
                    data_type = col.get('data_type', 'TEXT').upper().split('(')[0].strip()
                    new_row[name] = self._fallback_value(data_type, name)

        return new_row

    def _fallback_value(self, data_type: str, col_name: str) -> Any:
        """Generate a basic typed value when LLM pool doesn't cover a column."""
        mapped = self.SQL_TYPE_MAP.get(data_type, 'string')

        if mapped == 'integer':
            return random.randint(1, 10000)
        elif mapped == 'float':
            return round(random.uniform(0, 1000), 2)
        elif mapped == 'boolean':
            return random.choice([True, False])
        elif mapped == 'date':
            base = datetime.utcnow() - timedelta(days=random.randint(0, 365))
            return base.strftime('%Y-%m-%d')
        elif mapped == 'timestamp':
            base = datetime.utcnow() - timedelta(
                days=random.randint(0, 90),
                seconds=random.randint(0, 86400),
            )
            return base.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif mapped == 'uuid':
            return str(uuid.uuid4())
        else:
            return f'{col_name}_{random.randint(1, 999)}'

    def _make_event(self, op: str, table_name: str, table: Dict, before: Dict, after: Dict, ts: datetime) -> Dict:
        """Create a CDC event envelope."""
        return {
            'operation': op,
            'table': table_name,
            'timestamp': ts.isoformat() + 'Z',
            'before': before,
            'after': after,
            'primary_keys': table.get('primary_keys', []),
        }


def format_debezium(events: List[Dict]) -> List[Dict]:
    """Format events in Debezium-compatible JSON structure."""
    debezium_events = []
    for event in events:
        op_map = {'INSERT': 'c', 'UPDATE': 'u', 'DELETE': 'd'}
        payload = {
            'schema': {'type': 'struct', 'name': f'{event["table"]}.Envelope'},
            'payload': {
                'before': event.get('before'),
                'after': event.get('after'),
                'source': {
                    'version': '2.4.0',
                    'connector': 'dataforge-cdc',
                    'name': 'dataforge',
                    'ts_ms': int(datetime.fromisoformat(event['timestamp'].rstrip('Z')).timestamp() * 1000),
                    'db': 'dataforge_db',
                    'table': event['table'],
                },
                'op': op_map.get(event['operation'], 'c'),
                'ts_ms': int(datetime.fromisoformat(event['timestamp'].rstrip('Z')).timestamp() * 1000),
            }
        }
        debezium_events.append(payload)
    return debezium_events


def format_sql(events: List[Dict]) -> List[str]:
    """Format events as SQL statements."""
    statements = []
    for event in events:
        table = event['table']
        op = event['operation']

        if op == 'INSERT' and event.get('after'):
            cols = ', '.join(event['after'].keys())
            vals = ', '.join(_sql_val(v) for v in event['after'].values())
            statements.append(f"INSERT INTO {table} ({cols}) VALUES ({vals});")

        elif op == 'UPDATE' and event.get('after') and event.get('before'):
            pk_cols = event.get('primary_keys', [])
            sets = ', '.join(f"{k} = {_sql_val(v)}" for k, v in event['after'].items() if k not in pk_cols)
            wheres = ' AND '.join(f"{k} = {_sql_val(event['before'][k])}" for k in pk_cols if k in event['before'])
            if sets and wheres:
                statements.append(f"UPDATE {table} SET {sets} WHERE {wheres};")

        elif op == 'DELETE' and event.get('before'):
            pk_cols = event.get('primary_keys', [])
            wheres = ' AND '.join(f"{k} = {_sql_val(event['before'][k])}" for k in pk_cols if k in event['before'])
            if wheres:
                statements.append(f"DELETE FROM {table} WHERE {wheres};")

    return statements


def format_csv(events: List[Dict]) -> str:
    """Format events as CSV."""
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'operation', 'table', 'data'])

    for event in events:
        data = event.get('after') or event.get('before') or {}
        writer.writerow([
            event['timestamp'],
            event['operation'],
            event['table'],
            json.dumps(data, default=str),
        ])

    return output.getvalue()


def _sql_val(v) -> str:
    """Convert a Python value to SQL literal."""
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    return f"'{str(v).replace(chr(39), chr(39)+chr(39))}'"


def generate_cdc_background(job_id: str, schema_path: str, config: dict):
    """Background task for CDC event generation."""
    from app.db.database import SessionLocal, Job, JobStatusEnum
    import os
    from dotenv import load_dotenv

    load_dotenv()
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.progress = 5
        job.message = "Parsing schema..."
        db.commit()

        schema = DBSchemaParser.parse_schema(schema_path)

        job.progress = 10
        job.message = f"Found {schema['total_tables']} tables, initializing LLM..."
        db.commit()

        # Initialize LLM client
        api_key = config.get('gpt_api_key') or os.getenv('OPENAI_API_KEY')
        gpt_model = config.get('gpt_model', 'gpt-4o-mini')
        gpt_endpoint = config.get('gpt_endpoint')

        llm_client = None
        if api_key:
            llm_client = LLMClient(
                api_key=api_key,
                api_endpoint=gpt_endpoint,
                model=gpt_model
            )

        generator = CDCEventGenerator(llm_client=llm_client)

        def progress_callback(pct, msg):
            job.progress = pct
            job.message = msg
            db.commit()

        events = generator.generate_cdc_events(schema, config, progress_callback=progress_callback)

        job.progress = 60
        job.message = "Formatting output..."
        db.commit()

        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        output_format = config.get('cdc_output_format', 'debezium')

        if output_format == 'debezium':
            formatted = format_debezium(events)
            output_path = os.path.join(output_dir, "cdc_events.json")
            with open(output_path, 'w') as f:
                json.dump(formatted, f, indent=2, default=str)
        elif output_format == 'sql':
            statements = format_sql(events)
            output_path = os.path.join(output_dir, "cdc_events.sql")
            with open(output_path, 'w') as f:
                f.write('\n'.join(statements))
        else:  # csv
            csv_content = format_csv(events)
            output_path = os.path.join(output_dir, "cdc_events.csv")
            with open(output_path, 'w') as f:
                f.write(csv_content)

        job.progress = 85
        job.message = "Saving results..."
        db.commit()

        # Calculate event distribution
        from collections import Counter
        op_counts = Counter(e['operation'] for e in events)
        table_counts = Counter(e['table'] for e in events)

        results = {
            'summary': {
                'total_events': len(events),
                'inserts': op_counts.get('INSERT', 0),
                'updates': op_counts.get('UPDATE', 0),
                'deletes': op_counts.get('DELETE', 0),
                'tables_affected': len(table_counts),
                'output_format': output_format,
                'time_range_hours': config.get('cdc_time_range_hours', 24),
            },
            'event_distribution': dict(op_counts),
            'table_distribution': dict(table_counts),
            'sample_events': events[:10],
        }

        results_path = os.path.join(output_dir, "results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        job.progress = 100
        job.status = JobStatusEnum.COMPLETED
        job.message = f"Generated {len(events)} CDC events ({output_format} format)"
        job.rows_generated = len(events)
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"CDC generation failed: {e}")
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)[:500]
            job.message = f"Failed: {str(e)[:200]}"
            db.commit()
    finally:
        db.close()
