"""
Log & Event Data Synthesis Service - Parse log files and generate synthetic logs.

Generates synthetic logs that mirror the structure, vocabulary, and statistical
distributions of the original input — not random strings.
"""

import re
import json
import random
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LogParser:
    """Parse and analyze log files of various formats."""

    # Format detection patterns
    FORMAT_PATTERNS = {
        'apache': re.compile(
            r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+\S+"\s+(\d{3})\s+(\d+|-)'
        ),
        'nginx': re.compile(
            r'^(\S+)\s+-\s+\S+\s+\[([^\]]+)\]\s+"(\S+)\s+(\S+)\s+\S+"\s+(\d{3})\s+(\d+)'
        ),
        'syslog': re.compile(
            r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s+(.*)'
        ),
        # Structured application logs: "2024-03-01 08:00:01 INFO  [main] message..."
        'application': re.compile(
            r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|TRACE)\s+'
            r'\[([^\]]+)\]\s+(.*)'
        ),
        'json': None,   # Detected by trying JSON parse
        'csv': None,     # Detected by comma/tab structure
    }

    @staticmethod
    def detect_format(content: str) -> str:
        """Detect the log format from content."""
        lines = [l for l in content.strip().split('\n') if l.strip()][:20]

        if not lines:
            return 'unknown'

        # Try JSON first
        try:
            json.loads(lines[0])
            return 'json'
        except (json.JSONDecodeError, ValueError):
            pass

        # Try known patterns (application before syslog since it's more specific)
        ordered_fmts = ['apache', 'nginx', 'application', 'syslog']
        for fmt_name in ordered_fmts:
            pattern = LogParser.FORMAT_PATTERNS.get(fmt_name)
            if pattern is None:
                continue
            matches = sum(1 for line in lines if pattern.match(line))
            if matches > len(lines) * 0.5:
                return fmt_name

        # Check CSV (comma-separated with header)
        if ',' in lines[0] and len(lines[0].split(',')) >= 3:
            return 'csv'

        return 'unknown'

    @staticmethod
    def parse_logs(content: str, fmt: str) -> List[Dict[str, Any]]:
        """Parse logs into structured records."""
        lines = [l for l in content.strip().split('\n') if l.strip()]
        records = []

        if fmt == 'apache' or fmt == 'nginx':
            pattern = LogParser.FORMAT_PATTERNS[fmt]
            for line in lines:
                m = pattern.match(line)
                if m:
                    records.append({
                        'ip': m.group(1),
                        'timestamp': m.group(2),
                        'method': m.group(3),
                        'path': m.group(4),
                        'status': int(m.group(5)),
                        'size': int(m.group(6)) if m.group(6) != '-' else 0,
                    })
            # Also extract user field from full line (between IP and timestamp)
            user_pattern = re.compile(
                r'^(\S+)\s+\S+\s+(\S+)\s+\['
            )
            for i, line in enumerate(lines):
                mu = user_pattern.match(line)
                if mu and i < len(records):
                    records[i]['user'] = mu.group(2)

        elif fmt == 'syslog':
            pattern = LogParser.FORMAT_PATTERNS['syslog']
            for line in lines:
                m = pattern.match(line)
                if m:
                    records.append({
                        'timestamp': m.group(1),
                        'hostname': m.group(2),
                        'process': m.group(3),
                        'pid': m.group(4) or '',
                        'message': m.group(5),
                    })

        elif fmt == 'application':
            pattern = LogParser.FORMAT_PATTERNS['application']
            for line in lines:
                m = pattern.match(line)
                if m:
                    records.append({
                        'timestamp': m.group(1),
                        'level': m.group(2),
                        'component': m.group(3),
                        'message': m.group(4),
                    })

        elif fmt == 'json':
            for line in lines:
                try:
                    records.append(json.loads(line))
                except (json.JSONDecodeError, ValueError):
                    pass

        elif fmt == 'csv':
            import csv
            from io import StringIO
            reader = csv.DictReader(StringIO(content))
            for row in reader:
                records.append(dict(row))

        else:
            # Unknown: treat each line as a message
            for line in lines:
                records.append({'message': line, '_raw': line})

        return records

    @staticmethod
    def analyze_distributions(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze field value distributions from parsed records."""
        if not records:
            return {}

        distributions = {}
        all_keys = set()
        for r in records:
            all_keys.update(r.keys())

        for key in all_keys:
            if key.startswith('_'):
                continue
            values = [r.get(key) for r in records if r.get(key) is not None]
            if not values:
                continue

            # Detect value type from first non-None value
            sample = values[0]
            val_type = 'string'
            if isinstance(sample, bool):
                val_type = 'boolean'
            elif isinstance(sample, int):
                val_type = 'integer'
            elif isinstance(sample, float):
                val_type = 'float'

            # Count value frequencies (limit to top 50)
            counter = Counter(str(v) for v in values)
            top_values = counter.most_common(50)

            dist_info: Dict[str, Any] = {
                'total': len(values),
                'unique': len(counter),
                'type': val_type,
                'top_values': [{'value': v, 'count': c} for v, c in top_values],
            }

            # For numeric types, also store range for interpolation
            if val_type in ('integer', 'float'):
                numeric_vals = []
                for v in values:
                    try:
                        numeric_vals.append(float(v))
                    except (ValueError, TypeError):
                        pass
                if numeric_vals:
                    dist_info['min'] = min(numeric_vals)
                    dist_info['max'] = max(numeric_vals)
                    dist_info['mean'] = sum(numeric_vals) / len(numeric_vals)

            distributions[key] = dist_info

        return distributions


# ============================================================================
# Value sampling helpers
# ============================================================================

def _pick_weighted(dist_info: Dict) -> str:
    """Pick a value weighted by its frequency in the distribution."""
    top_values = dist_info.get('top_values', [])
    if not top_values:
        return ''
    values = [v['value'] for v in top_values]
    weights = [v['count'] for v in top_values]
    return random.choices(values, weights=weights, k=1)[0]


def _pick_numeric(dist_info: Dict) -> float:
    """Pick a numeric value from the observed distribution.

    Uses a mix: 70% sample from observed values, 30% interpolate within range
    to add realistic variety without leaving the original distribution.
    """
    top_values = dist_info.get('top_values', [])
    lo = dist_info.get('min', 0)
    hi = dist_info.get('max', 100)
    mean = dist_info.get('mean', (lo + hi) / 2)

    if top_values and random.random() < 0.7:
        # Sample from observed values
        val_str = _pick_weighted(dist_info)
        try:
            return float(val_str)
        except (ValueError, TypeError):
            pass

    # Interpolate: Gaussian around mean, clamped to [min, max]
    std = (hi - lo) / 4 if hi > lo else 1
    val = random.gauss(mean, std)
    return max(lo, min(hi, val))


def _pick_typed(dist_info: Dict) -> Any:
    """Pick a value with correct type from distribution."""
    val_type = dist_info.get('type', 'string')

    if val_type == 'boolean':
        val_str = _pick_weighted(dist_info)
        return val_str.lower() in ('true', '1', 'yes')

    if val_type in ('integer', 'float'):
        n = _pick_numeric(dist_info)
        return int(round(n)) if val_type == 'integer' else round(n, 2)

    return _pick_weighted(dist_info)


# ============================================================================
# Format-specific generators
# ============================================================================

def generate_synthetic_logs(
    records: List[Dict[str, Any]],
    distributions: Dict[str, Any],
    fmt: str,
    num_lines: int,
    time_range_hours: int,
    error_rate: float,
) -> List[str]:
    """Generate synthetic log lines based on analyzed distributions."""
    now = datetime.utcnow()
    start_time = now - timedelta(hours=time_range_hours)

    synthetic_lines = []

    for i in range(num_lines):
        # Generate timestamp spread across time range
        ts = start_time + timedelta(
            seconds=random.uniform(0, time_range_hours * 3600)
        )

        if fmt in ('apache', 'nginx'):
            line = _generate_access_log(ts, distributions, error_rate, fmt)
        elif fmt == 'syslog':
            line = _generate_syslog(ts, distributions, error_rate)
        elif fmt == 'application':
            line = _generate_application_log(ts, distributions, records, error_rate)
        elif fmt == 'json':
            line = _generate_json_log(ts, distributions, records, error_rate)
        else:
            line = _generate_generic_log(ts, distributions, records, error_rate)

        synthetic_lines.append(line)

    # Sort by timestamp
    synthetic_lines.sort()

    return synthetic_lines


def _generate_access_log(ts, distributions, error_rate, fmt):
    """Generate Apache/nginx access log line using original distributions."""
    # Sample IP from original distribution (not random faker IPs)
    ip = _pick_weighted(distributions['ip']) if 'ip' in distributions else '127.0.0.1'

    # Sample user from original distribution
    user = _pick_weighted(distributions['user']) if 'user' in distributions else '-'

    # Method and path from distributions
    method = _pick_weighted(distributions['method']) if 'method' in distributions else 'GET'
    path = _pick_weighted(distributions['path']) if 'path' in distributions else '/api/health'

    # Status from original distribution, modulated by error_rate
    if 'status' in distributions:
        status_str = _pick_weighted(distributions['status'])
        try:
            status = int(status_str)
        except ValueError:
            status = 200

        # Override with error status at the configured error rate
        if random.random() < error_rate and status < 400:
            # Pick an error status from original errors, or use defaults
            error_statuses = []
            for tv in distributions['status'].get('top_values', []):
                try:
                    s = int(tv['value'])
                    if s >= 400:
                        error_statuses.append((s, tv['count']))
                except ValueError:
                    pass
            if error_statuses:
                vals, wts = zip(*error_statuses)
                status = random.choices(vals, weights=wts, k=1)[0]
            else:
                status = random.choice([400, 404, 500])
    else:
        status = random.choice([400, 404, 500]) if random.random() < error_rate else 200

    # Response size from original distribution
    if 'size' in distributions:
        size = int(round(_pick_numeric(distributions['size'])))
        size = max(0, size)
    else:
        size = random.randint(32, 50000)

    ts_str = ts.strftime('%d/%b/%Y:%H:%M:%S +0000')

    return f'{ip} - {user} [{ts_str}] "{method} {path} HTTP/1.1" {status} {size}'


def _generate_syslog(ts, distributions, error_rate):
    """Generate syslog line using original distributions."""
    hostname = _pick_weighted(distributions['hostname']) if 'hostname' in distributions else 'localhost'
    process = _pick_weighted(distributions['process']) if 'process' in distributions else 'app'

    # Sample PID from original range if available
    if 'pid' in distributions:
        pid_str = _pick_weighted(distributions['pid'])
        try:
            pid = int(pid_str)
        except ValueError:
            pid = random.randint(1000, 65000)
    else:
        pid = random.randint(1000, 65000)

    # Sample message from original messages instead of hardcoded strings
    if 'message' in distributions:
        message = _pick_weighted(distributions['message'])
    else:
        message = 'service started'

    ts_str = ts.strftime('%b %d %H:%M:%S')
    return f'{ts_str} {hostname} {process}[{pid}]: {message}'


def _generate_application_log(ts, distributions, records, error_rate):
    """Generate structured application log line preserving original patterns.

    Format: "YYYY-MM-DD HH:MM:SS LEVEL  [component] message"
    """
    # Sample level from original distribution, modulated by error_rate
    if 'level' in distributions:
        level = _pick_weighted(distributions['level'])
        # Normalize level names
        if level == 'WARNING':
            level = 'WARN'
        # Inject errors at configured rate
        if random.random() < error_rate and level not in ('ERROR', 'FATAL'):
            error_levels = []
            for tv in distributions['level'].get('top_values', []):
                if tv['value'] in ('ERROR', 'FATAL'):
                    error_levels.append((tv['value'], tv['count']))
            if error_levels:
                vals, wts = zip(*error_levels)
                level = random.choices(vals, weights=wts, k=1)[0]
            else:
                level = 'ERROR'
    else:
        level = 'ERROR' if random.random() < error_rate else 'INFO'

    # Sample component from original distribution
    component = _pick_weighted(distributions['component']) if 'component' in distributions else 'app'

    # Sample message from original messages — this is the key improvement
    if 'message' in distributions:
        message = _pick_weighted(distributions['message'])
    elif records:
        # Fallback: pick a message from original records
        rec = random.choice(records)
        message = rec.get('message', 'operation completed')
    else:
        message = 'operation completed'

    # Pad level to align (INFO -> "INFO ", ERROR -> "ERROR")
    level_padded = level.ljust(5)

    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
    return f'{ts_str} {level_padded} [{component}] {message}'


def _generate_json_log(ts, distributions, records, error_rate):
    """Generate JSON log line preserving ALL original keys and value distributions.

    Instead of emitting a fixed schema with faker text, we reproduce the
    exact key set seen in the original records, sampling each value from
    its observed distribution with type-awareness.
    """
    # Determine the set of keys to emit from a randomly sampled original record
    if records:
        template = random.choice(records)
    else:
        template = {}

    entry: Dict[str, Any] = {}

    # Always set timestamp from our generated time
    entry['timestamp'] = ts.isoformat() + 'Z'

    # Determine level first (needed for error_rate modulation)
    if 'level' in distributions:
        level = _pick_weighted(distributions['level'])
        if random.random() < error_rate and level not in ('ERROR', 'FATAL'):
            error_levels = [
                tv for tv in distributions['level'].get('top_values', [])
                if tv['value'] in ('ERROR', 'FATAL')
            ]
            if error_levels:
                vals = [tv['value'] for tv in error_levels]
                wts = [tv['count'] for tv in error_levels]
                level = random.choices(vals, weights=wts, k=1)[0]
            else:
                level = 'ERROR'
        entry['level'] = level
    elif 'level' in template:
        entry['level'] = 'ERROR' if random.random() < error_rate else 'INFO'

    # Fill remaining keys from distributions, preserving original schema
    for key in template:
        if key in ('timestamp', 'level'):
            continue  # Already handled

        if key in distributions:
            entry[key] = _pick_typed(distributions[key])
        else:
            # Rare key not in distributions — copy from template
            entry[key] = template[key]

    return json.dumps(entry, default=str)


def _generate_generic_log(ts, distributions, records, error_rate):
    """Generate log line by sampling from original lines/messages.

    For unknown formats, the best strategy is to reproduce lines that look
    like the originals rather than inventing new structure.
    """
    # If we have original messages, sample from them
    if 'message' in distributions:
        message = _pick_weighted(distributions['message'])
        # Substitute the timestamp portion if the message already contains one
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        # Try to replace leading timestamp-like patterns
        message = re.sub(
            r'^\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}[^\s]*',
            ts_str,
            message,
        )
        return message

    if '_raw' in distributions:
        raw = _pick_weighted(distributions['_raw'])
        return raw

    # Fallback: if we have original records, pick one and format it
    if records:
        rec = random.choice(records)
        raw = rec.get('_raw') or rec.get('message', '')
        if raw:
            return raw

    level = 'ERROR' if random.random() < error_rate else 'INFO'
    return f'[{ts.isoformat()}] [{level}] event processed'


def generate_logs_background(job_id: str, original_path: str, config: dict):
    """Background task for log synthesis."""
    from app.db.database import SessionLocal, Job, JobStatusEnum
    import os

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.progress = 5
        job.message = "Reading log file..."
        db.commit()

        with open(original_path, 'r', errors='replace') as f:
            content = f.read()

        job.progress = 10
        job.message = "Detecting log format..."
        db.commit()

        fmt = LogParser.detect_format(content)

        job.progress = 15
        job.message = f"Parsing {fmt} logs..."
        db.commit()

        records = LogParser.parse_logs(content, fmt)

        job.progress = 25
        job.message = "Analyzing distributions..."
        db.commit()

        distributions = LogParser.analyze_distributions(records)

        job.progress = 35
        job.message = "Generating synthetic logs..."
        db.commit()

        num_lines = config.get('num_log_lines', 1000)
        time_range = config.get('log_time_range_hours', 24)
        error_rate = config.get('log_error_rate', 0.05)

        synthetic_lines = generate_synthetic_logs(
            records, distributions, fmt, num_lines, time_range, error_rate
        )

        job.progress = 80
        job.message = "Saving synthetic logs..."
        db.commit()

        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        ext = '.json' if fmt == 'json' else '.log'
        output_path = os.path.join(output_dir, f"synthetic_logs{ext}")
        with open(output_path, 'w') as f:
            f.write('\n'.join(synthetic_lines))

        # Save results
        analysis = {
            'original_format': fmt,
            'original_lines': len(records),
            'field_distributions': {
                k: {
                    'unique': v.get('unique', 0),
                    'top_5': [tv['value'] for tv in v.get('top_values', [])[:5]],
                }
                for k, v in distributions.items()
            },
        }

        results = {
            'summary': {
                'format': fmt,
                'original_lines': len(records),
                'generated_lines': len(synthetic_lines),
                'time_range_hours': time_range,
                'error_rate': error_rate,
            },
            'analysis': analysis,
            'sample_logs': synthetic_lines[:20],
        }

        results_path = os.path.join(output_dir, "results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        job.progress = 100
        job.status = JobStatusEnum.COMPLETED
        job.message = f"Generated {len(synthetic_lines)} synthetic {fmt} log lines"
        job.rows_generated = len(synthetic_lines)
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Log synthesis failed: {e}")
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)[:500]
            job.message = f"Failed: {str(e)[:200]}"
            db.commit()
    finally:
        db.close()
