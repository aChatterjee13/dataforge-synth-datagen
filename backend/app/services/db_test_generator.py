"""
Database Test Data Generator - Parses DB schemas and generates test INSERT statements using LLM.
"""

import os
import json
import re
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

from app.services.llm_client import LLMClient
from app.services.sql_validator import SQLValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DBSchemaParser:
    """Parse database schema files (SQL DDL, JSON, YAML)."""

    @staticmethod
    def parse_schema(file_path: str) -> Dict[str, Any]:
        """Auto-detect format and parse schema file."""
        ext = os.path.splitext(file_path)[1].lower()

        with open(file_path, 'r') as f:
            content = f.read()

        if ext in ('.sql', '.ddl'):
            return DBSchemaParser.parse_sql_ddl(content)
        elif ext in ('.json',):
            return DBSchemaParser._parse_json_schema(content)
        elif ext in ('.yaml', '.yml'):
            return DBSchemaParser._parse_yaml_schema(content)
        else:
            # Try SQL first, then JSON, then YAML
            if 'CREATE TABLE' in content.upper():
                return DBSchemaParser.parse_sql_ddl(content)
            try:
                return DBSchemaParser._parse_json_schema(content)
            except Exception:
                import yaml
                return DBSchemaParser._parse_yaml_schema(content)

    @staticmethod
    def parse_sql_ddl(content: str) -> Dict[str, Any]:
        """Parse CREATE TABLE statements from SQL DDL."""
        import sqlparse

        tables = {}
        parsed = sqlparse.parse(content)

        for statement in parsed:
            if statement.get_type() == 'CREATE':
                table_info = DBSchemaParser._parse_create_table(str(statement))
                if table_info:
                    tables[table_info['name']] = table_info

        # If sqlparse parsing missed tables, try regex fallback
        if not tables:
            tables = DBSchemaParser._regex_parse_ddl(content)

        dep_order = DBSchemaParser.topological_sort(tables)

        return {
            'tables': tables,
            'dependency_order': dep_order,
            'total_tables': len(tables),
            'raw_ddl': content
        }

    @staticmethod
    def _parse_create_table(statement: str) -> Optional[Dict]:
        """Parse a single CREATE TABLE statement."""
        # Extract table name
        match = re.search(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+(?:\.\w+)?)[`"\]]?',
            statement, re.IGNORECASE
        )
        if not match:
            return None

        table_name = match.group(1).split('.')[-1]  # Remove schema prefix

        # Extract column definitions
        # Find content between first ( and last )
        paren_start = statement.find('(')
        paren_end = statement.rfind(')')
        if paren_start == -1 or paren_end == -1:
            return None

        body = statement[paren_start + 1:paren_end]

        columns = []
        primary_keys = []
        foreign_keys = []
        unique_constraints = []

        # Split by commas, but respect parentheses
        parts = DBSchemaParser._split_column_defs(body)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            upper = part.upper().strip()

            # Table-level PRIMARY KEY
            if upper.startswith('PRIMARY KEY'):
                pk_match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
                if pk_match:
                    primary_keys.extend([
                        c.strip().strip('`"[]')
                        for c in pk_match.group(1).split(',')
                    ])
                continue

            # Table-level FOREIGN KEY
            if upper.startswith('FOREIGN KEY') or upper.startswith('CONSTRAINT'):
                fk_match = re.search(
                    r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"\[]?(\w+)[`"\]]?\s*\(([^)]+)\)',
                    part, re.IGNORECASE
                )
                if fk_match:
                    foreign_keys.append({
                        'columns': [c.strip().strip('`"[]') for c in fk_match.group(1).split(',')],
                        'ref_table': fk_match.group(2),
                        'ref_columns': [c.strip().strip('`"[]') for c in fk_match.group(3).split(',')]
                    })
                continue

            # Table-level UNIQUE
            if upper.startswith('UNIQUE'):
                uq_match = re.search(r'UNIQUE\s*\(([^)]+)\)', part, re.IGNORECASE)
                if uq_match:
                    unique_constraints.append(
                        [c.strip().strip('`"[]') for c in uq_match.group(1).split(',')]
                    )
                continue

            # Skip CHECK, INDEX, etc.
            if any(upper.startswith(kw) for kw in ('CHECK', 'INDEX', 'KEY', 'UNIQUE INDEX')):
                continue

            # Column definition
            col = DBSchemaParser._parse_column(part)
            if col:
                columns.append(col)
                if col.get('primary_key'):
                    primary_keys.append(col['name'])
                if col.get('foreign_key'):
                    foreign_keys.append(col['foreign_key'])

        return {
            'name': table_name,
            'columns': columns,
            'primary_keys': primary_keys,
            'foreign_keys': foreign_keys,
            'unique_constraints': unique_constraints
        }

    @staticmethod
    def _parse_column(definition: str) -> Optional[Dict]:
        """Parse a single column definition."""
        # Match: column_name TYPE [(size)] [constraints...]
        match = re.match(
            r'[`"\[]?(\w+)[`"\]]?\s+(\w+(?:\s+\w+)?)\s*(?:\(([^)]*)\))?\s*(.*)',
            definition.strip(),
            re.IGNORECASE
        )
        if not match:
            return None

        name = match.group(1)
        data_type = match.group(2).upper()
        type_params = match.group(3)
        constraints_str = match.group(4) or ''

        # Skip if name is a keyword
        if name.upper() in ('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'INDEX', 'CONSTRAINT', 'KEY'):
            return None

        col = {
            'name': name,
            'data_type': data_type,
            'nullable': True,
            'primary_key': False,
            'auto_increment': False,
            'default': None,
            'foreign_key': None
        }

        if type_params:
            col['type_params'] = type_params

        upper_constraints = constraints_str.upper()

        if 'NOT NULL' in upper_constraints:
            col['nullable'] = False
        if 'PRIMARY KEY' in upper_constraints:
            col['primary_key'] = True
            col['nullable'] = False
        if any(kw in upper_constraints for kw in ('AUTO_INCREMENT', 'AUTOINCREMENT', 'SERIAL', 'IDENTITY', 'GENERATED')):
            col['auto_increment'] = True

        # Inline REFERENCES
        ref_match = re.search(
            r'REFERENCES\s+[`"\[]?(\w+)[`"\]]?\s*\(([^)]+)\)',
            constraints_str, re.IGNORECASE
        )
        if ref_match:
            col['foreign_key'] = {
                'columns': [name],
                'ref_table': ref_match.group(1),
                'ref_columns': [c.strip().strip('`"[]') for c in ref_match.group(2).split(',')]
            }

        # Default value
        default_match = re.search(r"DEFAULT\s+(.+?)(?:\s+(?:NOT|NULL|PRIMARY|REFERENCES|UNIQUE|CHECK)|$)", constraints_str, re.IGNORECASE)
        if default_match:
            col['default'] = default_match.group(1).strip().strip("'\"")

        return col

    @staticmethod
    def _split_column_defs(body: str) -> List[str]:
        """Split column definitions by comma, respecting parentheses."""
        parts = []
        current = []
        depth = 0

        for char in body:
            if char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        return parts

    @staticmethod
    def _regex_parse_ddl(content: str) -> Dict:
        """Fallback regex-based DDL parser."""
        tables = {}
        pattern = re.compile(
            r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+(?:\.\w+)?)[`"\]]?\s*\((.+?)\)\s*;',
            re.IGNORECASE | re.DOTALL
        )

        for match in pattern.finditer(content):
            table_name = match.group(1).split('.')[-1]
            body = match.group(2)

            columns = []
            for line in body.split('\n'):
                line = line.strip().rstrip(',')
                if not line:
                    continue
                col = DBSchemaParser._parse_column(line)
                if col:
                    columns.append(col)

            if columns:
                tables[table_name] = {
                    'name': table_name,
                    'columns': columns,
                    'primary_keys': [c['name'] for c in columns if c.get('primary_key')],
                    'foreign_keys': [c['foreign_key'] for c in columns if c.get('foreign_key')],
                    'unique_constraints': []
                }

        return tables

    @staticmethod
    def _parse_json_schema(content: str) -> Dict[str, Any]:
        """Parse JSON schema definition."""
        data = json.loads(content)
        tables = {}

        # Support { "tables": { "table_name": { "columns": [...] } } }
        table_data = data.get('tables', data)

        for table_name, table_def in table_data.items():
            if not isinstance(table_def, dict):
                continue

            columns = []
            for col_def in table_def.get('columns', []):
                columns.append({
                    'name': col_def.get('name', ''),
                    'data_type': col_def.get('type', col_def.get('data_type', 'TEXT')).upper(),
                    'nullable': col_def.get('nullable', True),
                    'primary_key': col_def.get('primary_key', False),
                    'auto_increment': col_def.get('auto_increment', False),
                    'default': col_def.get('default'),
                    'foreign_key': col_def.get('foreign_key')
                })

            tables[table_name] = {
                'name': table_name,
                'columns': columns,
                'primary_keys': [c['name'] for c in columns if c.get('primary_key')],
                'foreign_keys': [c.get('foreign_key') for c in columns if c.get('foreign_key')],
                'unique_constraints': table_def.get('unique_constraints', [])
            }

        dep_order = DBSchemaParser.topological_sort(tables)

        return {
            'tables': tables,
            'dependency_order': dep_order,
            'total_tables': len(tables),
            'raw_ddl': content
        }

    @staticmethod
    def _parse_yaml_schema(content: str) -> Dict[str, Any]:
        """Parse YAML schema definition."""
        import yaml
        data = yaml.safe_load(content)
        return DBSchemaParser._parse_json_schema(json.dumps(data))

    @staticmethod
    def topological_sort(tables: Dict) -> List[str]:
        """Sort tables by foreign key dependencies (parents first)."""
        graph = defaultdict(set)
        in_degree = defaultdict(int)
        all_tables = set(tables.keys())

        for name, table in tables.items():
            in_degree.setdefault(name, 0)
            for fk in table.get('foreign_keys', []):
                if fk and isinstance(fk, dict):
                    ref_table = fk.get('ref_table', '')
                    if ref_table in all_tables and ref_table != name:
                        graph[ref_table].add(name)
                        in_degree[name] += 1

        # Kahn's algorithm
        queue = [t for t in all_tables if in_degree[t] == 0]
        order = []

        while queue:
            queue.sort()
            node = queue.pop(0)
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Append any remaining (circular deps)
        for t in all_tables:
            if t not in order:
                order.append(t)

        return order

    @staticmethod
    def analyze_schema_info(file_path: str) -> Dict[str, Any]:
        """Quick summary for upload response."""
        try:
            schema = DBSchemaParser.parse_schema(file_path)
            tables = schema['tables']

            total_columns = sum(len(t.get('columns', [])) for t in tables.values())
            total_fks = sum(len(t.get('foreign_keys', [])) for t in tables.values())

            return {
                'total_tables': schema['total_tables'],
                'total_columns': total_columns,
                'total_foreign_keys': total_fks,
                'table_names': list(tables.keys()),
                'dependency_order': schema['dependency_order'],
                'tables_summary': {
                    name: {
                        'columns': len(t.get('columns', [])),
                        'primary_keys': t.get('primary_keys', []),
                        'foreign_key_count': len(t.get('foreign_keys', []))
                    }
                    for name, t in tables.items()
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing schema: {e}")
            return {
                'total_tables': 0,
                'error': str(e)
            }


class DBTestDataGenerator(LLMClient):
    """Generate test INSERT data using LLM."""

    def generate_insert_data(
        self,
        table: Dict,
        all_tables: Dict,
        dep_order: List[str],
        num_rows: int,
        existing_pks: Dict[str, List],
        dialect: str
    ) -> Dict[str, Any]:
        """Generate INSERT statements for a single table."""
        system_prompt = (
            "You are an expert database engineer. Generate realistic SQL INSERT statements. "
            "Return valid JSON only."
        )

        # Build context about the table
        columns_desc = []
        for col in table.get('columns', []):
            desc = f"  - {col['name']} ({col['data_type']})"
            if col.get('primary_key'):
                desc += " [PK]"
            if not col.get('nullable'):
                desc += " [NOT NULL]"
            if col.get('auto_increment'):
                desc += " [AUTO_INCREMENT]"
            if col.get('foreign_key'):
                fk = col['foreign_key']
                desc += f" [FK -> {fk.get('ref_table', '?')}.{','.join(fk.get('ref_columns', []))}]"
            columns_desc.append(desc)

        # FK context: available parent PKs
        fk_context = ""
        for fk in table.get('foreign_keys', []):
            if fk and isinstance(fk, dict):
                ref_table = fk.get('ref_table', '')
                if ref_table in existing_pks:
                    pks = existing_pks[ref_table][:20]
                    fk_context += f"\nAvailable {ref_table} PKs: {json.dumps(pks)}"

        user_prompt = f"""Generate {num_rows} INSERT statements for table `{table['name']}`.

Table structure:
{chr(10).join(columns_desc)}
{fk_context}

Target SQL dialect: {dialect}

Requirements:
- Generate exactly {num_rows} INSERT statements
- Use realistic, domain-appropriate data
- Respect NOT NULL constraints
- Use available FK values for foreign key columns
- For auto-increment PKs, use sequential integers starting from 1
- For non-auto-increment PKs, generate unique values

Return JSON:
{{
  "inserts": ["INSERT INTO ...", "INSERT INTO ...", ...],
  "pk_values": [1, 2, 3, ...]
}}

The pk_values should be the primary key values used, for child table references."""

        try:
            result = self.call(system_prompt, user_prompt, expect_json=True)
            if not isinstance(result, dict):
                logger.warning(f"LLM returned non-dict for {table['name']} inserts: {type(result)}")
                return {'inserts': [], 'pk_values': []}
            return {
                'inserts': result.get('inserts', []),
                'pk_values': result.get('pk_values', [])
            }
        except Exception as e:
            logger.error(f"Error generating inserts for {table['name']}: {e}")
            return {'inserts': [], 'pk_values': []}

    def generate_violation_tests(
        self,
        table: Dict,
        all_tables: Dict,
        existing_pks: Dict[str, List]
    ) -> List[Dict]:
        """Generate constraint violation test cases."""
        system_prompt = (
            "You are an expert database test engineer. Generate SQL statements that intentionally "
            "violate database constraints for testing purposes. Return valid JSON only."
        )

        columns_desc = []
        for col in table.get('columns', []):
            desc = f"  - {col['name']} ({col['data_type']})"
            if col.get('primary_key'):
                desc += " [PK]"
            if not col.get('nullable'):
                desc += " [NOT NULL]"
            columns_desc.append(desc)

        user_prompt = f"""Generate constraint violation test cases for table `{table['name']}`.

Table structure:
{chr(10).join(columns_desc)}

Primary keys: {table.get('primary_keys', [])}
Foreign keys: {json.dumps(table.get('foreign_keys', []), default=str)}

Generate test cases that should FAIL when executed:

Return JSON array:
[
  {{
    "name": "Test name",
    "constraint_type": "not_null|unique|foreign_key|data_type|check",
    "description": "What constraint this violates",
    "sql": "INSERT INTO ... (the violating statement)",
    "expected_error": "Brief description of expected error"
  }}
]

Generate 3-5 violation tests covering different constraint types."""

        try:
            result = self.call(system_prompt, user_prompt, expect_json=True)
            violations = []
            if isinstance(result, list):
                violations = result
            elif isinstance(result, dict) and 'tests' in result:
                violations = result['tests'] if isinstance(result['tests'], list) else []
            return [v for v in violations if isinstance(v, dict)]
        except Exception as e:
            logger.error(f"Error generating violation tests for {table['name']}: {e}")
            return []

    @staticmethod
    def _adapt_dialect(sql: str, target_dialect: str) -> str:
        """Adapt SQL syntax for the target dialect."""
        if target_dialect == 'postgresql':
            sql = sql.replace('`', '"')
        elif target_dialect == 'mysql':
            sql = sql.replace('"', '`')
        elif target_dialect == 'sqlserver':
            sql = sql.replace('`', '[').replace('"', '[')
            # Close brackets
            sql = re.sub(r'\[(\w+)', r'[\1]', sql)
        elif target_dialect == 'oracle':
            sql = sql.replace('`', '"')
        # sqlite needs no changes
        return sql


def generate_db_tests_background(job_id: str, schema_path: str, config: dict):
    """Background task for database test data generation."""
    from app.db.database import SessionLocal, Job, JobStatusEnum
    from dotenv import load_dotenv

    load_dotenv()
    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.progress = 5
        job.message = "Parsing database schema..."
        db.commit()

        schema = DBSchemaParser.parse_schema(schema_path)
        tables = schema['tables']
        dep_order = schema['dependency_order']

        job.progress = 10
        job.message = f"Found {len(tables)} tables, generating test data..."
        db.commit()

        # Initialize generator
        api_key = config.get('gpt_api_key') or os.getenv('OPENAI_API_KEY')
        gpt_model = config.get('gpt_model', 'gpt-4o-mini')
        gpt_endpoint = config.get('gpt_endpoint')

        generator = DBTestDataGenerator(
            api_key=api_key,
            api_endpoint=gpt_endpoint,
            model=gpt_model
        )

        num_rows = config.get('num_rows_per_table', 100)
        dialect = config.get('sql_dialect', 'postgresql')
        generate_violations = config.get('generate_violations', True)
        generate_performance = config.get('generate_performance', False)

        # Generate INSERTs in dependency order
        existing_pks = {}
        all_inserts = {}
        all_violations = {}

        for i, table_name in enumerate(dep_order):
            if table_name not in tables:
                continue

            table = tables[table_name]

            progress = 10 + (60 * (i + 1) / len(dep_order))
            job.progress = int(progress)
            job.message = f"Generating data for {table_name} ({i+1}/{len(dep_order)})..."
            db.commit()

            result = generator.generate_insert_data(
                table, tables, dep_order, num_rows, existing_pks, dialect
            )

            all_inserts[table_name] = result.get('inserts', [])
            pk_values = result.get('pk_values', [])
            if pk_values:
                existing_pks[table_name] = pk_values

        # Generate violation tests
        if generate_violations:
            job.progress = 72
            job.message = "Generating constraint violation tests..."
            db.commit()

            for i, table_name in enumerate(dep_order):
                if table_name not in tables:
                    continue

                violations = generator.generate_violation_tests(
                    tables[table_name], tables, existing_pks
                )
                if violations:
                    all_violations[table_name] = violations

                progress = 72 + (13 * (i + 1) / len(dep_order))
                job.progress = int(progress)
                db.commit()

        # Run SQLite validation
        job.progress = 88
        job.message = "Running SQLite dry-run validation..."
        db.commit()

        # Build combined INSERT SQL
        all_insert_sql = ""
        for table_name in dep_order:
            if table_name in all_inserts:
                for stmt in all_inserts[table_name]:
                    all_insert_sql += stmt.rstrip(';') + ';\n'

        validation_result = SQLValidator.validate_inserts(
            schema.get('raw_ddl', ''),
            all_insert_sql
        )

        # Save outputs
        job.progress = 95
        job.message = "Saving output files..."
        db.commit()

        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        # Save insert statements
        inserts_path = os.path.join(output_dir, "inserts.sql")
        with open(inserts_path, 'w') as f:
            f.write(f"-- Generated INSERT statements for {len(all_inserts)} tables\n")
            f.write(f"-- Dialect: {dialect}\n")
            f.write(f"-- Generated at: {datetime.utcnow().isoformat()}\n\n")
            for table_name in dep_order:
                if table_name in all_inserts:
                    f.write(f"\n-- Table: {table_name}\n")
                    for stmt in all_inserts[table_name]:
                        f.write(stmt.rstrip(';') + ';\n')

        # Save violations
        if all_violations:
            violations_path = os.path.join(output_dir, "violations.sql")
            with open(violations_path, 'w') as f:
                f.write("-- Constraint violation test cases\n\n")
                for table_name, violations in all_violations.items():
                    f.write(f"\n-- Table: {table_name}\n")
                    for v in violations:
                        f.write(f"-- Test: {v.get('name', 'unnamed')} ({v.get('constraint_type', '')})\n")
                        f.write(f"-- Expected: {v.get('expected_error', 'Should fail')}\n")
                        f.write(f"{v.get('sql', '').rstrip(';')};\n\n")

        # Save results summary
        total_inserts = sum(len(stmts) for stmts in all_inserts.values())
        total_violations = sum(len(vs) for vs in all_violations.values())

        results = {
            'total_tables': len(tables),
            'total_inserts': total_inserts,
            'total_violations': total_violations,
            'dialect': dialect,
            'dependency_order': dep_order,
            'validation': validation_result,
            'table_details': {
                name: {
                    'insert_count': len(all_inserts.get(name, [])),
                    'violation_count': len(all_violations.get(name, [])),
                    'columns': len(tables[name].get('columns', [])),
                    'foreign_keys': [
                        fk.get('ref_table', '') for fk in tables[name].get('foreign_keys', [])
                        if fk and isinstance(fk, dict)
                    ]
                }
                for name in dep_order if name in tables
            },
            'sample_inserts': {
                name: stmts[:3] for name, stmts in all_inserts.items()
            },
            'sample_violations': {
                name: vs[:2] for name, vs in all_violations.items()
            }
        }

        results_path = os.path.join(output_dir, "results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        job.progress = 100
        job.status = JobStatusEnum.COMPLETED
        job.message = f"Generated {total_inserts} INSERTs for {len(tables)} tables"
        job.rows_generated = total_inserts
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"DB test generation failed: {e}")
        traceback.print_exc()
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)[:500]
            job.message = f"Failed: {str(e)[:200]}"
            db.commit()
    finally:
        db.close()
