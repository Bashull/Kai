# KaiSearch v0.2

Unified local search catalog + exact duplicate detector for the Kai ecosystem.

## Status

`STAGING / VERIFIED_SCOPE`. Search-by-content and exact-duplicate primitives work; donor retirement is not yet authorized.

## Why it exists

The old PC is bottlenecked by spinning disks. Running several independent scanners/indexers means repeated I/O. KaiSearch starts consolidating file discovery, metadata search and duplicate analysis around one SQLite catalog.

## Capability DNA

### From Windows Search / SearchIndexer
- Persistent local catalogue.
- Fast query after indexing.
- Search by file name/path, extracted content and properties.
- Incremental re-scan model.
- Reuse registered Windows IFilters directly without querying `SystemIndex`.
- One extraction per isolated subprocess with timeout/crash containment.

### From dupeGuru
- Duplicate discovery without assuming equal names.
- Cache work so unchanged files are not re-hashed.
- Preserve exclusions and user-selected roots.
- Exact duplicate verification by content.

### Transfer / improvement
- One metadata catalogue shared by search and duplicate detection.
- Size buckets eliminate unique-size files before reading contents.
- 64 KiB head/tail prehash eliminates most remaining candidates.
- Full BLAKE2b hash runs only on surviving candidates.
- Safe by design: v0.2 has no delete, move, hardlink or overwrite command.
- `UNKNOWN != MATCH`; extractor failures never enter FTS as content.
- Content cache key: size + mtime_ns + extractor_id + extractor_profile.

## Runtime

Python 3.12+ and SQLite with FTS5. No third-party Python dependencies.

```powershell
python kai_search.py --db .\catalog.db index C:\Users\ASIER\Documents D:\
python kai_search.py --db .\catalog.db extract --limit 500 --timeout 8
python kai_search.py --db .\catalog.db extract --ext pdf --ext docx
python kai_search.py --db .\catalog.db find "model sheet" --ext png
python kai_search.py --db .\catalog.db dupes --min-size 1048576
python kai_search.py --db .\catalog.db stats
```

## Safety gates before retiring donors

1. Verify search coverage against Windows Search on representative queries.
2. Add content extraction/full-text coverage where needed; v0.1 indexes names and paths only.
3. Verify duplicate groups against dupeGuru on controlled folders.
4. Preserve dupeGuru settings/exclusions/hash cache and donor source/genealogy.
5. Measure HDD I/O and index size.
6. Only then consider disabling `WSearch` or uninstalling dupeGuru.

## Genealogy

- Windows Search / `SearchIndexer.exe`: Windows capability donor; queried via documented `SystemIndex` APIs during transition.
- dupeGuru 4.3.1: GPL-3.0 donor used for capability study. No dupeGuru source code is copied into this implementation.
- Czkawka/Krokiet: algorithmic reference for staged duplicate filtering (size → prehash → full hash), studied as an external donor/reference.

The implementation in this directory is original stdlib Python unless a future file explicitly records another origin/license.

## Verified content extraction scope (Windows)

Direct IFilter extraction without `SearchIndexer` is verified for TXT, RTF, DOCX, XLSX (XlsxWriter-produced fixture), PPTX, PDF, HTML, XML, EML, MHT, URL, ZIP, ODT, ODS and valid ODP. PDF required `FilterRegistration` plus `IPersistStream`; valid ODP required a real page layout/master page.

Controlled 15-format benchmark on the old HDD PC: 15/15 extraction statuses `OK`, all 15 sentinels recovered through FTS, cold extraction ~3.16 s, immediate cached pass ~0.0002 s. These figures are evidence for the synthetic corpus only, not a full-disk performance claim.

## Remaining donor-retirement gates

- Representative full-tree comparison against Windows Search queries/ranking/coverage.
- Controlled large-folder duplicate comparison against dupeGuru.
- HDD I/O and catalogue-size measurements on real roots.
- Failure/recovery soak testing before disabling `WSearch` or uninstalling dupeGuru.
