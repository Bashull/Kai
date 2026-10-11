"""Restricted importers for official exports and KAI browser bridge envelopes."""
import json
import zipfile,stat
from pathlib import Path, PurePosixPath
from .store import sha

MAX_INPUT=512*1024*1024
MAX_ENTRY=256*1024*1024
MAX_TOTAL_UNCOMPRESSED=2*1024*1024*1024
MAX_RATIO=200
MAX_MEMBERS=20000

def classify_records(obj):
    if isinstance(obj,list):
        return [x for x in obj if isinstance(x,dict) and ('mapping' in x or 'messages' in x)]
    if not isinstance(obj,dict): return []
    if 'mapping' in obj or ('messages' in obj and ('id' in obj or 'conversation_id' in obj)):
        return [obj]
    for key in ('conversations','items'):
        arr=obj.get(key)
        if isinstance(arr,list):
            return [x.get('raw') if isinstance(x,dict) and isinstance(x.get('raw'),dict) else x for x in arr
                    if isinstance(x,dict) and (('mapping' in x) or ('messages' in x) or isinstance(x.get('raw'),dict))]
    return []

def ingest_json_bytes(store,name,data,fmt='json',scope='UNKNOWN'):
    if len(data)>MAX_INPUT: raise ValueError('input_too_large')
    # Store raw evidence even if schema is unexpected, but never claim completeness.
    sid=store.source(name,data,fmt,scope)
    try: obj=json.loads(data)
    except (UnicodeDecodeError,ValueError):
        store.warning(sid,'INVALID_JSON');return sid,0
    count=0
    for rec in classify_records(obj):
        if store.conversation(sid,rec):count+=1
    if count==0:store.warning(sid,'NO_SUPPORTED_CONVERSATION_GRAPH')
    return sid,count

def ingest_file(store,path):
    path=Path(path).expanduser().resolve()
    if path.is_dir():
        total=0
        # Never recurse all of Android storage indiscriminately.
        for p in sorted(path.iterdir()):
            if p.is_file() and p.suffix.lower() in ('.json','.jsonl','.zip'):
                total+=ingest_file(store,p)
        return total
    if path.stat().st_size>MAX_INPUT: raise ValueError('file_too_large')
    if path.suffix.lower()=='.zip': return ingest_zip(store,path)
    raw=path.read_bytes()
    if path.suffix.lower()=='.jsonl':
        sid=store.source(path.name,raw,'jsonl')
        count=0
        for line in raw.splitlines():
            if not line.strip(): continue
            try: obj=json.loads(line)
            except ValueError:
                store.warning(sid,'BAD_JSONL_LINE');continue
            for conv in classify_records(obj):
                if store.conversation(sid,conv):count+=1
        if not count:store.warning(sid,'NO_SUPPORTED_CONVERSATION_GRAPH')
        return count
    return ingest_json_bytes(store,path.name,raw)[1]

def ingest_zip(store,path):
    raw=path.read_bytes()
    sid=store.source(path.name,raw,'zip')
    count=0
    with zipfile.ZipFile(path) as archive:
        members=archive.infolist()
        if len(members)>MAX_MEMBERS:raise ValueError('too_many_zip_members')
        total=sum(m.file_size for m in members)
        if total>MAX_TOTAL_UNCOMPRESSED:raise ValueError('zip_uncompressed_limit')
        for inf in members:
            name=inf.filename.replace('\\','/')
            pp=PurePosixPath(name)
            if name.startswith('/') or '..' in pp.parts or ':' in name.split('/')[0]:
                store.warning(sid,'UNSAFE_ZIP_MEMBER');continue
            if inf.is_dir():continue
            if stat.S_ISLNK(inf.external_attr>>16) or inf.flag_bits&1:
                store.warning(sid,'UNSUPPORTED_ZIP_LINK_OR_ENCRYPTED');continue
            if inf.file_size>MAX_ENTRY or (inf.compress_size and inf.file_size/max(1,inf.compress_size)>MAX_RATIO):
                store.warning(sid,'ZIP_BOMB_GUARD');continue
            if inf.filename.lower().endswith('.json'):
                data=archive.read(inf)
                # Internal input content-addressed separately from entire ZIP.
                member_id,num=ingest_json_bytes(store,path.name+'::'+name,data,'zip-json')
                count+=num
            elif name.lower().endswith(('.png','.jpg','.jpeg','.webp','.gif','.pdf','.mp3','.mp4','.wav','.dat','.txt','.pak','.mpak','.log')):
                # Local asset is physical evidence; not linked to a logical reference unless proven.
                store.asset(sid,name,archive.read(inf))
    return count
