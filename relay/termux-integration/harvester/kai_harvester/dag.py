"""Lossless graph inspection. Never mutate provider JSON.

A provider mapping is neither guaranteed tree-ordered nor guaranteed acyclic.
Edges are the UNION of declared children and parent backlinks; conflicting
parent declarations are reported, not silently fixed.
"""

def inspect_dag(conv):
    mapping = conv.get('mapping')
    if not isinstance(mapping, dict):
        return {'mapping_present': False, 'node_count': 0, 'message_count': 0,
                'branch_count': None, 'active_path': [], 'branches': [],
                'anomalies': ['mapping_unavailable']}
    ids = set(mapping)
    children = {k: set() for k in mapping}
    anomalies = []
    for nid, node in mapping.items():
        if not isinstance(node, dict):
            anomalies.append('non_object_node:' + nid); continue
        parent = node.get('parent')
        if parent is not None:
            if isinstance(parent,str) and parent in ids:
                children[parent].add(nid)
            else:
                anomalies.append('dangling_parent:' + nid)
        declared=node.get('children') or []
        if not isinstance(declared,list):anomalies.append('children_not_list:'+nid);declared=[]
        for child in declared:
            if isinstance(child,str) and child in ids:
                children[nid].add(child)
                target = mapping.get(child)
                if isinstance(target, dict) and target.get('parent') not in (None, nid):
                    anomalies.append('conflicting_parent:' + str(child))
            else:
                anomalies.append('dangling_child:' + nid)
    def trace(leaf):
        path = []
        seen = set()
        nid = leaf
        while isinstance(nid,str) and nid in ids:
            if nid in seen:
                anomalies.append('cycle:' + nid)
                break
            seen.add(nid); path.append(nid)
            node = mapping[nid]
            if not isinstance(node, dict): break
            nid = node.get('parent')
            if nid is None: break
        return list(reversed(path))
    leaves = sorted(k for k, v in children.items() if not v)
    if not leaves and ids:
        anomalies.append('no_leaf_cycle_or_corruption')
    active = conv.get('current_node')
    if active is not None and (not isinstance(active,str) or active not in ids):
        anomalies.append('current_node_missing')
    branches = [trace(k) for k in leaves]
    # The current visible path can terminate at a node which is not a leaf.
    active_path = trace(active) if isinstance(active,str) and active in ids else []
    # A declared child edge without a backlink is evidence worth retaining.
    for nid, node in mapping.items():
        if isinstance(node, dict):
            for ch in (node.get('children') if isinstance(node.get('children'),list) else []):
                if isinstance(ch,str) and ch in ids and isinstance(mapping[ch], dict) and mapping[ch].get('parent') != nid:
                    anomalies.append('edge_without_matching_backlink:' + str(ch))
    return {'mapping_present': True, 'node_count': len(mapping),
            'message_count': sum(isinstance(x, dict) and isinstance(x.get('message'), dict) for x in mapping.values()),
            'branch_count': len(branches), 'active_path': active_path,
            'branches': branches, 'anomalies': sorted(set(anomalies))}


def message_text(message):
    if not isinstance(message, dict): return ''
    content = message.get('content') or {}
    if isinstance(content, str): return content
    if not isinstance(content, dict): return ''
    parts = content.get('parts')
    if isinstance(parts, list):
        # Do not invent text for images, non-text blocks or invisible tokens.
        return '\n'.join(p for p in parts if isinstance(p, str))
    text = content.get('text')
    return text if isinstance(text, str) else ''


def markdown_current_path(conv, assessment=None):
    assessment = assessment or inspect_dag(conv)
    title = str(conv.get('title') or 'Sin título').replace('\n', ' ')
    result = ['# ' + title, '', '> Vista derivada de la ruta activa. El JSON RAW conserva todas las ramas.', '']
    mapping = conv.get('mapping') or {}
    for nid in assessment['active_path']:
        msg = (mapping.get(nid) or {}).get('message') or {}
        txt = message_text(msg)
        if not txt: continue
        author=msg.get('author') if isinstance(msg.get('author'),dict) else {}
        role = author.get('role') or 'unknown'
        # Keep literal text as-is: no markdown parser roundtrip.
        result.extend(['## ' + str(role) + ' · ' + nid, '', txt, ''])
    return '\n'.join(result) + '\n'
