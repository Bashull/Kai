#!/usr/bin/env python3
"""On-demand Samsung control: reuse authorized ADB, live capture and Nexus.

No daemon, network listener, rooting, account login or automatic permission grant.
UI mutations require a caller-specified foreground package. Effect verification
is a separate observation, never implied by an input command's exit code.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sqlite3
import struct
import subprocess
import sys
import time
import urllib.request
import uuid

VERSION = "0.1.0"
HOME_PATH = Path.home()
STATE = HOME_PATH / ".kai_mobile/phone-control"
SHARED = Path("/storage/emulated/0")
ROOTS = {n: SHARED / n for n in ("Download", "Documents", "DCIM", "Pictures", "Movies", "Music")}
ROOTS["AndroidData"] = SHARED / "Android/data"
KEYS = {"BACK": 4, "HOME": 3, "RECENTS": 187, "ENTER": 66}


def package(value):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+", value):
        raise ValueError("invalid_package")
    return value


def serial_from_devices(text):
    ready = []
    for line in text.splitlines():
        bits = line.split()
        if len(bits) >= 2 and bits[1] == "device":
            ready.append(bits[0])
    if len(ready) != 1 or not re.fullmatch(r"127\.0\.0\.1:[0-9]{1,5}", ready[0]):
        raise ValueError("need_one_authorized_local_adb_device")
    if not 1 <= int(ready[0].split(":")[1]) <= 65535:
        raise ValueError("invalid_adb_port")
    return ready[0]


def foreground(text):
    for line in text.splitlines():
        if "topResumedActivity=" in line or "mResumedActivity:" in line:
            m = re.search(r"\bu\d+\s+([A-Za-z0-9_.]+)/([^\s}]+)", line)
            if m:
                return {"package": m.group(1), "component": m.group(1) + "/" + m.group(2)}
    return None


def browse_path(root, relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '\0' in relative:
        raise ValueError("invalid_relative_path")
    return str(ROOTS[root] / str(rel))


def run(argv, timeout=12, binary=False):
    # ADB shell otherwise drains the CLI's stdin during preflight, stealing text.
    p = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    if p.returncode:
        # No command arguments, stdout, input contents or private error payloads.
        raise RuntimeError("command_failed_exit_" + str(p.returncode))
    return p.stdout if binary else p.stdout.decode("utf-8", "replace")


class ADB:
    def __init__(self):
        self.serial = serial_from_devices(run(["adb", "devices", "-l"]))
        self.base = ["adb", "-s", self.serial]
        if self.shell(["getprop", "ro.product.model"]).strip() != "SM-S928B":
            raise ValueError("unexpected_device_model")

    def shell(self, args, timeout=12):
        # ADB shell has a remote shell boundary even when subprocess has shell=False.
        return run(self.base + ["shell", shlex.join([str(a) for a in args])], timeout)

    def foreground(self):
        return foreground(self.shell(["dumpsys", "activity", "activities"]))

    def guard(self, expected):
        current = self.foreground()
        if current is None or current["package"] != package(expected):
            raise ValueError("foreground_mismatch_or_unknown")
        return current


def live(path, payload=None, timeout=5):
    # The existing private pointer is resolved only in memory; never serialized.
    token = (HOME_PATH / ".kai_mobile/kai-live-token").read_text().strip()
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request("http://127.0.0.1:7190" + path, data=data,
                                 headers={"Authorization": "Bearer " + token,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def private_write(path, data):
    path = Path(path).expanduser().absolute()
    # Evidence may contain screen contents: keep under private Termux home.
    if not path.parent.resolve().is_relative_to(HOME_PATH.resolve()):
        raise ValueError("evidence_requires_private_home_path")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def nexus_search(query, limit):
    dbpath = HOME_PATH / "KAI_VISUAL_STUDIO/STATE/nexus_index.sqlite"
    with closing(sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        count = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        rows = [dict(r) for r in db.execute(
            "SELECT path,name,kind,size,mtime_ns,scanned_ns FROM files "
            "WHERE instr(lower(name),lower(?))>0 ORDER BY name LIMIT ?", (query, limit + 1))]
    return {"scope": "EXISTING_NEXUS_INDEX_PARTIAL", "indexed_records": count,
            "query_matches_truncated": len(rows) > limit, "matches": rows[:limit],
            "note": "Index metadata is historical; recheck an item before acting."}


def live_find(query, root, limit, budget_s):
    start = time.monotonic()
    pending = [ROOTS[root]]
    found, errors, scanned = [], 0, 0
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for item in entries:
                    if time.monotonic() - start >= budget_s:
                        return {"scope": "BOUNDED_LIVE", "complete": False, "reason": "time_budget",
                                "matches": found, "entries": scanned, "unreadable": errors}
                    scanned += 1
                    if item.name.startswith(".") or item.is_symlink():
                        continue
                    if item.is_dir(follow_symlinks=False):
                        pending.append(Path(item.path))
                    elif query.casefold() in item.name.casefold():
                        st = item.stat(follow_symlinks=False)
                        found.append({"path": item.path, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns})
                        if len(found) >= limit:
                            return {"scope": "BOUNDED_LIVE", "complete": False, "reason": "result_limit",
                                    "matches": found, "entries": scanned, "unreadable": errors}
        except OSError:
            errors += 1
    return {"scope": "VISIBLE_REGULAR_FILES_ONE_ROOT", "complete": errors == 0,
            "matches": found, "entries": scanned, "unreadable": errors,
            "excludes": ["dotfiles", "symlinks", "archive contents"]}


def execute(a):
    if a.command == "search":
        return nexus_search(a.query, a.limit)
    if a.command == "find":
        return live_find(a.query, a.root, a.limit, a.budget)
    adb = ADB()
    if a.command == "status":
        result = {"version": VERSION, "serial": adb.serial, "model": "SM-S928B",
                  "shell_uid": adb.shell(["id", "-u"]).strip(), "foreground": adb.foreground(),
                  "location_enabled": adb.shell(["cmd", "location", "is-location-enabled"]).strip()}
        try:
            s = live("/status")
            result["existing_live"] = {k:s.get(k) for k in ("ok", "sequence", "frame_age_ms", "control_alive", "preferred_input", "logical_size", "frame_size", "fps")}
        except Exception as e:
            result["existing_live"] = {"available": False, "error_type": type(e).__name__}
        return result
    if a.command == "apps":
        args = ["pm", "list", "packages", "--user", "0"] + (["-3"] if a.user else [])
        values = sorted(l[8:].strip() for l in adb.shell(args).splitlines() if l.startswith("package:"))
        return {"scope": "USER_0_VISIBLE_PACKAGES", "total": len(values),
                "packages": [p for p in values if a.query.casefold() in p.casefold()]}
    if a.command == "roots":
        result = []
        for name, path in ROOTS.items():
            row = {"name": name, "path": str(path)}
            for actor in ["termux", "adb_shell"]:
                try:
                    if actor == "termux":
                        with os.scandir(path) as items:
                            next(items, None)
                    else:
                        adb.shell(["ls", "-A", str(path)])
                    row[actor] = "LISTABLE"
                except (OSError, RuntimeError):
                    row[actor] = "UNAVAILABLE_OR_DENIED"
            result.append(row)
        return {"roots": result, "scope": "seven_known_shared_roots"}
    if a.command == "browse":
        path = browse_path(a.root, a.relative)
        data = adb.shell(["find",path,"-mindepth","1","-maxdepth","1","-print0"])
        entries = sorted(x for x in data.split('\0') if x)
        return {"scope":"ADB_ONE_DIRECTORY", "path":path, "total_entries":len(entries),
                "truncated":len(entries)>a.limit,"entries":entries[:a.limit],
                "note":"A listed directory does not prove access to every descendant."}
    if a.command == "screen":
        data = run(adb.base + ["exec-out", "screencap", "-p"], binary=True)
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("invalid_screenshot")
        meta = private_write(a.out or STATE / ("screen-" + uuid.uuid4().hex + ".png"), data)
        meta["dimensions"] = struct.unpack(">II", data[16:24])
        return meta
    if a.command == "ui":
        temp = "/data/local/tmp/kai-phone-" + uuid.uuid4().hex + ".xml"
        try:
            adb.shell(["uiautomator", "dump", "--compressed", temp], timeout=20)
            data = adb.shell(["cat", temp]).encode()
        finally:
            adb.shell(["rm", "-f", temp])
        if b"<hierarchy" not in data:
            raise ValueError("invalid_ui_dump")
        return private_write(a.out or STATE / ("ui-" + uuid.uuid4().hex + ".xml"), data)
    if a.command == "launch":
        target = package(a.package)
        text = adb.shell(["cmd", "package", "resolve-activity", "--brief", "--user", "0",
                          "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", target])
        candidates = [v.strip() for v in text.splitlines() if v.strip().startswith(target + "/")]
        if len(candidates) != 1 or not re.fullmatch(r"[A-Za-z0-9_.$/]+", candidates[0]):
            raise ValueError("no_unique_launcher")
        adb.shell(["am", "start", "-W", "-n", candidates[0]])
        post = adb.foreground()
        return {"sent": True, "foreground_verified": bool(post and post["package"] == target), "foreground": post}
    adb.guard(a.expect_package)
    if a.command in ("tap", "swipe"):
        sizes = re.findall(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", adb.shell(["wm", "size"]))
        if not sizes:
            raise ValueError("unknown_display_dimensions")
        width, height = map(int, sizes[-1])
        coords = [(a.x, a.y)] if a.command == "tap" else [(a.x1, a.y1), (a.x2, a.y2)]
        if any(x < 0 or y < 0 or x >= width or y >= height for x,y in coords):
            raise ValueError("coordinates_out_of_bounds")
    if a.command == "tap":
        action = {"type":"tap", "x":a.x, "y":a.y, "space":"logical"}
        shell_args = ["input", "tap", str(a.x), str(a.y)]
    elif a.command == "swipe":
        action = {"type":"swipe", "x1":a.x1,"y1":a.y1,"x2":a.x2,"y2":a.y2,"duration_ms":a.duration,"space":"logical"}
        shell_args = ["input", "swipe", *map(str, [a.x1,a.y1,a.x2,a.y2,a.duration])]
    elif a.command == "key":
        action = {"type":"key", "keycode":KEYS[a.key]}
        shell_args = ["input", "keyevent", str(KEYS[a.key])]
    else:
        text = sys.stdin.read(4097).removesuffix("\n")
        if not text or len(text) > 4096 or "\0" in text:
            raise ValueError("invalid_text_length")
        action = {"type":"text", "text":text}
        if a.transport == "adb" and not re.fullmatch(r"[A-Za-z0-9 ._/-]{1,512}", text):
            raise ValueError("adb_text_requires_simple_ascii_use_live_for_unicode")
        shell_args = ["input", "text", text.replace(" ", "%s")]
    adb.guard(a.expect_package)
    started = time.monotonic()
    if a.transport == "live":
        result = live("/act", {"actions":[action]}, timeout=12)
        if result.get("ok") is not True:
            raise RuntimeError("live_input_rejected")
        return {"sent":True, "effect_verified":False, "transport":"existing_live",
                "elapsed_ms":round((time.monotonic()-started)*1000,2), "receipt":result}
    adb.shell(shell_args)
    return {"sent":True,"effect_verified":False,"transport":"adb",
            "elapsed_ms":round((time.monotonic()-started)*1000,2)}


def bounded_int(low, high):
    def check(s):
        v = int(s)
        if not low <= v <= high:
            raise argparse.ArgumentTypeError("out of bounds")
        return v
    return check


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status"); sub.add_parser("roots")
    s=sub.add_parser("browse");s.add_argument("root",choices=ROOTS)
    s.add_argument("--relative",default=".");s.add_argument("--limit",type=bounded_int(1,200),default=50)
    s = sub.add_parser("apps"); s.add_argument("query", nargs="?", default=""); s.add_argument("--user", action="store_true")
    for cmd in ["search", "find"]:
        s=sub.add_parser(cmd);s.add_argument("query");s.add_argument("--limit", type=bounded_int(1,200), default=30)
        if cmd=="find":
            s.add_argument("--root", choices=ROOTS, default="Download");s.add_argument("--budget", type=bounded_int(1,30),default=10)
    for cmd in ["screen", "ui"]:
        s=sub.add_parser(cmd);s.add_argument("--out",type=Path)
    s=sub.add_parser("launch");s.add_argument("package")
    for cmd in ["tap","swipe","key","text"]:
        s=sub.add_parser(cmd);s.add_argument("--expect-package", required=True)
        s.add_argument("--transport",choices=["adb","live"],default="adb")
        if cmd=="tap":
            s.add_argument("x",type=int);s.add_argument("y",type=int)
        elif cmd=="swipe":
            for n in ["x1","y1","x2","y2"]:s.add_argument(n,type=int)
            s.add_argument("--duration",type=bounded_int(20,5000),default=250)
        elif cmd=="key":s.add_argument("key",choices=KEYS)
    return p


def main():
    os.umask(0o077)
    a=parser().parse_args()
    try:
        result=execute(a);code=0
    except Exception as e:
        # Keep values of text, queries, tokens and private subprocess output out of logs.
        result={"ok":False,"error":str(e) if isinstance(e,ValueError) else type(e).__name__};code=2
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (STATE/"audit.jsonl").open("a") as f:
        f.write(json.dumps({"at":time.time(),"command":a.command,"exit":code,"version":VERSION})+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2));return code


if __name__ == "__main__":
    raise SystemExit(main())
