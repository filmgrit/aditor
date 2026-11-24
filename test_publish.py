import unittest
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
if __name__=='__main__': unittest.main()
