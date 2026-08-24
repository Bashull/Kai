#!/usr/bin/env python3
"""Isolated Windows IFilter worker for KaiSearch.

Runs one file per process. It never touches the KaiSearch catalog.
"""
from __future__ import annotations

import ctypes
import json
import os
import sys

HRESULT = ctypes.c_long
ULONG = ctypes.c_ulong
LCID = ctypes.c_ulong
CHUNK_TEXT = 0x1
CHUNK_VALUE = 0x2
EXTRACTOR_ID = "windows-ifilter"
EXTRACTOR_PROFILE = "init0-gettext-getvalue-filterregistration-v2"


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]
class PROPSPEC_UNION(ctypes.Union):
    _fields_ = [("propid", ULONG), ("lpwstr", ctypes.c_wchar_p)]


class PROPSPEC(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("ulKind", ULONG), ("u", PROPSPEC_UNION)]


class FULLPROPSPEC(ctypes.Structure):
    _fields_ = [("guidPropSet", GUID), ("psProperty", PROPSPEC)]


class STAT_CHUNK(ctypes.Structure):
    _fields_ = [("idChunk", ULONG), ("breakType", ctypes.c_int),
                ("flags", ctypes.c_int), ("locale", LCID),
                ("attribute", FULLPROPSPEC), ("idChunkSource", ULONG),
                ("cwcStartSource", ULONG), ("cwcLenSource", ULONG)]


WINFUNCTYPE = ctypes.WINFUNCTYPE
ReleaseProto = WINFUNCTYPE(ULONG, ctypes.c_void_p)
InitProto = WINFUNCTYPE(HRESULT, ctypes.c_void_p, ULONG, ULONG,
                        ctypes.POINTER(FULLPROPSPEC), ctypes.POINTER(ULONG))
GetChunkProto = WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(STAT_CHUNK))
GetTextProto = WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(ULONG),
                           ctypes.POINTER(ctypes.c_wchar))
GetValueProto = WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))

QueryInterfaceProto = WINFUNCTYPE(
    HRESULT, ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)
)
PersistFileLoadProto = WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong)
PersistStreamLoadProto = WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_void_p)

class FILTERED_DATA_SOURCES(ctypes.Structure):
    _fields_ = [("pwcsExtension", ctypes.c_wchar_p), ("pwcsMime", ctypes.c_wchar_p),
                ("pClsid", ctypes.POINTER(GUID)), ("pwcsOverride", ctypes.c_wchar_p)]

PrivateLoadProto = WINFUNCTYPE(
    HRESULT, ctypes.c_void_p, ctypes.POINTER(FILTERED_DATA_SOURCES), ctypes.c_int,
    ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_void_p),
)


def hr_u32(value: int) -> int:
    return ctypes.c_uint32(value).value


def hr_hex(value: int) -> str:
    return f"0x{hr_u32(value):08X}"


def succeeded(value: int) -> bool:
    return value >= 0


def method(obj, index, proto):
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return proto(vtbl[index])


def normalize_text(value: str) -> str:
    value = value.split("\x00", 1)[0]
    return "".join(ch for ch in value if ch in "\r\n\t" or ord(ch) >= 32)
def propvariant_to_string(prop_ptr) -> str:
    propsys = ctypes.WinDLL("propsys.dll")
    fn = propsys.PropVariantToStringAlloc
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    fn.restype = HRESULT
    out = ctypes.c_void_p()
    hr = int(fn(prop_ptr, ctypes.byref(out)))
    if not succeeded(hr) or not out.value:
        return ""
    try:
        return normalize_text(ctypes.cast(out, ctypes.c_wchar_p).value or "")
    finally:
        ctypes.windll.ole32.CoTaskMemFree(out)


def free_propvariant(prop_ptr) -> None:
    if not prop_ptr:
        return
    ctypes.windll.ole32.PropVariantClear(prop_ptr)
    ctypes.windll.ole32.CoTaskMemFree(prop_ptr)



CLSID_FILTER_REGISTRATION = "{9E175B8D-F52A-11D8-B9A5-505054503030}"
IID_LOAD_FILTER_PRIVATE = "{40BDBD34-780B-48D3-9BB6-12EBD4AD2E75}"
IID_IPERSISTFILE = "{0000010b-0000-0000-C000-000000000046}"
IID_IPERSISTSTREAM = "{00000109-0000-0000-C000-000000000046}"


def guid(text: str) -> GUID:
    value = GUID()
    fn = ctypes.windll.ole32.CLSIDFromString
    fn.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
    fn.restype = HRESULT
    hr = int(fn(text, ctypes.byref(value)))
    if not succeeded(hr):
        raise OSError(hr_hex(hr))
    return value


def query_interface(obj, iid_text: str):
    qi = method(obj, 0, QueryInterfaceProto)
    iid = guid(iid_text)
    out = ctypes.c_void_p()
    hr = int(qi(obj, ctypes.byref(iid), ctypes.byref(out)))
    return hr, out


def persist_file_load(obj, path: str):
    hr, persist = query_interface(obj, IID_IPERSISTFILE)
    meta = {"qi_ipersistfile": hr_hex(hr)}
    if not succeeded(hr) or not persist.value:
        return False, meta
    release = method(persist, 2, ReleaseProto)
    load = method(persist, 5, PersistFileLoadProto)
    try:
        hr = int(load(persist, path, 0))
        meta["ipersistfile_load"] = hr_hex(hr)
        return succeeded(hr), meta
    finally:
        release(persist)


