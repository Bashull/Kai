"""Normalize optional Agent Skills metadata to the standard string-to-string map.

Keep operational body bytes unchanged; retain typed input in an external receipt.
"""
import json
import re
import yaml


def normalize_metadata(data):
    text = data.decode('utf-8')
    match = re.match(r'^---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        raise ValueError('Valid staged frontmatter required')
    fm = yaml.safe_load(match[1])
    metadata = fm.get('metadata')
    if 'metadata' not in fm:
        return data, None
    if isinstance(metadata, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()):
        return data, None
    original = metadata
    if not isinstance(metadata, dict):
        normalized = {'kai-original-metadata-json': json.dumps(metadata, ensure_ascii=False, sort_keys=True)}
    else:
        if any(not isinstance(k, str) for k in metadata):
            raise ValueError('Non-string metadata keys require explicit reconciliation')
        normalized = {k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True)
                      for k, v in metadata.items()}
    fm['metadata'] = normalized
    body = text[match.end():]
    header = '---\n' + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000) + '---\n'
    result = (header + body).encode('utf-8')
    # Assert the exact byte span after the original delimiter survived.
    result_match = re.match(br'^---\n(.*?)\n---\n', result, re.S)
    if result[result_match.end():] != body.encode('utf-8'):
        raise ValueError('Operational body changed during metadata normalization')
    return result, {'original_metadata': original, 'normalized_metadata': normalized,
                    'body_bytes_unchanged': True, 'typed_values_encoded_as_json_strings': True}
