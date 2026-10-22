import json, sys, re, random, time, difflib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
recs=[json.loads(l) for l in open(sys.argv[1])]
random.seed(13); S=random.sample(recs,300)
od=[r['version_data'][0]['docstring'] for r in S]; nd=[r['version_data'][1]['docstring'] for r in S]; nc=[r['version_data'][1]['code'] for r in S]
ratio=np.array([difflib.SequenceMatcher(None,a,b).ratio() for a,b in zip(od,nd)])
def report(name,s_new,s_old,secs=None):
    win=(s_new>s_old).mean(); tie=(s_new==s_old).mean()
    y=np.r_[np.zeros(300),np.ones(300)]; auc=roc_auc_score(y,np.r_[-s_new,-s_old])
    big=ratio<0.95
    print(f'{name:45s} new>old={win:.3f} ties={tie:.3f} pooledAUC={auc:.3f} new>old(edit ratio<0.95)={(s_new>s_old)[big].mean():.3f}' + (f' sec/text={secs:.3f}' if secs else ''), flush=True)
def split_ids(t):
    t=re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',t).replace('_',' '); return ' '.join(re.findall(r'[A-Za-z][A-Za-z0-9]+',t)).lower()
tr=[json.loads(l) for l in open(sys.argv[1])]
corpus=[split_ids(r['version_data'][k][f]) for r in tr for k in (0,1) for f in ('docstring','code')]
vec=TfidfVectorizer(sublinear_tf=True,min_df=2).fit(corpus)
def tcos(a,b): A=vec.transform([split_ids(x) for x in a]); B=vec.transform([split_ids(x) for x in b]); return np.asarray(A.multiply(B).sum(1)).ravel()
report('tfidf+identifier-split',tcos(nc,nd),tcos(nc,od))
vec2=TfidfVectorizer(sublinear_tf=True,min_df=2).fit([r['version_data'][k][f] for r in tr for k in (0,1) for f in ('docstring','code')])
def tcos2(a,b): A=vec2.transform(a); B=vec2.transform(b); return np.asarray(A.multiply(B).sum(1)).ravel()
report('tfidf-raw(no split)',tcos2(nc,nd),tcos2(nc,od))
from sentence_transformers import SentenceTransformer
for mid,kw in [('sentence-transformers/all-MiniLM-L6-v2',{}),('jinaai/jina-embeddings-v2-base-code',{'trust_remote_code':True}),('microsoft/unixcoder-base',{})]:
    try:
        m=SentenceTransformer(mid,device='cpu',**kw); m.max_seq_length=min(512, m.max_seq_length or 512)
        t=time.time(); E=m.encode(od+nd+nc,batch_size=16,normalize_embeddings=True,show_progress_bar=False); secs=(time.time()-t)/900
        eo,en,ec=E[:300],E[300:600],E[600:]
        report(f'{mid} (max_seq={m.max_seq_length})',(ec*en).sum(1),(ec*eo).sum(1),secs)
    except Exception as e: print(mid,'FAILED',repr(e)[:300],flush=True)
