"""Exact counterexamples to printed historical equations, not Guala execution."""
import hashlib
import itertools
import json
from fractions import Fraction
from pathlib import Path

B=Path(__file__).resolve().parent
rows=[]

def record(id, subject, witness, limitation):
    rows.append(dict(id=id,subject=subject,verdict='PRINTED_CLAIM_FALSIFIED',witness=witness,limitation=limitation))

cases=[]
for a,b in itertools.product((-1,0,1),repeat=2):
    total=a+b
    correct_carry=(total+1)//3
    s=total-3*correct_carry
    printed_carry=correct_carry-1
    assert total != s+3*printed_carry
    cases.append(dict(a=a,b=b,sum_trit=s,printed_carry=printed_carry,printed_reconstruction=s+3*printed_carry,required_total=total))
record('EQ01','April v4.0 carry formula and v5.0.1 carry function contain an extra minus one',cases,'This falsifies the printed formula for the stated balanced digits; no claim that deployed native/HDL uses it. With incoming carry the same offset error persists.')

barrier=(1+Fraction(3,4)*Fraction(37,64))*Fraction(3,2)
assert barrier==Fraction(1101,512)
record('EQ02','Printed numerical energy barrier2.37 contradicts its own coefficients',dict(exact=str(barrier),decimal=float(barrier),printed_decimal='2.37'),'Arithmetic substitution only. This does not validate the proposed barrier law or physical constants.')

record('EQ03','Subtracting individual constraint ranks double-counts dependent constraints',dict(n_start=2,C1=[1,0],C2=[1,0],individual_rank_sum=2,combined_rank=1,printed_n_eff=0,linear_solution_dimension=1),'For these linear equality constraints the correct rank is the stacked independent rank. Nonlinear geometry requires its own demonstrated conditions; no replacement L6 law is invented.')

original_a=(0,0,0,0,0)
original_b=(1,-1,0,0,0)
received=(1,0,0,0,0)
assert sum(original_a)==sum(original_b)==0
assert sum(x!=y for x,y in zip(original_a,received))==1
assert sum(x!=y for x,y in zip(original_b,received))==1
record('EQ04','One sum-parity constraint cannot uniquely locate and correct any unknown single-trit error',dict(K=0,original_a=original_a,original_b=original_b,same_received=received),'If the failed position is independently known, the other four trits can reconstruct that erasure. The counterexample concerns the blanket unknown-error correction claim.')

record('EQ05','Hermitian evolution with additive injection does not generally conserve norm',dict(hbar=1,psi='1',H='0',J='i',derivative_psi='1',derivative_norm_squared=2,identity='d||psi||²/dt = 2 Im(<psi,J>)/hbar for Hermitian H'),'Norm preservation holds for the homogeneous Hermitian evolution, not arbitrary forcing. A valid open-system balance must be supplied; renormalization would hide the input balance.')

record('EQ06','v0.4 Crank–Nicolson forcing term disagrees with its stated differential equation',dict(hbar=1,H=0,J='1',psi_initial='0',delta_time=1,printed_successor='1',successor_of_stated_ODE='-i'),'For i*hbar*dpsi/dt=H*psi+J with constant J, the forcing increment is -i*dt*J/hbar. No product equation was edited.')

record('EQ07','The claimed three levels for ceil(log3(32)) is incorrect',dict(word_width=32,three_levels_capacity=27,four_levels_capacity=81,required_ceiling_levels=4),'This only corrects the stated tree-depth arithmetic; it does not validate the physical per-level latency or the carry implementation.')

A,Bdiv,N=5,9,1
scale=3**N
truncated=Fraction((A*scale)//Bdiv,scale)
better=Fraction(2,3)
actual=Fraction(A,Bdiv)
assert abs(actual-better)<abs(actual-truncated)
record('EQ08','Integer folding quotient truncation is not always the nearest finite balanced-ternary approximation',dict(A=A,B=Bdiv,fractional_places=N,scaled_integer_quotient=(A*scale)//Bdiv,returned=str(truncated),actual=str(actual),closer_representable=str(better),returned_error=str(abs(actual-truncated)),closer_error=str(abs(actual-better))),'Truncating an already exact balanced-ternary expansion has a different tail-bound property. The printed divide-after-scaling algorithm truncates an integer quotient, so that property does not prove its claim. Actual HDL must be traced independently.')

a=(1,1);b=(1,0)
raw=[x+y for x,y in zip(a,b)]
c=[(x+1)//3 for x in raw]
s=[x-3*y for x,y in zip(raw,c)]
expected=sum((x+y)*3**i for i,(x,y) in enumerate(zip(a,b)))
only_s=sum(x*3**i for i,x in enumerate(s))
assert expected==5 and only_s==2
record('EQ09','Independent redundant-digit normalization omits incoming carry when claimed as final canonical digits',dict(a=a,b=b,raw=raw,normalized_digits=s,outgoing_carries=c,expected=expected,normalized_digits_value=only_s),'Keeping the carry vector as a separate redundant representation preserves value; it does not establish a fully normalized result in the asserted two independent passes. Further carry incorporation must be specified and bounded.')

record('EQ10','Unforced time-independent Hermitian evolution does not itself minimize energy',dict(hbar=1,H='diag(0,1)',psi_initial='(1/sqrt(2),1/sqrt(2))',psi_at_t='(1/sqrt(2),exp(-i*t)/sqrt(2))',energy_expectation='1/2 for all t',ground_state_energy=0),'This exact solution remains above the minimum. Dissipative TAL and conservative Psi laws need an explicit coupling/open-system balance; one cannot call them equivalent because both use a field.')

result=dict(scope='Exact mathematical falsification of recovered printed specifications; no organism import, mutation, native build or physical hardware test',checks=rows,count=len(rows),product_qualification=False)
payload=(json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode()
p=B/'historical-equation-falsifiers.json'
if p.exists():
    assert p.read_bytes()==payload
else:
    p.write_bytes(payload)
print(json.dumps(dict(checks=len(rows),result='Ten historical printed claims have exact counterexamples or arithmetic contradictions',sha256=hashlib.sha256(payload).hexdigest(),product_acceptance=False)))
