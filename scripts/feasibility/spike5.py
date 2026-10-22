import json, sys, re, random, time
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
recs=[json.loads(l) for l in open(sys.argv[1])]
random.seed(13); S=random.sample(recs,300)
od=[r['version_data'][0]['docstring'] for r in S]; nd=[r['version_data'][1]['docstring'] for r in S]
oc=[r['version_data'][0]['code'] for r in S]; nc=[r['version_data'][1]['code'] for r in S]
y=np.r_[np.zeros(300),np.ones(300)]
def rep(name,eod,end,eoc,enc,secs=None):
    abs_new=(enc*end).sum(1); abs_old=(enc*eod).sum(1)
    d_new=abs_new-(eoc*end).sum(1); d_old=abs_old-(eoc*eod).sum(1)
    print(f'{name:50s} ABS pair={np.mean(abs_new>abs_old):.3f} AUC={roc_auc_score(y,np.r_[-abs_new,-abs_old]):.3f} | DELTA pair={np.mean(d_new>d_old)+0.5*np.mean(d_new==d_old):.3f} AUC={roc_auc_score(y,np.r_[-d_new,-d_old]):.3f}'+(f' | s/text={secs:.3f}' if secs else ''),flush=True)
def Sx(t):
    t=re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',t).replace('_',' '); return ' '.join(re.findall(r'[A-Za-z][A-Za-z0-9]+',t)).lower()
vec=TfidfVectorizer(sublinear_tf=True,min_df=2).fit([Sx(r['version_data'][k][f]) for r in recs for k in (0,1) for f in ('docstring','code')])
T=lambda xs: vec.transform([Sx(x) for x in xs]).toarray()
rep('tfidf+split',T(od),T(nd),T(oc),T(nc))
from sentence_transformers import SentenceTransformer
for mid in ['flax-sentence-embeddings/st-codesearch-distilroberta-base','microsoft/unixcoder-base','sentence-transformers/all-MiniLM-L6-v2']:
    try:
        m=SentenceTransformer(mid,device='cpu'); m.max_seq_length=min(512,m.max_seq_length or 512)
        t=time.time(); E=m.encode(od+nd+oc+nc,batch_size=16,normalize_embeddings=True,show_progress_bar=False); secs=(time.time()-t)/1200
        rep(f'{mid} (max_seq={m.max_seq_length})',E[:300],E[300:600],E[600:900],E[900:],secs)
    except Exception as e: print(mid,'FAILED',repr(e)[:200],flush=True)
