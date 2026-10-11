from __future__ import annotations
from dataclasses import dataclass,asdict
import json,time,sqlite3
from pathlib import Path
@dataclass(frozen=True)
class Review:
    decision_id:str;actor:str;approved:bool;reason:str;wall_ms:float
class DecisionLedger:
    """Independent review ledger: the component proposing an action cannot self-approve it."""
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);cx=sqlite3.connect(self.path);cx.execute('CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY AUTOINCREMENT,decision_id TEXT,actor TEXT,approved INTEGER,reason TEXT,wall_ms REAL)');cx.commit();cx.close()
    def record(self,decision_id,actor,approved,reason):
        r=Review(str(decision_id),str(actor),bool(approved),str(reason),time.time()*1000);cx=sqlite3.connect(self.path);cx.execute('INSERT INTO reviews(decision_id,actor,approved,reason,wall_ms) VALUES(?,?,?,?,?)',(r.decision_id,r.actor,int(r.approved),r.reason,r.wall_ms));cx.commit();cx.close();return r
    def vetoed(self,decision_id):
        cx=sqlite3.connect(self.path);row=cx.execute('SELECT 1 FROM reviews WHERE decision_id=? AND approved=0 LIMIT 1',(str(decision_id),)).fetchone();cx.close();return bool(row)
