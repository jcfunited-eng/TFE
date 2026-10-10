import ast,hashlib,json,os,re,math
from datetime import datetime,timezone
from pathlib import Path
R=Path('/workspaces/Tao_Financial_Engine');B=R/'backups/runtime/a1-speech-specification-20261010';changes=[]
src=ast.parse((R/'backups/runtime/a1-speech-reconciliation-20261010/reconcile_operating_guidance.py').read_text())
exec(compile(ast.Module(body=[x for x in src.body if isinstance(x,ast.FunctionDef) and x.name in ('whole','dump')],type_ignores=[]),'custody-helper','exec'))
p=R/'docs/GUALA_SPEECH_LEARNING_SPECIFICATION.md';lines=p.read_text().splitlines();out=[]
for line in lines:
 if line.startswith("A_j'="):
  out.append(r"A_j'=e^{-h/(3\mathrm{s})}A_j+(1-e^{-h/(3\mathrm{s})})\pi_j.")
 elif line.startswith('Use the same normalized value-coefficient update,'):
  out.extend(r'''For the value readout keep eV_l'=rho_l eV_l+(1-rho_l)z on the same three timescales and set eVbar=(eV_2+eV_8+eV_32)/3. The explicit update is

\[
v^{q\prime}=\Pi_{\mathcal W_V}\left[v^q+
\eta_V\delta^q\frac{\bar e^V}{\epsilon+\|\bar e^V\|^2}\right],\qquad \eta_V=.001.
\]

Allowed eta_V is [10^-6,.001]. Each forecast, residual and trace uses the declared pre-update chronology. For each reached adaptive input contact, keep three eligibility traces'''.splitlines())
 elif line.startswith('Store effective coefficient w and labile component l.'):
  out.extend(r'''Store authoritative effective coefficient w and labile component l. Let s=w-l be the implied stable portion. Start newly introduced records with w=l=0; preserve every existing mature coefficient outside this new representation. An admitted learning update first projects w_new to its effective interval and then uses Delta=w_new-w to set l_new=l+Delta, so s is unchanged. With w,s initially in [-1,1], l is bounded in [-2,2].

During native sleep, l'=exp(-h/(600 s))l while authoritative w is unchanged; the implied stable portion moves toward w without altering current transmission. For the proposed one-hour labile decay, an awake step removes Delta=(1-exp(-h/(3600 s)))l from both w and l. Effective w then moves toward s and stays within the admitted interval. This avoids independently clipped fast/stable sums and sleep-transfer rounding changing the authoritative transmission. Whether consolidation improves retention must be tested; it cannot invent experience or improve pronunciation without learning.'''.splitlines())
 else:out.append(line)
whole(p,'\n'.join(out)+'\n')
c=R/'docs/guala_reconciliation/speech-learning-contract.json';contract=json.loads(c.read_text());contract['specification_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();dump(c,contract)
# Keep the predecessor machine-readable hypothesis explicitly superseded as implementation guidance.
c=R/'docs/guala_reconciliation/speech-complete-hypothetical-loop.json';d=json.loads(c.read_text());d['implementation_guidance_superseded_by']={'specification':'docs/GUALA_SPEECH_LEARNING_SPECIFICATION.md','id':'GUALA-SPEECH-01','revision':'1.0','reason':'Skeptical review corrected control, timing, provenance, credit, ownership and boundedness; prior equations are historical where conflicting.'};dump(c,d)
# Refresh all changed documentation entries, then validate only the new normative scope.
m=R/'docs/guala_reconciliation/indexes/artifact-manifest.json';manifest=json.loads(m.read_text());rows={x['path']:x for x in manifest['files']}
original=json.loads((B/'document-changes.json').read_text())['changes'];all_changes=original+changes
paths={str(Path(x['path']).relative_to(R)) for x in all_changes}
for rel in paths:
 if rel.startswith('docs/') and rel!='docs/guala_reconciliation/indexes/artifact-manifest.json':
  raw=(R/rel).read_bytes();rows[rel]={'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
manifest['files']=sorted(rows.values(),key=lambda x:x['path']);manifest['at_utc']=datetime.now(timezone.utc).isoformat();dump(m,manifest)
checks=[];s=p.read_text();assert s.count(r'\[')==s.count(r'\]');checks.append('balanced display math delimiters')
for i in range(1,17):assert f'SPF{i:02}' in s
for i in range(1,7):assert f'SPEECH-EX{i:02}' in s
checks.extend(['16 findings have normative dispositions','6 scoped exceptions present'])
for target in re.findall(r'\]\(([^)]+)\)',s):
 if not target.startswith(('http:','https:','#')):
  local=(p.parent/target.split('#')[0]).resolve();assert local.exists(),str(local)
checks.append('new specification local links exist')
assert hashlib.sha256(p.read_bytes()).hexdigest()==contract['specification_sha256']
for rel in paths:
 if rel.endswith('.json'):json.loads((R/rel).read_text())
 if rel in rows:
  raw=(R/rel).read_bytes();assert rows[rel]['sha256']==hashlib.sha256(raw).hexdigest() and rows[rel]['bytes']==len(raw)
checks.append('changed JSON and manifest custody consistent')
for J in [0,.01,.1,1,10,100]:
 for mu in [.01,.1,.5]:
  factor=1-mu*J*J/(1e-6+J*J);assert abs(factor)<=1
checks.append('normalized scalar fixed-model step is nonexpansive for checked gains; not a nonlinear product proof')
for w in [-1,-.4,0,.6,1]:
 for stable in [-1,-.3,0,.2,1]:
  l=w-stable;assert -2<=l<=2
  for alpha in [0,.1,.5,1]:
   awake=w-alpha*l;assert -1-1e-12<=awake<=1+1e-12
   sleep_stable=w-(1-alpha)*l;assert -1-1e-12<=sleep_stable<=1+1e-12
checks.append('consolidation bound/authority arithmetic cases pass; not retention qualification')
validation={'at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'checks_count':len(checks),'product_tests_run':False,'source_or_runtime_changed':False,'specification_sha256':contract['specification_sha256'],'paths_for_publication':sorted(paths|{'backups/runtime/a1-speech-specification-20261010/review.json','backups/runtime/a1-speech-specification-20261010/validation.json','backups/runtime/a1-speech-specification-20261010/review.py','backups/runtime/a1-speech-specification-20261010/finalize.py'})}
dump(B/'validation.json',validation)
print(json.dumps({'documentation_checks':len(checks),'spec_sha256':validation['specification_sha256'],'paths':len(validation['paths_for_publication']),'product_tests_run':False}))
