# Explicit-edit variant [R4]: signal = cos(doc, added_lines) - cos(doc, removed_lines). Same project-disjoint dev split as spike6.
import json, sys, re, random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
recs=[json.loads(l) for l in open(sys.argv[1])]
projs=sorted({r['project'] for r in recs}); random.seed(13); devp=set(random.sample(projs,20))
dev=[r for r in recs if r['project'] in devp]; tr=[r for r in recs if r['project'] not in devp]
def lines(diff,sign): return '\n'.join(l[2:] for l in str(diff).splitlines() if l.startswith(sign+' ')) or ' '
od=[r['version_data'][0]['docstring'] for r in dev]; nd=[r['version_data'][1]['docstring'] for r in dev]
add=[lines(r['diff_code'],'+') for r in dev]; rem=[lines(r['diff_code'],'-') for r in dev]
n=len(dev); y=np.r_[np.zeros(n),np.ones(n)]
def rep(name,eod,end,eadd,erem):
    dn=(eadd*end).sum(1)-(erem*end).sum(1); do=(eadd*eod).sum(1)-(erem*eod).sum(1)
    print(f'{name:40s} EDIT pair={np.mean(dn>do)+0.5*np.mean(dn==do):.3f} AUC={roc_auc_score(y,np.r_[-dn,-do]):.3f}',flush=True)
def Sx(t):
    t=re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',t).replace('_',' '); return ' '.join(re.findall(r'[A-Za-z][A-Za-z0-9]+',t)).lower()
vec=TfidfVectorizer(sublinear_tf=True,min_df=2).fit([Sx(r['version_data'][k][f]) for r in tr for k in (0,1) for f in ('docstring','code')])
T=lambda xs: vec.transform([Sx(x) for x in xs]).toarray()
rep('tfidf explicit-edit',T(od),T(nd),T(add),T(rem))
from sentence_transformers import SentenceTransformer
for mid,ms in [('sentence-transformers/all-MiniLM-L6-v2',128),('microsoft/unixcoder-base',256)]:
    m=SentenceTransformer(mid,device='cpu'); m.max_seq_length=ms
    E=lambda xs: m.encode(xs,batch_size=32,normalize_embeddings=True,show_progress_bar=False)
    rep(f'{mid} explicit-edit (max {ms})',E(od),E(nd),E(add),E(rem))
