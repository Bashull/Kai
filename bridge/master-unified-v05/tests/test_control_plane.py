from dataclasses import replace
import uuid
import unittest

from kai_master.control_plane import (Intent,Evidence,RouteError,REGISTRY,
    classify,plan_route,make_action,digest_action,verify_receipt,route_summary)
NOW=1791857000

def action(cap='windows.status', now=NOW):
    return Intent(cap,str(uuid.uuid4()),now-1,now+60,{})

def proof(cap='windows.status', now=NOW):
    c=REGISTRY[cap]
    return Evidence(c.node,cap,now-2,c.backend,'COMPLETED')

class TestUnified(unittest.TestCase):
    def test_inventory(self):
        self.assertIn('android.status',REGISTRY)
        self.assertIn('windows.gui.catalog',REGISTRY)
        self.assertEqual(classify('missing'),'UNKNOWN')
        self.assertEqual(classify('windows.gui.catalog'),'STAGING')
        self.assertFalse(route_summary()['high_trust_routable'])
    def test_windows_read(self):
        x=action();p=proof()
        r=plan_route(x,p,now=NOW)
        self.assertEqual(r.backend,'sentinel-kai-inbox')
        a=make_action(x,p,now=NOW)
        self.assertEqual(a['schema'],'kai.master.action/1')
        self.assertEqual(a['deadline'],NOW+60)
        self.assertEqual(a['params'],{})
    def test_receipt_binding(self):
        a=make_action(action(),proof(),now=NOW)
        r={'schema':'kai.master.receipt/1','request_id':a['request_id'],
           'node_id':a['node_id'],'capability':a['capability'],
           'digest':digest_action(a),'status':'COMPLETED',
           'result':{'status':'ready'},'error':None}
        self.assertEqual(verify_receipt(a,r)['status'],'COMPLETED')
        for key,value in [('status','BOGUS'),('node_id','other'),('digest','0'*64)]:
            with self.assertRaises(RouteError): verify_receipt(a,r|{key:value})
        with self.assertRaises(RouteError):verify_receipt(a,r|{'extra':'x'})
        with self.assertRaises(RouteError):verify_receipt(a,r|{'error':'problem'})
    def test_android_plan_is_not_windows_action(self):
        x=action('android.status');p=proof('android.status')
        self.assertEqual(plan_route(x,p,now=NOW).node,'kai-galaxy-s24')
        with self.assertRaisesRegex(RouteError,'NOT_A_WINDOWS_QUEUE_ACTION'):
            make_action(x,p,now=NOW)
    def test_high_trust_denied(self):
        for cap in ('windows.gui.catalog','windows.gui.capture','windows.gui.click',
                    'windows.gui.type','windows.admin.shell','android.gui.tap','android.root'):
            with self.subTest(cap=cap):
                with self.assertRaisesRegex(RouteError,'CAPABILITY_NOT_ENABLED'):
                    plan_route(action(cap),proof(cap),now=NOW)
    def test_wrong_identity_denied(self):
        x=action();p=proof()
        for ep in [replace(p,node='other'),replace(p,capability='android.status'),
                   replace(p,transport='new-bypass'),replace(p,result='PROPOSED'),
                   replace(p,origin='historical_document')]:
            with self.subTest(ep=ep):
                with self.assertRaises(RouteError):plan_route(x,ep,now=NOW)
    def test_freshness(self):
        x=action();p=proof()
        with self.assertRaises(RouteError):plan_route(x,replace(p,observed_at=NOW-121),now=NOW)
        with self.assertRaises(RouteError):plan_route(x,replace(p,observed_at=NOW+1),now=NOW)
        with self.assertRaises(RouteError):plan_route(x,None,now=NOW)
        with self.assertRaises(RouteError):plan_route(x,p,now=NOW+90)
    def test_uuid_ttl_params(self):
        x=action();p=proof()
        variants=[replace(x,request_id='evil'),replace(x,request_id=str(uuid.uuid1())),
                  replace(x,issued_at=NOW+1),replace(x,expires_at=NOW+150),
                  replace(x,expires_at=NOW),replace(x,params={'cmd':'powershell'}),
                  replace(x,params={'cmd':42}),replace(x,issued_at=True)]
        for v in variants:
            with self.subTest(v=v):
                with self.assertRaises(RouteError):plan_route(v,p,now=NOW)
    def test_no_signing_claim(self):
        a=make_action(action(),proof(),now=NOW)
        self.assertEqual(len(digest_action(a)),64)
        self.assertFalse('signature' in a)

if __name__=='__main__':unittest.main()