import json, sys, re, difflib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
recs=[json.loads(l) for l in open(sys.argv[1])]
def S(t):
    t=re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',t).replace('_',' '); return ' '.join(re.findall(r'[A-Za-z][A-Za-z0-9]+',t)).lower()
od=[S(r['version_data'][0]['docstring']) for r in recs]; nd=[S(r['version_data'][1]['docstring']) for r in recs]
oc=[S(r['version_data'][0]['code']) for r in recs]; nc=[S(r['version_data'][1]['code']) for r in recs]
vec=TfidfVectorizer(sublinear_tf=True,min_df=2).fit(od+nd+oc+nc)
def cos(a,b): A=vec.transform(a); B=vec.transform(b); return np.asarray(A.multiply(B).sum(1)).ravel()
# delta-alignment: sim(doc,new_code) - sim(doc,old_code); stale doc should lean to old code
d_old=cos(od,nc)-cos(od,oc); d_new=cos(nd,nc)-cos(nd,oc)
y=np.r_[np.zeros(len(recs)),np.ones(len(recs))]
print('Delta-alignment TF-IDF pooled AUC (stale=old_doc): %.3f' % roc_auc_score(y,np.r_[-d_new,-d_old]))
print('Delta-alignment within-record new>old: %.3f ties %.3f' % ((d_new>d_old).mean(), (d_new==d_old).mean()))
print('share stale docs with delta<0: %.3f ; updated docs with delta<0: %.3f' % ((d_old<0).mean(), (d_new<0).mean()))
