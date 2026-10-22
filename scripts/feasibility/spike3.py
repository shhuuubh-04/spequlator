import json, sys, ast, textwrap, docstring_parser as dp
import numpy as np
recs=[json.loads(l) for l in open(sys.argv[1])]
ok=0; withparams=0; stale_old=0; stale_new=0; n=0
def sig_params(code):
    t=ast.parse(textwrap.dedent(code)); f=next(x for x in ast.walk(t) if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)))
    a=f.args; names=[x.arg for x in a.posonlyargs+a.args+a.kwonlyargs]+([a.vararg.arg] if a.vararg else [])+([a.kwarg.arg] if a.kwarg else [])
    return set(names)-{'self','cls'}
def doc_params(d):
    try: return {p.arg_name.split()[0].lstrip('*') for p in dp.parse(d).params if p.arg_name}
    except Exception: return set()
for r in recs:
    n+=1
    try: sp=sig_params(r['version_data'][1]['code']); ok+=1
    except Exception: continue
    po=doc_params(r['version_data'][0]['docstring']); pn=doc_params(r['version_data'][1]['docstring'])
    if po or pn: withparams+=1
    stale_old+= bool(po - sp); stale_new+= bool(pn - sp)
print(f'N={n} ast-parse ok={ok/n:.3f} records with documented params={withparams/n:.3f}')
print(f'doc names a param absent from NEW signature: old_doc={stale_old/n:.3f} new_doc={stale_new/n:.3f}')
