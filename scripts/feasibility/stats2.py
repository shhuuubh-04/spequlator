import json, sys, re
recs=[json.loads(l) for l in open(sys.argv[1])]
tq=sum(('"""' in r['version_data'][1]['code']) or ("'''" in r['version_data'][1]['code']) for r in recs)
leak=sum(r['version_data'][1]['docstring'].strip()[:40] in r['version_data'][1]['code'] for r in recs if len(r['version_data'][1]['docstring'].strip())>20)
print('code containing triple quotes', tq, 'of', len(recs)); print('new docstring first-40-chars found inside new code', leak)
r=recs[5]
print('diff_code type', type(r['diff_code']).__name__); print(repr(str(r['diff_code'])[:500]))
print('---diff_docstring'); print(repr(str(r['diff_docstring'])[:400]))
print('---commit msgs', repr(r['version_data'][0]['commit_message'][:80]), '|', repr(r['version_data'][1]['commit_message'][:80]))
print('dates', r['version_data'][0]['commit_date_time'], r['version_data'][1]['commit_date_time'])
# tests share
print('functions starting with test_', sum(r['function'].startswith('test') for r in recs))
