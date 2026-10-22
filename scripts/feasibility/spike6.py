# Project-disjoint dev split INSIDE train: fine-tune MiniLM with (anchor=new_code, pos=new_doc, neg=old_doc); evaluate delta-alignment on dev.
import json, sys, re, random, time
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
recs=[json.loads(l) for l in open(sys.argv[1])]
projs=sorted({r['project'] for r in recs}); random.seed(13); devp=set(random.sample(projs,20))
dev=[r for r in recs if r['project'] in devp]; tr=[r for r in recs if r['project'] not in devp]
print('train recs',len(tr),'dev recs',len(dev),'dev projects',len(devp),flush=True)
g=lambda R,k,f:[r['version_data'][k][f] for r in R]
od,nd,oc,nc=g(dev,0,'docstring'),g(dev,1,'docstring'),g(dev,0,'code'),g(dev,1,'code')
n=len(dev); y=np.r_[np.zeros(n),np.ones(n)]
def delta(eod,end,eoc,enc):
    return (enc*end).sum(1)-(eoc*end).sum(1), (enc*eod).sum(1)-(eoc*eod).sum(1)
def rep(name,dn,do,secs=None):
    print(f'{name:40s} DELTA pair={np.mean(dn>do)+0.5*np.mean(dn==do):.3f} AUC={roc_auc_score(y,np.r_[-dn,-do]):.3f}'+(f' {secs}' if secs else ''),flush=True)
def Sx(t):
    t=re.sub(r'([a-z0-9])([A-Z])',r'\1 \2',t).replace('_',' '); return ' '.join(re.findall(r'[A-Za-z][A-Za-z0-9]+',t)).lower()
vec=TfidfVectorizer(sublinear_tf=True,min_df=2).fit([Sx(x) for k in (0,1) for f in ('docstring','code') for x in g(tr,k,f)])
T=lambda xs: vec.transform([Sx(x) for x in xs]).toarray()
tdn,tdo=delta(T(od),T(nd),T(oc),T(nc)); rep('tfidf delta',tdn,tdo)
from sentence_transformers import SentenceTransformer, losses
from datasets import Dataset
base='sentence-transformers/all-MiniLM-L6-v2'
m=SentenceTransformer(base,device='cpu'); m.max_seq_length=128
E=lambda M,xs: M.encode(xs,batch_size=32,normalize_embeddings=True,show_progress_bar=False)
bdn,bdo=delta(E(m,od),E(m,nd),E(m,oc),E(m,nc)); rep('MiniLM base delta',bdn,bdo)
ds=Dataset.from_dict({'anchor':g(tr,1,'code'),'positive':g(tr,1,'docstring'),'negative':g(tr,0,'docstring')})
from sentence_transformers import SentenceTransformerTrainer, SentenceTransformerTrainingArguments
args=SentenceTransformerTrainingArguments(output_dir='/tmp/claude-0/-home-claude/6cd1a5cf-8444-51d7-a668-6d7138b1f98a/scratchpad/ft',num_train_epochs=1,per_device_train_batch_size=8,learning_rate=2e-5,warmup_steps=0.1,seed=13,save_strategy='no',logging_steps=50,report_to='none',use_cpu=True)
t=time.time()
SentenceTransformerTrainer(model=m,args=args,train_dataset=ds,loss=losses.MultipleNegativesRankingLoss(m)).train()
print('train seconds',round(time.time()-t),flush=True)
fdn,fdo=delta(E(m,od),E(m,nd),E(m,oc),E(m,nc)); rep('MiniLM fine-tuned delta',fdn,fdo)
# simple combiner: z-scored average of tfidf and ft deltas
z=lambda a,b:(a-np.r_[a,b].mean())/np.r_[a,b].std()
cdn=z(tdn,tdo)+z(fdn,fdo); cdo=z(tdo,tdn)+z(fdo,fdn)
rep('combined tfidf+ft (z-avg)',cdn,cdo)
