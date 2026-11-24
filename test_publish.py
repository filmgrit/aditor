import unittest
from unittest.mock import patch
import json, os, urllib.error
from tempfile import TemporaryDirectory
from pathlib import Path
from datetime import datetime, timedelta
import publish as p

class Tests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,24,12,tzinfo=p.KST)
        self.rows=[{'title':f'Campaign {i}','source':'Source A','url':f'https://example.com/{i}','date':(self.now-timedelta(hours=i)).isoformat(),'excerpt':'Synthetic test only.','media':[],'image':''} for i in range(8)]
        self.proposals=[{'refs':[i],'brand':f'Brand {i}','name':f'Campaign {i}','industry':p.INDUSTRIES[i%4],'formats':['Film'],'pick':p.PICKS[i%5],'reason':'Test','desc':'Test','what':'Test','why':'Test','how':'Test','insight':'Test','tags':['test'],'originality':25,'utility':20,'strategy':15} for i in range(8)]
    def test_rss(self):
        xml=b'<rss><channel><item><title>Test campaign</title><link>https://example.com/one</link><pubDate>Tue, 24 Nov 2026 01:00:00 GMT</pubDate><description><![CDATA[This is a synthetic advertising campaign test with an embedded video. https://www.youtube.com/watch?v=abcdefghijk]]></description></item></channel></rss>'
        rows=p.parse_feed(xml,'Test',self.now);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['media'][0]['id'],'abcdefghijk')
    def test_limit_diversity(self):
        chosen=p.select(self.rows,self.proposals,[],self.now);self.assertEqual(len(chosen),5);self.assertGreaterEqual(len({x['industry'] for x in chosen}),3)
    def test_dedup(self):
        old=p.select(self.rows,self.proposals,[],self.now);new=p.select(self.rows,self.proposals,old,self.now);self.assertEqual(len(new),3);self.assertFalse(set(x['id'] for x in old)&set(x['id'] for x in new))
    def test_no_padding(self):
        self.assertEqual(len(p.select(self.rows,self.proposals[:2],[],self.now)),2)
    def test_evidence_score(self):
        rows=self.rows+[dict(self.rows[0],source='Source B',url='https://example.org/one')]; proposals=[dict(self.proposals[0],refs=[0,8])]; c=p.select(rows,proposals,[],self.now)[0];self.assertEqual(c['scores']['화제성'],20);self.assertEqual(len(c['evidence']),2)
    def test_gemini_request(self):
        expected={'campaigns':self.proposals[:1]}
        response={'candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'internal'},{'text':json.dumps(expected)}]}}]}
        with patch.dict(os.environ,{'GEMINI_API_KEY':'fake-key'}), patch.object(p,'get',return_value=json.dumps(response).encode()) as request:
            self.assertEqual(p.curate(self.rows,[]),expected['campaigns'])
            url,body,headers=request.call_args.args
            self.assertEqual(url,'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent')
            self.assertEqual(headers['x-goog-api-key'],'fake-key')
            self.assertNotIn('fake-key',url+body.decode())
            self.assertEqual(json.loads(body)['generationConfig']['responseJsonSchema'],p.SCHEMA)
    def test_quota_preserves_archive(self):
        with TemporaryDirectory() as d:
            out=Path(d)/'campaigns.json'; initial='{"schema":1,"campaigns":[],"editions":{}}';out.write_text(initial)
            err=urllib.error.HTTPError('https://example.com',429,'limit',None,None)
            with patch.dict(os.environ,{'GEMINI_API_KEY':'fake-key'}),patch.object(p,'OUT',out),patch.object(p,'collect',return_value=(self.rows,[])),patch.object(p,'get',side_effect=err) as request:
                with self.assertRaisesRegex(RuntimeError,'429'): p.publish(self.now)
                self.assertEqual(request.call_count,1)
                self.assertEqual(out.read_text(),initial)
    def test_invalid_response(self):
        for response in [{'candidates':[]},{'candidates':[{'finishReason':'MAX_TOKENS'}]},{'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"campaigns":[{}]}'}]}}]}]:
            with patch.dict(os.environ,{'GEMINI_API_KEY':'fake-key'}),patch.object(p,'get',return_value=json.dumps(response).encode()):
                with self.assertRaises((RuntimeError,ValueError)): p.curate(self.rows,[])
if __name__=='__main__': unittest.main()
