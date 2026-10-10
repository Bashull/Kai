#!/usr/bin/env python3
"""Create a safe candidate Codex skill; never overwrite or auto-install it."""
import argparse
import json
import re
from pathlib import Path

SLUG = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')


def create_skill(slug, purpose, trigger, out_root):
    if not SLUG.fullmatch(slug) or len(slug) > 50:
        raise ValueError('Invalid skill name; use lowercase hyphenated slug')
    if not purpose.strip() or not trigger.strip() or len(purpose) > 500 or len(trigger) > 250:
        raise ValueError('Purpose and trigger must be concise, nonempty text')
    # Candidate text is untrusted; never let multiline input alter YAML or Markdown structure.
    purpose = ' '.join(purpose.strip().split())
    trigger = ' '.join(trigger.strip().split())
    target = Path(out_root).resolve() / slug
    if target.exists():
        raise FileExistsError('Candidate already exists; no overwrite')
    if not Path(out_root).resolve().is_dir():
        raise FileNotFoundError('Create the dedicated staging directory first')
    text = f'''---
name: {slug}
description: {json.dumps(trigger, ensure_ascii=False)}
---

# {slug}

## Purpose
{purpose.strip()}

## Trigger
{trigger.strip()}

## Safety and workflow
1. Recover the relevant CURRENT and wiki/runbook; compare against existing capabilities first.
2. Inventory dependencies, owner, permissions, and allowed operations. No secret values in this file.
3. Prepare dry-run and a minimal reversible test; never mutate a live Minecraft world by default.
4. Require explicit scope approval for game actions with side effects.
5. Record inputs/outputs, expected vs observed effects, rollback, errors, and provenance.
6. Run tests in staging and update canon only after verified user approval.

## State
CANDIDATE / NOT_TESTED / NOT_PROMOTED. A generated SKILL.md is not a working integration.
'''
    target.mkdir()
    (target / 'SKILL.md').write_text(text, encoding='utf-8')
    manifest = {'name': slug, 'state': 'CANDIDATE', 'source': 'kai-minecraft-skill-forge', 'trigger': trigger, 'purpose': purpose, 'requires': ['testing', 'wiki/runbook reconciliation', 'promotion review']}
    (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument('slug')
    p.add_argument('--purpose', required=True)
    p.add_argument('--trigger', required=True)
    p.add_argument('--staging', required=True)
    args = p.parse_args()
    print(create_skill(args.slug, args.purpose, args.trigger, args.staging))


if __name__ == '__main__':
    main()
