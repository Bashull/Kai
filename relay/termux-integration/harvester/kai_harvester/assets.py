"""Discover provider asset descriptors without exposing signed URLs or credentials.

Discovery is not materialization. The detector is intentionally conservative;
unknown provider blocks remain preserved unmodified in RAW evidence.
"""
from hashlib import sha256
import json

IDENTITY_FIELDS=('id','file_id','asset_pointer','image_url','download_url','url')

def find_references(root,max_nodes=100000):
    refs={}
    stack=[('root',root)]
    visited=0
    while stack:
        path,obj=stack.pop()
        visited+=1
        if visited>max_nodes:break
        if isinstance(obj,dict):
            if isinstance(obj.get('attachments'),list):
                for i,a in enumerate(obj['attachments']):
                    if isinstance(a,dict):
                        identity=str(next((a.get(k) for k in IDENTITY_FIELDS if a.get(k)),''))
                        if identity:
                            code=sha256(identity.encode()).hexdigest()
                            refs[code]={'fingerprint':code,'kind':'upload_attachment',
                                        'path':path+'/attachments/'+str(i),
                                        'label':str(a.get('name') or a.get('filename') or '')[:150]}
            for key,value in obj.items():
                if key in ('asset_pointer','image_url') and isinstance(value,str) and value:
                    code=sha256(value.encode()).hexdigest()
                    refs[code]={'fingerprint':code,'kind':key,'path':path+'/'+key,'label':''}
                # Avoid descending into every arbitrary large data-uri string.
                if isinstance(value,(dict,list)):
                    stack.append((path+'/'+str(key)[:80],value))
        elif isinstance(obj,list):
            for i,value in enumerate(obj):
                if isinstance(value,(dict,list)):
                    stack.append((path+'/'+str(i),value))
    return sorted(refs.values(),key=lambda x:x['fingerprint'])
