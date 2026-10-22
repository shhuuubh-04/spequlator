# Feasibility spike on TRAIN split only. Proxy task: given new code, is new docstring more similar than old docstring?
import json, sys, re, difflib, random
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
recs=[json.loads(l) for l in open(sys.argv[1])]
def split_ids(t):
    t=re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',t); t=t.replace('_',' ')
    return ' '.join(re.findall(r'[A-Za-z][A-Za-z0-9]+',t)).lower()
old_d=[split_ids(r['version_data'][0]['docstring']) for r in recs]
new_d=[split_ids(r['version_data'][1]['docstring']) for r in recs]
new_c=[split_ids(r['version_data'][1]['code']) for r in recs]
old_c=[split_ids(r['version_data'][0]['code']) for r in recs]
vec=TfidfVectorizer(sublinear_tf=True, min_df=2).fit(old_d+new_d+new_c+old_c)
def cos(a,b):
    A=vec.transform(a); B=vec.transform(b); return np.asarray(A.multiply(B).sum(1)).ravel()
s_new=cos(new_c,new_d); s_old=cos(new_c,old_d)
ratio=np.array([difflib.SequenceMatcher(None,r['version_data'][0]['docstring'],r['version_data'][1]['docstring']).ratio() for r in recs])
win=(s_new>s_old); tie=(s_new==s_old)
print('N',len(recs))
print('TF-IDF pairwise: new>old %.3f  ties %.3f' % (win.mean(), tie.mean()))
y=np.r_[np.zeros(len(recs)),np.ones(len(recs))]; score=np.r_[-s_new,-s_old]  # higher score => more stale
print('TF-IDF AUC (stale=new_code+old_doc) %.3f' % roc_auc_score(y,score))
for lo,hi in [(0,0.7),(0.7,0.9),(0.9,0.95),(0.95,1.01)]:
    m=(ratio>=lo)&(ratio<hi); print(f'  doc-edit ratio [{lo},{hi}) n={m.sum()} new>old={win[m].mean():.3f} ties={tie[m].mean():.3f}')
# Delta signal: does doc change align with code change? cos(added code tokens, added doc tokens)
def added(diff, sign):
    return ' '.join(l[2:] for l in str(diff).splitlines() if l.startswith(sign+' '))
ac=[split_ids(added(r['diff_code'],'+')) for r in recs]; rc=[split_ids(added(r['diff_code'],'-')) for r in recs]
# OVERLAP(C, deleted) rule from Panthaplackel et al.: old doc shares a token with deleted code lines (that is not in new code)
def ov(doc, deleted, newcode):
    d=set(doc.split()); dl=set(deleted.split())-set(newcode.split()); return len(d & dl)>0
ov_old=np.array([ov(old_d[i],rc[i],new_c[i]) for i in range(len(recs))]); ov_new=np.array([ov(new_d[i],rc[i],new_c[i]) for i in range(len(recs))])
print('OVERLAP rule fires: old_doc %.3f  new_doc %.3f' % (ov_old.mean(), ov_new.mean()))