def persist_stream_load(obj, path: str):
    hr, persist = query_interface(obj, IID_IPERSISTSTREAM)
    meta = {"qi_ipersiststream": hr_hex(hr)}
    if not succeeded(hr) or not persist.value:
        return False, meta
    stream = ctypes.c_void_p()
    create = ctypes.windll.shlwapi.SHCreateStreamOnFileEx
    create.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int,
                       ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    create.restype = HRESULT
    hs = int(create(path, 0x40, 0, 0, None, ctypes.byref(stream)))
    meta["stream_create"] = hr_hex(hs)
    release_persist = method(persist, 2, ReleaseProto)
    try:
        if not succeeded(hs) or not stream.value:
            return False, meta
        load = method(persist, 5, PersistStreamLoadProto)
        hl = int(load(persist, stream))
        meta["ipersiststream_load"] = hr_hex(hl)
        return succeeded(hl), meta
    finally:
        if stream.value:
            method(stream, 2, ReleaseProto)(stream)
        release_persist(persist)



def load_registered_filter(path: str):
    clsid = guid(CLSID_FILTER_REGISTRATION)
    iid = guid(IID_LOAD_FILTER_PRIVATE)
    reg = ctypes.c_void_p()
    co = ctypes.windll.ole32.CoCreateInstance
    co.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_ulong,
                   ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
    co.restype = HRESULT
    hr = int(co(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(reg)))
    meta = {"registration_cocreate": hr_hex(hr)}
    if not succeeded(hr) or not reg.value:
        return None, meta
    release_reg = method(reg, 2, ReleaseProto)
    load = method(reg, 6, PrivateLoadProto)
    sources = FILTERED_DATA_SOURCES(os.path.splitext(path)[1], None, None, None)
    filter_clsid = GUID(); is_private = ctypes.c_int(); obj = ctypes.c_void_p()
    try:
        hr = int(load(reg, ctypes.byref(sources), 0, ctypes.byref(filter_clsid),
                      ctypes.byref(is_private), ctypes.byref(obj)))
        meta.update({"registration_load": hr_hex(hr), "private_com": bool(is_private.value)})
        if not succeeded(hr) or not obj.value:
            return None, meta
        loaded, persistence = persist_file_load(obj, path)
        meta.update(persistence)
        if not loaded:
            loaded, persistence = persist_stream_load(obj, path)
            meta.update(persistence)
        if not loaded:
            method(obj, 2, ReleaseProto)(obj)
            return None, meta
        return obj, meta
    finally:
        release_reg(reg)

def base_result(path: str) -> dict:
    return {"path": path, "status": "HANDLER_ERROR", "text": "", "values": [],
            "extractor_id": EXTRACTOR_ID, "extractor_profile": EXTRACTOR_PROFILE}
def extract(path: str) -> dict:
    path = os.path.abspath(path)
    result = base_result(path)
    query = ctypes.WinDLL("query.dll")
    load = query.LoadIFilter
    load.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    load.restype = HRESULT
    obj = ctypes.c_void_p()
    load_hr = int(load(path, None, ctypes.byref(obj)))
    result["load_hr"] = hr_hex(load_hr)
    if succeeded(load_hr) and obj.value:
        result["load_strategy"] = "query-loadifilter"
    else:
        fallback_obj, fallback_meta = load_registered_filter(path)
        result.update(fallback_meta)
        if fallback_obj is None:
            result["status"] = "UNSUPPORTED" if hr_u32(load_hr) in {0x80004002, 0x80040154} else "HANDLER_ERROR"
            result["error"] = f"no usable IFilter; direct={result['load_hr']}"
            return result
        obj = fallback_obj
        result["load_strategy"] = "filter-registration"

    release = method(obj, 2, ReleaseProto)
    init = method(obj, 3, InitProto)
    get_chunk = method(obj, 4, GetChunkProto)
    get_text = method(obj, 5, GetTextProto)
    get_value = method(obj, 6, GetValueProto)
    flags_out = ULONG(0)
    init_hr = int(init(obj, 0, 0, None, ctypes.byref(flags_out)))
    result["init_hr"] = hr_hex(init_hr)
    try:
        if not succeeded(init_hr):
            result["status"] = "UNSUPPORTED" if hr_u32(init_hr) == 0x8004170C else "HANDLER_ERROR"
            result["error"] = f"IFilter.Init failed: {result['init_hr']}"
            return result
        text_parts, values = [], []
        chunk_count = 0
        for _ in range(10000):
            stat = STAT_CHUNK()
            chunk_hr = int(get_chunk(obj, ctypes.byref(stat)))
            if not succeeded(chunk_hr):
                result["end_hr"] = hr_hex(chunk_hr)
                break
            chunk_count += 1
            if stat.flags & CHUNK_TEXT:
                for _ in range(10000):
                    count = ULONG(4095)
                    buf = ctypes.create_unicode_buffer(4096)
                    text_hr = int(get_text(obj, ctypes.byref(count), buf))
                    value = normalize_text(buf.value)
                    if value:
                        text_parts.append(value)
                    if not succeeded(text_hr) or count.value == 0:
                        break
            if stat.flags & CHUNK_VALUE:
                prop = ctypes.c_void_p()
                value_hr = int(get_value(obj, ctypes.byref(prop)))
                if succeeded(value_hr) and prop.value:
                    try:
                        value = propvariant_to_string(prop)
                        if value:
                            values.append(value)
                    finally:
                        free_propvariant(prop)
        result["chunks"] = chunk_count
        result["text"] = "".join(text_parts)
        result["values"] = values
        result["status"] = "OK"
        return result
    finally:
        release(obj)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(json.dumps({"status": "BAD_REQUEST", "error": "expected one path"}))
        return 2
    ctypes.windll.ole32.CoInitialize(None)
    try:
        try:
            result = extract(argv[0])
        except BaseException as exc:
            result = base_result(os.path.abspath(argv[0]))
            result["status"] = "HANDLER_ERROR"
            result["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        ctypes.windll.ole32.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
