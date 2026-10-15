# KAI Skills Auditor v0.4

Offline inspection and reconciliation tools for an explicitly scoped collection of skill instruction documents. Donor scripts are read as data, never executed by the auditor. Provider services, credentials and functional validation are outside the archive's integrity claims.

Run `python -m unittest -v` in this directory. Python 3.10+ is required. PyYAML enables full frontmatter parsing for the auditor and bundle builder; the standalone bundle verifier uses the standard library.

`kai_skill_auditor.py --source INPUT --out NEW_OUTPUT --expected 847` reads existing `skills_*.json` capture batches. It rejects empty exact-root bodies, conflicting source revisions, missing indices, duplicate identities, invalid indices and existing output directories before producing a candidate archive.

`bundle_io.py ARCHIVE.zip` verifies complete manifest coverage, hashes, CRC and archive paths. `--id ID --target NEW_LAB` previews an isolated copy; `--apply` copies only those selected IDs. Existing targets, active skill roots and conflicting selected names are rejected. This is a lab copier, not a production installer.

`build_bundle.py` is a task-specific reproducible builder consuming the six supplied archives and explicit local/cloud/provider recovery receipts. It is not a downloader or a universal upstream updater. Source archives, private catalogs and third-party resource collections are deliberately excluded from this Git repository.

Validation records: 20 regression tests, actual 847-root capture reconciliation on Termux, and independent archive/hash/staging checks. These are tool and packaging checks, not functional tests of 847 provider skills.
