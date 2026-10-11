from __future__ import annotations
import argparse,json,pathlib
from .parsers import parse_line
from .skills import skill_list
from .runtime_probe import inspect_many
from .bridge_audit import audit
from .store import EventStore
from .gates import GateInput,evaluate
from .pipeline import collect_logcat
from .contracts import RuntimeContract

def main(argv=None):
    p=argparse.ArgumentParser(prog='kai-nerve');s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('parse-line');q.add_argument('line')
    s.add_parser('status')
    s.add_parser('skills')
    s.add_parser('contract')
    q=s.add_parser('probe-runtime');q.add_argument('services',nargs='+')
    q=s.add_parser('audit-bridges');q.add_argument('services',nargs='+')
    q=s.add_parser('events');q.add_argument('db');q.add_argument('--limit',type=int,default=20)
    q=s.add_parser('gate')
    for k in GateInput.__dataclass_fields__:q.add_argument('--'+k.replace('_','-'),action='store_true')
    q=s.add_parser('collect-logcat');q.add_argument('--serial',required=True);q.add_argument('--challenge',required=True);q.add_argument('--worldbus-db',required=True);q.add_argument('--nerve-db',required=True);q.add_argument('--replay-db',required=True);q.add_argument('--max-age-ms',type=float,default=750.0);q.add_argument('--once',action='store_true')
    a=p.parse_args(argv)
    if a.cmd=='parse-line':
        o=parse_line(a.line); print(json.dumps(None if o is None else o.__dict__,ensure_ascii=False,indent=2));return 0
    if a.cmd=='status':
        from .perception_clock import health
        root=pathlib.Path.home()/'.kai_mobile'
        states={}
        for name in ['perception','worldbus','reflex']:
            try: states[name]=json.loads((root/name/'status.json').read_text())
            except (OSError,ValueError): states[name]={'ok':False,'reason':'status_unavailable'}
        states['perception']={k:states['perception'].get(k) for k in ('ok','seq','build','hud_present','session_id')}|health(states['perception'])
        print(json.dumps(states,ensure_ascii=False,indent=2));return 0
    if a.cmd=='skills':print(json.dumps(skill_list(),ensure_ascii=False,indent=2));return 0
    if a.cmd=='contract':print(json.dumps(RuntimeContract().to_dict(),ensure_ascii=False,indent=2));return 0
    if a.cmd=='probe-runtime':print(json.dumps(inspect_many(a.services),ensure_ascii=False,indent=2));return 0
    if a.cmd=='audit-bridges':print(json.dumps(audit(inspect_many(a.services)),ensure_ascii=False,indent=2));return 0
    if a.cmd=='events':print(json.dumps(EventStore(a.db).recent(a.limit),ensure_ascii=False,indent=2));return 0
    if a.cmd=='gate':
        kw={k:getattr(a,k) for k in GateInput.__dataclass_fields__};print(json.dumps(evaluate(GateInput(**kw)).to_dict(),indent=2));return 0
    if a.cmd=='collect-logcat':
        for result in collect_logcat(serial=a.serial,nerve_db=a.nerve_db,replay_db=a.replay_db,worldbus_db=a.worldbus_db,expected_challenge=a.challenge,max_age_ms=a.max_age_ms,once=a.once):
            if result.get('parse_error'):
                print(json.dumps({'parse_error':True,'raw':result['raw']}),flush=True);continue
            if 'event' in result:
                e=result['event']; out={'event_id':e.event_id,'source':e.source,'kind':e.kind,'session_id':e.session_id,'seq':e.source_seq,'freshness':e.freshness.value,'effective_age_ms':e.effective_age_ms,'actuation_eligible':e.actuation_eligible,'provenance':e.provenance,'worldbus_inserted':result['worldbus_inserted'],'worldbus_readback_id':(result['worldbus_readback'] or {}).get('id')}
            else: out=result
            print(json.dumps(out,ensure_ascii=False),flush=True)
        return 0
    return 2
if __name__=='__main__':raise SystemExit(main())
