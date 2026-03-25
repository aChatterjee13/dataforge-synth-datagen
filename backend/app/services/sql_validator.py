"""
In-memory SQLite validation for generated SQL INSERT statements.
"""

import sqlite3
import re
from typing import Dict, Any, List


class SQLValidator:
    """Validates generated INSERT statements by executing them in an in-memory SQLite database."""

    @staticmethod
    def validate_inserts(schema_ddl: str, insert_statements: str) -> Dict[str, Any]:
        """
        Validate INSERT statements against a schema using in-memory SQLite.

        Args:
            schema_ddl: CREATE TABLE statements (will be adapted to SQLite)
            insert_statements: INSERT statements to validate

        Returns:
            Dictionary with validation results
        """
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        results = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'validation_score': 0.0
        }

        try:
            # Adapt and execute DDL
            adapted_ddl = SQLValidator._adapt_ddl_to_sqlite(schema_ddl)
            for statement in SQLValidator._split_statements(adapted_ddl):
                statement = statement.strip()
                if statement and statement.upper().startswith('CREATE'):
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        results['errors'].append(f"DDL error: {str(e)[:100]}")

            conn.commit()

            # Execute INSERTs
            for statement in SQLValidator._split_statements(insert_statements):
                statement = statement.strip()
                if not statement or not statement.upper().startswith('INSERT'):
                    continue

                results['total'] += 1
                try:
                    cursor.execute(statement)
                    results['successful'] += 1
                except Exception as e:
                    results['failed'] += 1
                    if len(results['errors']) < 20:
                        results['errors'].append(f"INSERT #{results['total']}: {str(e)[:150]}")

            conn.commit()

            # Calculate score
            if results['total'] > 0:
                results['validation_score'] = round(
                    results['successful'] / results['total'], 4
                )

        except Exception as e:
            results['errors'].append(f"Validation error: {str(e)[:200]}")
        finally:
            conn.close()

        return results

    @staticmethod
    def _adapt_ddl_to_sqlite(ddl: str) -> str:
        """Adapt DDL from various SQL dialects to SQLite-compatible syntax."""
        adapted = ddl

        # Remove engine-specific clauses
        adapted = re.sub(r'ENGINE\s*=\s*\w+', '', adapted, flags=re.IGNORECASE)
        adapted = re.sub(r'DEFAULT\s+CHARSET\s*=\s*\w+', '', adapted, flags=re.IGNORECASE)
        adapted = re.sub(r'COLLATE\s*=?\s*\w+', '', adapted, flags=re.IGNORECASE)
        adapted = re.sub(r'AUTO_INCREMENT\s*=?\s*\d*', '', adapted, flags=re.IGNORECASE)
        adapted = re.sub(r'COMMENT\s+\'[^\']*\'', '', adapted, flags=re.IGNORECASE)

        # Replace common type aliases
        type_map = {
            r'\bSERIAL\b': 'INTEGER',
            r'\bBIGSERIAL\b': 'INTEGER',
            r'\bSMALLSERIAL\b': 'INTEGER',
            r'\bUUID\b': 'TEXT',
            r'\bVARCHAR\s*\([^)]*\)': 'TEXT',
            r'\bCHARACTER\s+VARYING\s*\([^)]*\)': 'TEXT',
            r'\bNVARCHAR\s*\([^)]*\)': 'TEXT',
            r'\bTIMESTAMPTZ\b': 'TEXT',
            r'\bTIMESTAMP\s+WITH\s+TIME\s+ZONE\b': 'TEXT',
            r'\bTIMESTAMP\s+WITHOUT\s+TIME\s+ZONE\b': 'TEXT',
            r'\bTIMESTAMP\b': 'TEXT',
            r'\bDATETIME2?\b': 'TEXT',
            r'\bBOOLEAN\b': 'INTEGER',
            r'\bBOOL\b': 'INTEGER',
            r'\bJSONB?\b': 'TEXT',
            r'\bARRAY\b': 'TEXT',
            r'\bMONEY\b': 'REAL',
            r'\bDOUBLE\s+PRECISION\b': 'REAL',
            r'\bNUMERIC\s*\([^)]*\)': 'REAL',
            r'\bDECIMAL\s*\([^)]*\)': 'REAL',
            r'\bINT\d?\b': 'INTEGER',
            r'\bBIGINT\b': 'INTEGER',
            r'\bSMALLINT\b': 'INTEGER',
            r'\bTINYINT\b': 'INTEGER',
            r'\bMEDIUMINT\b': 'INTEGER',
        }

        for pattern, replacement in type_map.items():
            adapted = re.sub(pattern, replacement, adapted, flags=re.IGNORECASE)

        # Remove IF NOT EXISTS for broader compat
        adapted = re.sub(r'IF\s+NOT\s+EXISTS\s+', '', adapted, flags=re.IGNORECASE)

        # Remove schema prefix (e.g., public.table_name -> table_name)
        adapted = re.sub(r'\b\w+\.(\w+)', r'\1', adapted)

        # Remove ON DELETE/UPDATE CASCADE etc from inline constraints for simpler parsing
        # Keep REFERENCES but simplify
        adapted = re.sub(r'ON\s+DELETE\s+\w+(\s+\w+)?', '', adapted, flags=re.IGNORECASE)
        adapted = re.sub(r'ON\s+UPDATE\s+\w+(\s+\w+)?', '', adapted, flags=re.IGNORECASE)

        # Replace NOW() / CURRENT_TIMESTAMP functions
        adapted = re.sub(r"DEFAULT\s+NOW\(\)", "DEFAULT CURRENT_TIMESTAMP", adapted, flags=re.IGNORECASE)
        adapted = re.sub(r"DEFAULT\s+GETDATE\(\)", "DEFAULT CURRENT_TIMESTAMP", adapted, flags=re.IGNORECASE)

        # Remove IDENTITY(...) for SQL Server
        adapted = re.sub(r'IDENTITY\s*\([^)]*\)', '', adapted, flags=re.IGNORECASE)

        return adapted

    @staticmethod
    def _split_statements(sql: str) -> List[str]:
        """Split SQL into individual statements by semicolons, respecting quotes."""
        statements = []
        current = []
        in_quote = False
        quote_char = None

        for char in sql:
            if char in ("'", '"') and not in_quote:
                in_quote = True
                quote_char = char
                current.append(char)
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
                current.append(char)
            elif char == ';' and not in_quote:
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(char)

        # Last statement (no trailing semicolon)
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)

        return statements
