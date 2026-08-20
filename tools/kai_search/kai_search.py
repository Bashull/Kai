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
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = 1
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
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            ext TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            root TEXT NOT NULL,
            prehash TEXT,
            fullhash TEXT,
            scan_id INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_files_root ON files(root);
        CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);
        CREATE INDEX IF NOT EXISTS idx_files_hash ON files(fullhash, size);
        CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
            path, name,
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
            INSERT INTO file_fts(rowid,path,name) VALUES(new.id,new.path,new.name);
        END;
        CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
            DELETE FROM file_fts WHERE rowid=old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE OF path,name ON files BEGIN
            DELETE FROM file_fts WHERE rowid=old.id;
            INSERT INTO file_fts(rowid,path,name) VALUES(new.id,new.path,new.name);
        END;
        """
    )
    con.execute(
        "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
        (str(SCHEMA_VERSION),),
    )
    # Repair FTS if an interrupted migration left counts mismatched.
    n_files = con.execute("SELECT count(*) FROM files").fetchone()[0]
    n_fts = con.execute("SELECT count(*) FROM file_fts").fetchone()[0]
    if n_files != n_fts:
        con.execute("DELETE FROM file_fts")
        con.execute("INSERT INTO file_fts(rowid,path,name) SELECT id,path,name FROM files")
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
