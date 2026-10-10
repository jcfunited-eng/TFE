import hashlib,json,math,subprocess
from pathlib import Path
from datetime import datetime,timezone
R=Path('/workspaces/Tao_Financial_Engine'); B=R/'backups/runtime/a1-speech-specification-20261010'
paths=['native/guala_core/src/functional64_owner.rs','native/guala_core/src/functional64_source.rs','native/guala_core/src/functional64_material.rs','native/guala_core/src/functional64_geometry.rs','native/guala_core/src/functional64_contact.rs','native/guala_core/src/functional64_owner_boundary.rs','native/guala_core/src/virtual_articulated_body.rs','native/guala_core/src/virtual_articulatory_body.rs','dsf_ai_service/guala_functional64_loop.py','dsf_ai_service/lean_actor.py']
records=[]
for rel in paths:
 p=R/rel
 if p.exists():
  raw=p.read_bytes(); records.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'scope':'Selected causal-path source review; no compile or live verification'})
# These are analytic counterexamples, not simulations of Guala or speech evidence.
raw_slots=2621440+67108864+16777216
cases={
 'raw_slot_trace_bytes_three_f64':raw_slots*3*8,
 'raw_slot_trace_GiB':raw_slots*3*8/2**30,
 'trace_2s_remaining_after_10s':math.exp(-10/2),
 'trace_2s_remaining_after_20s':math.exp(-20/2),
 'trace_32s_remaining_after_20s':math.exp(-20/32),
 'native_source_observation_span_ms':(46-1)*10,
 'native_source_steady_stride_ms':(46-21)*10,
 'constant_gain_instability':{'J':10,'gain':.05,'closed_loop_error_multiplier':1-.05*10**2},
 'one_step_delay_counterexample':{'plant':'y[n+1]=u[n-2]','immediate_jacobian':0,'delayed_jacobian_at_3_frames':1},
 'ambiguous_regression_counterexample':{'identical_predictor_state_targets':[-1,1],'least_squares_prediction':0,'observed_target_equal_to_prediction':False},
 'consolidation_transfer':{'stable_before':.3,'labile_before':.2,'fraction':.5,'effective_before':.5,'effective_after':.5},
}
assert cases['constant_gain_instability']['closed_loop_error_multiplier']==-4
assert cases['raw_slot_trace_bytes_three_f64']==2076180480
assert cases['native_source_steady_stride_ms']==250
out={'at_utc':datetime.now(timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'source':records,'analytic_counterexamples':cases,'product_tests_run':False,'live_inspected_this_turn':False,'scope':'Bounded source and mathematical review of the proposed speech specification'}
(B/'review.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'sources':len(records),'counterexamples':cases,'organism_pass_claimed':False}))
