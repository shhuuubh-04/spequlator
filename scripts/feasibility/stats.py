import json, sys, statistics as st, difflib, hashlib, collections
path = sys.argv[1]
recs = [json.loads(l) for l in open(path)]
print(path.split('/')[-1], 'records', len(recs), 'sha256', hashlib.sha256(open(path,'rb').read()).hexdigest()[:16])
r = recs[0]
print('top keys', list(r.keys()))
print('version_data type', type(r['version_data']), len(r['version_data']))
print('v0 keys', list(r['version_data'][0].keys()))
def q(xs):
    xs=sorted(xs); n=len(xs); return dict(p10=xs[n//10], p50=xs[n//2], p90=xs[9*n//10], p99=xs[99*n//100], max=xs[-1])
dl=[];cl=[];ratio=[];cratio=[];same_doc=0;same_code=0;empty_dd=0;empty_dc=0
projects=collections.Counter()
for r in recs:
    v1,v2=r['version_data'][0],r['version_data'][1]
    d1,d2,c1,c2=v1['docstring'],v2['docstring'],v1['code'],v2['code']
    dl.append(len(d2.split())); cl.append(len(c2.split()))
    ratio.append(round(difflib.SequenceMatcher(None,d1,d2).ratio(),3))
    cratio.append(round(difflib.SequenceMatcher(None,c1,c2).ratio(),3))
    same_doc+= d1.strip()==d2.strip(); same_code+= c1.strip()==c2.strip()
    empty_dd+= not str(r.get('diff_docstring','')).strip(); empty_dc+= not str(r.get('diff_code','')).strip()
    projects[r['project']]+=1
print('new docstring words', q(dl)); print('new code whitespace-tokens', q(cl))
print('old-vs-new docstring similarity ratio', q(ratio)); print('old-vs-new code similarity ratio', q(cratio))
print('identical doc (strip)', same_doc, 'identical code', same_code, 'empty diff_docstring', empty_dd, 'empty diff_code', empty_dc)
print('docstring ratio>=0.95 share', round(sum(x>=0.95 for x in ratio)/len(ratio),3), '>=0.9', round(sum(x>=0.9 for x in ratio)/len(ratio),3))
top=projects.most_common(5); print('projects', len(projects), 'top5', top, 'top5 share', round(sum(c for _,c in top)/len(recs),3))
print('sample version_data[0] code head:', repr(r['version_data'][0]['code'][:150]))
print('sample diff_docstring head:', repr(str(r['diff_docstring'])[:200]))
print('v1 commit==v2 commit?', r['version_data'][0]['commit_sha']==r['version_data'][1]['commit_sha'])
