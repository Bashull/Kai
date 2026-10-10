#!/usr/bin/env python3
"""Validate a provenance-first Minecraft donor ledger. No network or file writes."""
import argparse
import json
import re
from pathlib import Path

SHA_RE = re.compile(r'^[a-fA-F0-9]{40}$')
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
POLICIES = {'ADAPT', 'STUDY', 'STUDY_ONLY', 'ATTRIBUTION_REVIEW'}
RESTRICTED = {'AGPL-3.0', 'GPL-3.0', 'LGPL-3.0', 'UNVERIFIED', 'NOASSERTION', 'LICENSE_COMPONENT_SPECIFIC'}


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get('donors'), list):
        raise ValueError('donors must be a list')
    seen = set()
    for i, donor in enumerate(data['donors']):
        if not isinstance(donor, dict):
            raise ValueError(f'donor {i} must be an object')
        repo = donor.get('repo')
        if not isinstance(repo, str) or not REPO_RE.fullmatch(repo):
            raise ValueError(f'donor {i} invalid repository')
        if repo.casefold() in seen:
            raise ValueError(f'duplicate repository: {repo}')
        seen.add(repo.casefold())
        if donor.get('url') != 'https://github.com/' + repo:
            raise ValueError(f'URL does not match repository: {repo}')
        if not isinstance(donor.get('branch'), str) or not donor['branch']:
            raise ValueError(f'missing branch: {repo}')
        if not isinstance(donor.get('commit'), str) or not SHA_RE.fullmatch(donor['commit']):
            raise ValueError(f'invalid 40-char commit SHA: {repo}')
        lic = donor.get('license')
        policy = donor.get('policy')
        if not isinstance(lic, str) or not lic:
            raise ValueError(f'unknown license for: {repo}')
        if policy not in POLICIES:
            raise ValueError(f'invalid policy for: {repo}')
        if lic in RESTRICTED and policy == 'ADAPT':
            if lic in {'AGPL-3.0', 'GPL-3.0', 'LGPL-3.0'}:
                raise ValueError(f'copyleft license must have review gate: {repo}')
            raise ValueError(f'license not verified for copying: {repo}')
        for field in ('role', 'license_evidence', 'verified_at'):
            if not isinstance(donor.get(field), str) or not donor[field].strip():
                raise ValueError(f'missing {field}: {repo}')
    return len(data['donors'])


def main():
    ap = argparse.ArgumentParser(description='Validate pinned donor inventory; read-only')
    ap.add_argument('file', type=Path)
    a = ap.parse_args()
    count = validate(json.loads(a.file.read_text(encoding='utf-8')))
    print(json.dumps({'status': 'validated', 'donors': count, 'mode': 'read_only'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
