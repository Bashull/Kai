"""Append-only local evidence store using the Python standard library.

Every import captures original source bytes by SHA-256; provider objects are
serialized as separate immutable projections with provenance, never overwrite.
No HTTP, no token handling, no automatic deletion.
"""
import hashlib
import html
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from .dag import inspect_dag, markdown_current_path
from .assets import find_references

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, sha256 TEXT NOT NULL,
 ingested_at TEXT NOT NULL, format TEXT NOT NULL,
 declared_scope TEXT NOT NULL, original_bytes INTEGER NOT NULL,
 UNIQUE(name,sha256)
);
CREATE TABLE IF NOT EXISTS conversations (
 id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id),
 provider_id TEXT NOT NULL, raw_sha256 TEXT NOT NULL, title TEXT,
 node_count INTEGER, message_count INTEGER, branch_count INTEGER,
 mapping_present INTEGER NOT NULL, anomalies TEXT NOT NULL,
 UNIQUE(source_id,provider_id,raw_sha256)
);
CREATE TABLE IF NOT EXISTS assets (
 id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id),
 source_member TEXT NOT NULL, sha256 TEXT NOT NULL, byte_size INTEGER NOT NULL,
 UNIQUE(source_id,source_member)
);
CREATE TABLE IF NOT EXISTS asset_refs (
 source_id INTEGER NOT NULL REFERENCES sources(id),
 provider_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
 kind TEXT NOT NULL, path TEXT NOT NULL, label TEXT NOT NULL,
 PRIMARY KEY(source_id,provider_id,fingerprint)
);
CREATE TABLE IF NOT EXISTS warnings (
 id INTEGER PRIMARY KEY, source_id INTEGER REFERENCES sources(id),
 code TEXT NOT NULL, detail TEXT NOT NULL
);
'''

def sha(data): return hashlib.sha256(data).hexdigest()

def now(): return datetime.now(timezone.utc).isoformat()

def safe_slug(value):
    s = re.sub(r'[^a-zA-Z0-9_.-]+', '_', str(value))[:90].strip('._')
    return s or 'unnamed'

class Store:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.root.chmod(0o700)
        self.dbpath = self.root/'index.sqlite3'
        self.db = sqlite3.connect(self.dbpath)
        self.db.executescript(SCHEMA)
        self.dbpath.chmod(0o600)
        (self.root/'objects').mkdir(exist_ok=True)
        (self.root/'objects').chmod(0o700)
        (self.root/'views').mkdir(exist_ok=True)
        (self.root/'views').chmod(0o700)
    def close(self): self.db.close()
    def put_blob(self,data):
        digest = sha(data)
        dst = self.root/'objects'/digest[:2]/digest[2:]
        if dst.exists():
            if sha(dst.read_bytes())!=digest:raise ValueError('EXISTING_BLOB_CORRUPT')
            return digest
        dst.parent.mkdir(exist_ok=True,mode=0o700)
        fd,tmp=tempfile.mkstemp(prefix='.'+digest+'.',dir=dst.parent)
        temp=Path(tmp)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(temp,dst)
            dirfd=os.open(dst.parent,os.O_RDONLY)
            try:os.fsync(dirfd)
            finally:os.close(dirfd)
        finally:temp.unlink(missing_ok=True)
        return digest
    def source(self,name,data,fmt,scope='UNKNOWN'):
        digest=self.put_blob(data)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO sources(name,sha256,ingested_at,format,declared_scope,original_bytes) VALUES(?,?,?,?,?,?)', (name,digest,now(),fmt,scope,len(data)))
            row=self.db.execute('SELECT id FROM sources WHERE name=? AND sha256=?',(name,digest)).fetchone()
        return row[0]
    def warning(self,sid,code,detail=''):
        # Avoid writing sensitive tokens/URLs to logs.
        detail=safe_slug(detail)[:90]
        with self.db: self.db.execute('INSERT INTO warnings(source_id,code,detail) VALUES(?,?,?)',(sid,code,detail))
    def conversation(self,sid,conv):
        cid=conv.get('id') or conv.get('conversation_id')
        if not isinstance(cid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{4,128}',cid):
            self.warning(sid,'MISSING_OR_UNSAFE_CONVERSATION_ID');return False
        raw=json.dumps(conv,ensure_ascii=False,separators=(',',':')).encode('utf8')
        raw_hash=self.put_blob(raw)
        graph=inspect_dag(conv)
        with self.db:
            self.db.execute('''INSERT OR IGNORE INTO conversations(source_id,provider_id,raw_sha256,title,node_count,message_count,branch_count,mapping_present,anomalies) VALUES(?,?,?,?,?,?,?,?,?)''',
                (sid,cid,raw_hash,str(conv.get('title') or '')[:250],graph['node_count'],graph['message_count'],graph['branch_count'],int(graph['mapping_present']),json.dumps(graph['anomalies'])))
        with self.db:
            for asset in find_references(conv):
                self.db.execute('INSERT OR IGNORE INTO asset_refs(source_id,provider_id,fingerprint,kind,path,label) VALUES(?,?,?,?,?,?)',
                    (sid,cid,asset['fingerprint'],asset['kind'],asset['path'][:350],asset['label']))
        if graph['anomalies']: self.warning(sid,'GRAPH_ANOMALY',cid)
        return True
    def asset(self,sid,member,data):
        digest=self.put_blob(data)
        with self.db: self.db.execute('INSERT OR IGNORE INTO assets(source_id,source_member,sha256,byte_size) VALUES(?,?,?,?)',(sid,member,digest,len(data)))
        return digest
    def read_blob(self,digest):
        return (self.root/'objects'/digest[:2]/digest[2:]).read_bytes()
    def stats(self):
        def n(t):return self.db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        present=self.db.execute('SELECT COUNT(*) FROM conversations WHERE mapping_present=1').fetchone()[0]
        return {'sources':n('sources'),'conversation_records':n('conversations'),
                'with_mapping':present,'without_mapping':n('conversations')-present,
                'assets_physical':n('assets'),'asset_references_discovered':n('asset_refs'),'warnings':n('warnings'),
                'scope':'VERIFIED_SCOPE_OFFLINE_ONLY',
                'inventory_complete':False,'assets_complete':False,'full_history_complete':False}
    def audit(self):
        missing=[]; corrupt=[]
        for (dig,) in self.db.execute('SELECT sha256 FROM sources UNION SELECT raw_sha256 FROM conversations UNION SELECT sha256 FROM assets'):
            path=self.root/'objects'/dig[:2]/dig[2:]
            if not path.exists(): missing.append(dig)
            elif sha(path.read_bytes())!=dig: corrupt.append(dig)
        stats=self.stats()
        stats.update({'missing_blobs':missing,'corrupt_blobs':corrupt,'integrity_pass':not missing and not corrupt,
            'safe_to_delete_source_chat':False})
        return stats
    def export_views(self):
        generated=0
        for cid, raw in self.db.execute('SELECT provider_id,raw_sha256 FROM conversations'):
            conv=json.loads(self.read_blob(raw))
            dest=self.root/'views'/(safe_slug(cid)+'_'+raw[:12]+'.md')
            dest.write_text(markdown_current_path(conv),encoding='utf8')
            generated+=1
        return generated
    def manifest(self):
        data={'schema':'kai.harvester.offline.v1','generated_at':now(),'audit':self.audit(),
              'sources':[{'name':n,'sha256':s,'format':f,'scope':scope} for n,s,f,scope in self.db.execute('SELECT name,sha256,format,declared_scope FROM sources')],
              'records':[{'provider_id':c,'raw_sha256':r,'nodes':n,'branches':b} for c,r,n,b in self.db.execute('SELECT provider_id,raw_sha256,node_count,branch_count FROM conversations')]}
        path=self.root/'manifest.json'; temp=path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8');os.replace(temp,path)
        return path

    def export_reader(self):
        """Static, searchable index with no CDN/scripts from third parties."""
        self.export_views()
        rows=[]
        for cid,digest,title,nodes,branches in self.db.execute(
                'SELECT provider_id,raw_sha256,title,node_count,branch_count FROM conversations ORDER BY id'):
            fname=safe_slug(cid)+'_'+digest[:12]+'.md'
            rows.append('<li data-search="'+html.escape((title+' '+cid).lower(),quote=True)+'"><a href="views/'+html.escape(fname,quote=True)+'">'+html.escape(title or cid)+'</a> <small>nodes='+str(nodes)+' branches='+str(branches)+'</small></li>')
        page="""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KAI Harvester · Offline</title><style>body{font:16px system-ui;max-width:850px;margin:2em auto;padding:0 1em;background:#101827;color:#e9f1fa}a{color:#79cdfc}li{margin:0.6em 0}input{padding:0.8em;width:90%}small{color:#aab}</style></head><body><h1>KAI Harvester · índice offline</h1><p>Visor local. RAW en objects/, manifest.json, sin llamadas de red. Los archivos MD son vistas activas, no el grafo completo.</p><label>Buscar <input id="q" type="search" placeholder="Título o ID"></label><ol id="rows">"""+''.join(rows)+"""</ol><script>document.getElementById('q').addEventListener('input',e=>{const q=e.target.value.toLowerCase();for(const x of document.querySelectorAll('#rows li'))x.hidden=!x.dataset.search.includes(q)});</script></body></html>"""
        path=self.root/'index.html';path.write_text(page,encoding='utf8');return str(path)
