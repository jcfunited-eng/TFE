"""Arithmetic design verification, not a repaired product or live-state replay."""
from pathlib import Path
import math,sys,json
from decimal import Decimal,localcontext
B=Path(__file__).resolve().parent
EPS2=sys.float_info.epsilon**2
up=lambda x:math.nextafter(x,math.inf)
down=lambda x:math.nextafter(x,-math.inf)
add=lambda x,y:y if x==0 else x if y==0 else up(x+y)
mul=lambda x,y:0.0 if x==0 or y==0 else up(x*y)
div=lambda x,y:0.0 if x==0 else up(x/y)
def tail_test(r0,v0,a,z):
 r1=z*v0-a*r0;s=max(abs(r0),abs(r1));t=max(abs(v0),abs(r1))
 # Binary exponents are representation scales, never altered physical state.
 se=math.frexp(s)[1] if s else 0;te=math.frexp(t)[1] if t else 0
 sg=math.ldexp(s,-se);tv=math.ldexp(t,-te)
 c=[math.ldexp(r0,-se),math.ldexp(r1,-se)]
 vg=[math.ldexp(v0,-te),-math.ldexp(r1,-te)]
 budgets=[down(EPS2*sg),down(EPS2*down(sg*sg)),down(EPS2*down(tv*tv))]
 ag=add(abs(c[0]),abs(c[1]));av=add(abs(vg[0]),abs(vg[1]))
 for degree in range(1,109):
  factor=z+a/(degree+1);nxt=-factor*c[-1];nv=-factor*vg[-1]
  rho=add(abs(z),div(a,degree+2));den=down(1-rho)
  tg=div(0 if nxt==0 else up(abs(nxt)),den);tt=div(0 if nv==0 else up(abs(nv)),den)
  sq=lambda tau,absolute:add(div(mul(mul(2,tau),absolute),degree+2),div(mul(tau,tau),2*degree+3))
  tails=[div(tg,degree+2),sq(tg,ag),sq(tt,av)]
  if all(x<=y for x,y in zip(tails,budgets)):break
  if degree==108:raise AssertionError('normalization did not resolve example')
  c.append(nxt);vg.append(nv);ag=add(ag,abs(nxt));av=add(av,abs(nv))
 i1=math.fsum(x/(i+1) for i,x in enumerate(c))
 i2=math.fsum(c[i]*c[j]*(1 if i==j else 2)/(i+j+1) for i in range(len(c)) for j in range(i,len(c)))
 return {'degree':degree,'scales_binary_exponent':[se,te],'budgets':budgets,'tails':tails,'normalized_integrals':[i1,i2]}
small=tail_test(-1e-147,1e-147,1.25,0.0)
with localcontext() as ctx:
 ctx.prec=100;a=Decimal.from_float(1.25);r=Decimal.from_float(-1e-147);se=small['scales_binary_exponent'][0];scale=Decimal(2)**se
 exact1=r*(1-(-a).exp())/a/scale
 exact2=r*r*(1-(-2*a).exp())/(2*a)/(scale*scale)
 errors=[float(abs(Decimal.from_float(value)-exact)/abs(exact)) for value,exact in zip(small['normalized_integrals'],[exact1,exact2])]
 assert max(errors)<1e-14
 small['relative_errors_vs_100_digit_held_capacitance_law']=errors
receipt={'scope':'Scaled stopping-criterion design verified on independent tiny-charge counterexample only; no physical output serialization, product implementation, live replay or speed qualification','result':small}
(B/'normalized-tail-design.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
