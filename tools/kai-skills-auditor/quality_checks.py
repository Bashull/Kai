"""Read-only descriptive checks with explicit grain, denominators and UTC clock.

No thresholds, data repairs, source queries or quality certification are inferred.
Only aggregate evidence is returned; source keys and row values are not emitted.
"""
import argparse
import collections
import datetime as dt
import json
from pathlib import Path


def _rows_and_keys(rows, keys):
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Rows must be a JSON array of objects')
    if (not isinstance(keys, (list, tuple)) or not keys
            or any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys)):
        raise ValueError('Explicit unique nonempty key field names required')


def _key(row, keys, normalize=False):
    values = [row.get(k) for k in keys]
    if any(v is None for v in values): return None
    if any(isinstance(v, (dict, list)) for v in values):
        raise ValueError('Key fields must contain scalar values')
    if normalize: values = [v.strip().casefold() if isinstance(v, str) else v for v in values]
    return json.dumps(values, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def profile_keys(rows, keys, normalize_strings=False):
    _rows_and_keys(rows, keys); n = len(rows)
    counts = collections.Counter(); missing = 0; normalized_to_raw = {}
    for row in rows:
        raw = _key(row, keys)
        if raw is None: missing += 1; continue
        counts[raw] += 1
        if normalize_strings:
            normalized_to_raw.setdefault(_key(row, keys, True), set()).add(raw)
    affected = sum(c for c in counts.values() if c > 1)
    excess = sum(c - 1 for c in counts.values() if c > 1)
    return {'status':'DESCRIPTIVE_NOT_QUALITY_CERTIFICATION' if n else 'EMPTY',
        'row_count':n, 'key_fields':list(keys), 'valid_key_rows':n-missing,
        'missing_key_rows':missing, 'missing_key_share_all_rows':missing/n if n else None,
        'distinct_nonmissing_keys':len(counts), 'duplicate_groups':sum(c>1 for c in counts.values()),
        'duplicate_excess_rows':excess, 'duplicate_affected_rows':affected,
        'duplicate_affected_share_all_rows':affected/n if n else None,
        'normalization_applied_to_primary_result':False,
        'normalization_collision_groups':sum(len(v)>1 for v in normalized_to_raw.values()) if normalize_strings else None,
        'normalization_semantics':'OPTIONAL_STRIP_CASEFOLD_CANDIDATES_ONLY',
        'null_semantics':'MISSING_KEYS_COUNTED_SEPARATELY_NOT_VALID_DUPLICATE_KEYS',
        'coverage':'EXACT_WITHIN_SUPPLIED_ROWS_NOT_A_CLAIM_ABOUT_SOURCE_POPULATION'}


def _timestamp(value):
    if not isinstance(value, str): raise ValueError('ISO timestamp string required')
    parsed = dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ValueError('Timestamp timezone required')
    return parsed.astimezone(dt.timezone.utc)


def profile_freshness(rows, field, as_of):
    _rows_and_keys(rows, [field]); now = _timestamp(as_of)
    valid = []; missing = invalid = future = 0
    for row in rows:
        value = row.get(field)
        if value is None: missing += 1; continue
        try: stamp = _timestamp(value)
        except (ValueError, TypeError, OverflowError): invalid += 1; continue
        if stamp > now: future += 1
        else: valid.append(stamp)
    latest = max(valid) if valid else None
    return {'field':field, 'as_of_utc':now.isoformat(), 'row_count':len(rows),
        'missing_rows':missing, 'invalid_or_timezone_missing_rows':invalid, 'future_rows':future,
        'latest_nonfuture_utc':latest.isoformat() if latest else None,
        'age_seconds':(now-latest).total_seconds() if latest else None,
        'status':'DESCRIPTIVE_NOT_QUALITY_CERTIFICATION' if latest else 'NO_VALID_NONFUTURE_TIMESTAMP',
        'event_vs_load_time':'CALLER_MUST_DECLARE_WHICH_CLOCK_THIS_FIELD_REPRESENTS'}


def profile_join(left, right, left_keys, right_keys):
    _rows_and_keys(left,left_keys); _rows_and_keys(right,right_keys)
    if len(left_keys) != len(right_keys): raise ValueError('Join key arity mismatch')
    parent = collections.Counter(k for row in right if (k := _key(row,right_keys)) is not None)
    inner = outer = missing = orphan = expanded = 0
    for row in left:
        key = _key(row,left_keys)
        if key is None: missing += 1; matches = 0
        else:
            matches = parent[key]
            if matches == 0: orphan += 1
        if matches > 1: expanded += 1
        inner += matches; outer += max(1,matches)
    return {'left_rows':len(left), 'right_rows':len(right),
        'inner_join_rows':inner, 'left_join_rows':outer,
        'missing_left_key_rows':missing, 'unmatched_nonmissing_left_rows':orphan,
        'left_rows_with_multiple_right_matches':expanded,
        'right_duplicate_key_groups':sum(c>1 for c in parent.values()),
        'null_semantics':'SQL_STYLE_NULL_KEYS_DO_NOT_MATCH',
        'status':'DESCRIPTIVE_NOT_QUALITY_CERTIFICATION'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('--keys',nargs='+',required=True)
    p.add_argument('--normalize-strings',action='store_true')
    p.add_argument('--time-field');p.add_argument('--as-of')
    p.add_argument('--right',type=Path);p.add_argument('--right-keys',nargs='+')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.time_field and not a.as_of:p.error('--time-field requires explicit timezone-aware --as-of')
    if bool(a.right) != bool(a.right_keys):p.error('--right and --right-keys must be supplied together')
    if a.output and (a.output.exists() or a.output.is_symlink()):p.error('Output must be a new file')
    rows=json.loads(a.input.read_bytes()); result={'keys':profile_keys(rows,a.keys,a.normalize_strings)}
    if a.time_field:result['freshness']=profile_freshness(rows,a.time_field,a.as_of)
    if a.right:result['join']=profile_join(rows,json.loads(a.right.read_bytes()),a.keys,a.right_keys)
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if a.output:
        with a.output.open('x',encoding='utf-8') as f:f.write(text)
    else:print(text,end='')


if __name__=='__main__':main()
