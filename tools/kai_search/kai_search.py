#!/usr/bin/env python3
"""KaiSearch v0.1 - lightweight local file index + safe duplicate detector.

Stdlib-only. Designed for old Windows PCs and large spinning disks.
No command in this version deletes, moves, hardlinks or modifies indexed files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 2
DEFAULT_EXCLUDES = {
    "$Recycle.Bin", "System Volume Information", ".git", "node_modules",
    "__pycache__", ".cache", ".venv", "venv",
}
PREHASH_BYTES = 64 * 1024
HASH_CHUNK = 1024 * 1024


def default_db() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "KaiSearch" / "catalog.db"
    return Path.home() / ".local" / "share" / "KaiSearch" / "catalog.db"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
            ext TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
            root TEXT NOT NULL, prehash TEXT, fullhash TEXT, scan_id INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_files_root ON files(root);
        CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);
        CREATE INDEX IF NOT EXISTS idx_files_hash ON files(fullhash, size);
        CREATE TABLE IF NOT EXISTS file_content(
            file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
            text TEXT NOT NULL DEFAULT '', values_json TEXT NOT NULL DEFAULT '[]',
            search_text TEXT NOT NULL DEFAULT '', status TEXT NOT NULL,
            error TEXT, extractor_id TEXT NOT NULL, extractor_profile TEXT NOT NULL,
            source_size INTEGER NOT NULL, source_mtime_ns INTEGER NOT NULL,
            extracted_ns INTEGER NOT NULL
        );
        """
    )
    fts_cols = {r[1] for r in con.execute("PRAGMA table_info(file_fts)")}
    if fts_cols and "content" not in fts_cols:
        con.executescript("DROP TRIGGER IF EXISTS files_ai; DROP TRIGGER IF EXISTS files_ad; DROP TRIGGER IF EXISTS files_au; DROP TABLE file_fts;")
    con.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
            path, name, content, tokenize='unicode61 remove_diacritics 2'
        );
        DROP TRIGGER IF EXISTS files_ai;
        DROP TRIGGER IF EXISTS files_ad;
        DROP TRIGGER IF EXISTS files_au;
        CREATE TRIGGER files_ai AFTER INSERT ON files BEGIN
            INSERT INTO file_fts(rowid,path,name,content) VALUES(new.id,new.path,new.name,'');
        END;
        CREATE TRIGGER files_ad AFTER DELETE ON files BEGIN
            DELETE FROM file_fts WHERE rowid=old.id;
        END;
        CREATE TRIGGER files_au AFTER UPDATE OF path,name ON files BEGIN
            DELETE FROM file_fts WHERE rowid=old.id;
            INSERT INTO file_fts(rowid,path,name,content)
            VALUES(new.id,new.path,new.name,COALESCE((SELECT search_text FROM file_content WHERE file_id=new.id),''));
        END;
        """
    )
    con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
    n_files = con.execute("SELECT count(*) FROM files").fetchone()[0]
    n_fts = con.execute("SELECT count(*) FROM file_fts").fetchone()[0]
    if n_files != n_fts:
        con.execute("DELETE FROM file_fts")
        con.execute(
            """INSERT INTO file_fts(rowid,path,name,content)
               SELECT f.id,f.path,f.name,COALESCE(c.search_text,'')
               FROM files f LEFT JOIN file_content c ON c.file_id=f.id"""
        )
    con.commit()
    return con

def norm_path(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def walk_files(
    root: str,
    excludes: set[str],
    skip_paths: set[str] | None = None,
) -> Iterable[tuple[str, os.stat_result]]:
    skip_paths = skip_paths or set()

    def onerror(exc: OSError) -> None:
        print(f"[skip] {exc}", file=sys.stderr)

    for current, dirs, files in os.walk(root, topdown=True, onerror=onerror):
        dirs[:] = [d for d in dirs if d not in excludes]
        for name in files:
            path = os.path.join(current, name)
            if norm_path(path) in skip_paths:
                continue
            try:
                st = os.stat(path, follow_symlinks=False)
            except (OSError, PermissionError):
                continue
            if not os.path.isfile(path):
                continue
            yield path, st


def index_root(
    con: sqlite3.Connection,
    root: str,
    excludes: set[str],
    skip_paths: set[str] | None = None,
) -> dict:
    root = norm_path(root)
    if not os.path.isdir(root):
        raise FileNotFoundError(root)
    scan_id = time.time_ns()
    seen = 0
    changed = 0
    started = time.monotonic()
    cur = con.cursor()
    cur.execute("BEGIN")
    try:
        for path, st in walk_files(root, excludes, skip_paths):
            path = norm_path(path)
            name = os.path.basename(path)
            ext = os.path.splitext(name)[1].lower()
            old = cur.execute(
                "SELECT size,mtime_ns FROM files WHERE path=?", (path,)
            ).fetchone()
            same = old and old[0] == st.st_size and old[1] == st.st_mtime_ns
            cur.execute(
                """
                INSERT INTO files(path,name,ext,size,mtime_ns,root,prehash,fullhash,scan_id)
                VALUES(?,?,?,?,?,?,NULL,NULL,?)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,
                    ext=excluded.ext,
                    size=excluded.size,
                    mtime_ns=excluded.mtime_ns,
                    root=excluded.root,
                    prehash=CASE
                        WHEN files.size=excluded.size AND files.mtime_ns=excluded.mtime_ns
                        THEN files.prehash ELSE NULL END,
                    fullhash=CASE
                        WHEN files.size=excluded.size AND files.mtime_ns=excluded.mtime_ns
                        THEN files.fullhash ELSE NULL END,
                    scan_id=excluded.scan_id
                """,
                (path, name, ext, st.st_size, st.st_mtime_ns, root, scan_id),
            )
            if not same:
                file_id = cur.execute("SELECT id FROM files WHERE path=?", (path,)).fetchone()[0]
                cur.execute("DELETE FROM file_content WHERE file_id=?", (file_id,))
                cur.execute("DELETE FROM file_fts WHERE rowid=?", (file_id,))
                cur.execute("INSERT INTO file_fts(rowid,path,name,content) SELECT id,path,name,'' FROM files WHERE id=?", (file_id,))
            seen += 1
            changed += 0 if same else 1
            if seen % 10000 == 0:
                print(f"  indexed {seen:,} files...", file=sys.stderr)
        stale = cur.execute(
            "DELETE FROM files WHERE root=? AND scan_id<>?", (root, scan_id)
        ).rowcount
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {
        "root": root,
        "files_seen": seen,
        "changed_or_new": changed,
        "stale_removed": stale,
        "seconds": round(time.monotonic() - started, 3),
    }


def _refresh_fts_row(con: sqlite3.Connection, file_id: int) -> None:
    con.execute("DELETE FROM file_fts WHERE rowid=?", (file_id,))
    con.execute(
        """INSERT INTO file_fts(rowid,path,name,content)
           SELECT f.id,f.path,f.name,COALESCE(c.search_text,'')
           FROM files f LEFT JOIN file_content c ON c.file_id=f.id
           WHERE f.id=?""",
        (file_id,),
    )


def store_extraction_result(con: sqlite3.Connection, file_id: int, result: dict) -> dict:
    file_row = con.execute("SELECT size,mtime_ns FROM files WHERE id=?", (file_id,)).fetchone()
    if file_row is None:
        raise KeyError(file_id)
    status = str(result.get("status") or "HANDLER_ERROR").upper()
    values = result.get("values") if isinstance(result.get("values"), list) else []
    values = [str(v) for v in values if v is not None]
    text = str(result.get("text") or "") if status == "OK" else ""
    search_text = "\n".join([text, *values]).strip() if status == "OK" else ""
    extractor_id = str(result.get("extractor_id") or "unknown")
    extractor_profile = str(result.get("extractor_profile") or "default")
    error = result.get("error")
    error = None if error is None else str(error)
    con.execute(
        """INSERT INTO file_content(
               file_id,text,values_json,search_text,status,error,extractor_id,extractor_profile,
               source_size,source_mtime_ns,extracted_ns
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(file_id) DO UPDATE SET
               text=excluded.text, values_json=excluded.values_json, search_text=excluded.search_text,
               status=excluded.status, error=excluded.error, extractor_id=excluded.extractor_id,
               extractor_profile=excluded.extractor_profile, source_size=excluded.source_size,
               source_mtime_ns=excluded.source_mtime_ns, extracted_ns=excluded.extracted_ns""",
        (file_id, text, json.dumps(values, ensure_ascii=False), search_text, status, error,
         extractor_id, extractor_profile, file_row["size"], file_row["mtime_ns"], time.time_ns()),
    )
    _refresh_fts_row(con, file_id)
    con.commit()
    return {"file_id": file_id, "status": status, "indexed_chars": len(search_text)}


def extract_file_isolated(path: str, timeout: float = 8.0, worker_script: Path | None = None) -> dict:
    worker = Path(worker_script) if worker_script else Path(__file__).with_name("windows_ifilter_worker.py")
    cmd = [sys.executable, str(worker), str(path)]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "text": "", "values": [], "error": f"timeout after {timeout}s",
                "extractor_id": "subprocess-worker", "extractor_profile": "isolated-v1"}
    if cp.returncode != 0:
        return {"status": "CRASH", "text": "", "values": [], "error": (cp.stderr or "").strip()[-2000:],
                "extractor_id": "subprocess-worker", "extractor_profile": "isolated-v1"}
    payload = None
    for line in reversed(cp.stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            payload = candidate
            break
    if payload is None:
        return {"status": "INVALID_OUTPUT", "text": "", "values": [], "error": "worker emitted no JSON object",
                "extractor_id": "subprocess-worker", "extractor_profile": "isolated-v1"}
    payload.setdefault("status", "HANDLER_ERROR")
    payload.setdefault("text", "")
    payload.setdefault("values", [])
    payload.setdefault("extractor_id", "subprocess-worker")
    payload.setdefault("extractor_profile", "isolated-v1")
    return payload



WINDOWS_IFILTER_EXTRACTOR_ID = "windows-ifilter"
WINDOWS_IFILTER_PROFILE = "init0-gettext-getvalue-filterregistration-v2"


def extract_pending(
    con: sqlite3.Connection,
    timeout: float = 8.0,
    max_files: int | None = None,
    worker_script: Path | None = None,
    extractor_id: str = WINDOWS_IFILTER_EXTRACTOR_ID,
    extractor_profile: str = WINDOWS_IFILTER_PROFILE,
    extensions: set[str] | None = None,
) -> dict:
    normalized_exts = None
    if extensions:
        normalized_exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in extensions}
    rows = con.execute(
        """SELECT f.id,f.path,f.ext,f.size,f.mtime_ns,
                  c.extractor_id,c.extractor_profile,c.source_size,c.source_mtime_ns
           FROM files f LEFT JOIN file_content c ON c.file_id=f.id
           ORDER BY f.id"""
    ).fetchall()
    pending = []
    cached = 0
    for row in rows:
        if normalized_exts is not None and row["ext"] not in normalized_exts:
            continue
        fresh = (
            row["extractor_id"] == extractor_id
            and row["extractor_profile"] == extractor_profile
            and row["source_size"] == row["size"]
            and row["source_mtime_ns"] == row["mtime_ns"]
        )
        if fresh:
            cached += 1
        else:
            pending.append(row)
    selected = pending if max_files is None else pending[:max_files]
    statuses: dict[str, int] = defaultdict(int)
    for row in selected:
        result = extract_file_isolated(row["path"], timeout=timeout, worker_script=worker_script)
        if str(result.get("status", "")).upper() == "OK":
            if result.get("extractor_id") != extractor_id or result.get("extractor_profile") != extractor_profile:
                result = {
                    "status": "INVALID_OUTPUT", "text": "", "values": [],
                    "error": "worker identity/profile mismatch",
                    "extractor_id": extractor_id, "extractor_profile": extractor_profile,
                }
        stored = store_extraction_result(con, row["id"], result)
        statuses[stored["status"]] += 1
    return {
        "processed": len(selected), "cached": cached,
        "pending_remaining": max(0, len(pending) - len(selected)),
        "statuses": dict(statuses),
    }


def fts_query(text: str) -> str:
    tokens = re.findall(r"[\w-]+", text, flags=re.UNICODE)
    return " AND ".join(f'"{t.replace(chr(34), "")}"*' for t in tokens)


def find_files(
    con: sqlite3.Connection,
    text: str,
    ext: str | None = None,
    min_size: int | None = None,
    max_size: int | None = None,
    limit: int = 100,
) -> list[dict]:
    where = ["file_fts MATCH ?"]
    params: list[object] = [fts_query(text)]
    if ext:
        ext = ext if ext.startswith(".") else "." + ext
        where.append("f.ext=?")
        params.append(ext.lower())
    if min_size is not None:
        where.append("f.size>=?")
        params.append(min_size)
    if max_size is not None:
        where.append("f.size<=?")
        params.append(max_size)
    params.append(limit)
    sql = f"""
        SELECT f.path,f.name,f.ext,f.size,f.mtime_ns
        FROM file_fts JOIN files f ON f.id=file_fts.rowid
        WHERE {' AND '.join(where)}
        ORDER BY bm25(file_fts), f.mtime_ns DESC
        LIMIT ?
    """
    return [dict(r) for r in con.execute(sql, params)]


def prehash_file(path: str, size: int) -> str:
    h = hashlib.blake2b(digest_size=16)
    h.update(size.to_bytes(8, "little", signed=False))
    with open(path, "rb", buffering=0) as f:
        h.update(f.read(PREHASH_BYTES))
        if size > PREHASH_BYTES:
            f.seek(max(0, size - PREHASH_BYTES))
            h.update(f.read(PREHASH_BYTES))
    return h.hexdigest()


def fullhash_file(path: str) -> str:
    h = hashlib.blake2b(digest_size=32)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def duplicate_groups(
    con: sqlite3.Connection,
    min_size: int = 1,
    limit_groups: int | None = None,
) -> list[dict]:
    candidates = con.execute(
        """
        SELECT size FROM files
        WHERE size>=?
        GROUP BY size HAVING count(*)>1
        ORDER BY size DESC
        """,
        (min_size,),
    ).fetchall()
    groups: list[dict] = []
    for size_row in candidates:
        size = int(size_row[0])
        rows = con.execute(
            "SELECT id,path,prehash,fullhash FROM files WHERE size=?", (size,)
        ).fetchall()
        pre_groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
        for row in rows:
            path = row["path"]
            try:
                ph = row["prehash"] or prehash_file(path, size)
            except (OSError, PermissionError):
                continue
            if not row["prehash"]:
                con.execute("UPDATE files SET prehash=? WHERE id=?", (ph, row["id"]))
            pre_groups[ph].append(row)
        for pg in pre_groups.values():
            if len(pg) < 2:
                continue
            hash_groups: dict[str, list[str]] = defaultdict(list)
            for row in pg:
                path = row["path"]
                try:
                    fh = row["fullhash"] or fullhash_file(path)
                except (OSError, PermissionError):
                    continue
                if not row["fullhash"]:
                    con.execute("UPDATE files SET fullhash=? WHERE id=?", (fh, row["id"]))
                hash_groups[fh].append(path)
            for fh, paths in hash_groups.items():
                if len(paths) > 1:
                    groups.append(
                        {
                            "size": size,
                            "hash": fh,
                            "count": len(paths),
                            "wasted_bytes": size * (len(paths) - 1),
                            "paths": sorted(paths),
                        }
                    )
                    if limit_groups and len(groups) >= limit_groups:
                        con.commit()
                        return groups
        con.commit()
    return groups


def stats(con: sqlite3.Connection, db_path: Path) -> dict:
    row = con.execute(
        "SELECT count(*),coalesce(sum(size),0),sum(fullhash IS NOT NULL) FROM files"
    ).fetchone()
    dup_candidates = con.execute(
        "SELECT count(*) FROM (SELECT size FROM files GROUP BY size HAVING count(*)>1)"
    ).fetchone()[0]
    return {
        "files": row[0],
        "indexed_bytes": row[1],
        "files_fully_hashed": row[2] or 0,
        "duplicate_size_buckets": dup_candidates,
        "db": str(db_path),
        "db_bytes": db_path.stat().st_size if db_path.exists() else 0,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="kai-search")
    p.add_argument("--db", type=Path, default=default_db())
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("index", help="Incrementally index one or more roots")
    s.add_argument("roots", nargs="+")
    s.add_argument("--exclude", action="append", default=[])

    s = sub.add_parser("find", help="Search indexed names and paths")
    s.add_argument("query")
    s.add_argument("--ext")
    s.add_argument("--min-size", type=int)
    s.add_argument("--max-size", type=int)
    s.add_argument("--limit", type=int, default=100)

    s = sub.add_parser("extract", help="Extract searchable content with isolated Windows IFilters")
    s.add_argument("--limit", type=int)
    s.add_argument("--timeout", type=float, default=8.0)
    s.add_argument("--ext", action="append", default=[])

    s = sub.add_parser("dupes", help="Find exact duplicates; never deletes")
    s.add_argument("--min-size", type=int, default=1)
    s.add_argument("--limit-groups", type=int)

    sub.add_parser("stats")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    con = connect(args.db)
    try:
        if args.cmd == "index":
            excludes = set(DEFAULT_EXCLUDES) | set(args.exclude)
            db_abs = norm_path(args.db)
            skip_paths = {db_abs, db_abs + "-wal", db_abs + "-shm"}
            out = [index_root(con, r, excludes, skip_paths) for r in args.roots]
        elif args.cmd == "find":
            out = find_files(con, args.query, args.ext, args.min_size, args.max_size, args.limit)
        elif args.cmd == "extract":
            out = extract_pending(con, timeout=args.timeout, max_files=args.limit, extensions=set(args.ext) or None)
        elif args.cmd == "dupes":
            out = duplicate_groups(con, args.min_size, args.limit_groups)
        else:
            out = stats(con, args.db)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
