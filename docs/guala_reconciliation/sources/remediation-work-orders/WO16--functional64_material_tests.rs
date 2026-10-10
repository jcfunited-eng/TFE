//! Component falsifiers, not mature-organism or learned-behavior evidence.
use super::*;
fn at_ms(ms:i64)->ExactTime{
    let mut n=ms;let mut d=1000i64;let(mut a,mut b)=(n.unsigned_abs(),d as u64);
    while b!=0{let r=a%b;a=b;b=r;}n/=a as i64;d/=a as i64;ExactTime::new(n,d as u64).unwrap()
}
fn anatomy()->Arc<Anatomy>{
    let geometry=Geometry::new(vec![false;4096].into(),[1.0;64],1.0).unwrap();
    let inputs=(0..INPUTS).map(|index|if index<480{index/60*320+160+index%60}
        else if index<512{let i=index-480;(8+4*(i/16)+(i%16)/4)*320+160+i%4}
        else{let t=index-512;(16+t%8)*320+160+t/8}).map(|i|i as u16).collect::<Vec<_>>();
    Arc::new(Anatomy::declare(geometry,inputs.into(),Arc::from(&b"explicit component fixture; no production-history claim"[..]),500_000,
        vec![ThermalLoad{identity:Arc::from(&b"component-core"[..]),microwatts:41_500_000}].into()).unwrap())
}
fn admission()->Admission{
    let per_trial=(NODES+4*FACTS+INPUTS+TERMINALS)*(MAX_ITERATIONS+1)+TERMINALS*2*circuit_series_limit()*108;
    Admission{max_force_terms:(per_trial*3*((1usize<<(MAX_REFINEMENT+1))-1))as u64,
        max_yield_queries:(NODES*3*((1usize<<(MAX_REFINEMENT+1))-1))as u64,
        max_staged_bytes:Frontier::scratch_bound(NODES,FACTS,64).unwrap(),max_source_bytes:1<<20}
}
fn source_bounds()->AdmissionBounds{AdmissionBounds{max_source_bytes:1<<20,max_frames:46,max_vertices:70985,max_group_members:70985,max_contacts:64,max_payload_bytes:1<<28}}
fn state(weights:&[(u32,f64)],reserve:u64)->Functional64Material{Functional64Material::commission(anatomy(),at_ms(0),weights,reserve).unwrap()}
fn prepare(s:&Functional64Material,ms:i64,power:Vec<PowerPacket>)->Result<PreparedMaterial>{s.prepare_boundary(MaterialInputs{start:at_ms(ms),end:at_ms(ms+1),actual_reserve_ug:s.source_reserve_micrograms(),power,field:None,admission:admission()})}
fn optical(ms:i64)->PowerPacket{PowerPacket{identity:format!("actual-test-illumination-{ms}").into_bytes().into(),receiver:0,origin:PowerOrigin::MeasuredEnvironmental,
    acquired_start:at_ms(ms),acquired_end:at_ms(ms),available:at_ms(ms),release_start:at_ms(ms),release_end:at_ms(ms+1),
    admitted_j:1e-22,lower_j:1e-22,upper_j:1e-22}}
#[test]
fn unpowered_rest_has_no_phase_motion_deformation_or_emission(){
    let s=state(&[(0,-0.0),(1,4.25),((RAW_SLOTS-1)as u32,-2.0)],0);
    let p=prepare(&s,0,Vec::new()).unwrap();
    assert!(p.discharges.is_empty());assert_eq!(p.powered_offset.ticks,0);
    assert!(p.successor.nonzero_nodes.is_empty());assert!(p.successor.contact_changes.allocated().all(|(_,v)|!*v));
    assert_eq!(p.successor.weights.get(0).to_bits(),(-0.0f64).to_bits());
    assert_eq!(p.successor.weights.get(RAW_SLOTS-1).to_bits(),(-2.0f64).to_bits());
    for gate in p.successor.gates.iter(){assert_eq!(gate.y.to_bits(),REST.to_bits());assert_eq!(gate.q,Charge::ZERO);assert_eq!(gate.qm,Charge::ZERO);assert_eq!(gate.qr,Charge::ZERO);}
    assert_eq!(p.evidence.energy_residual_j,0.0);assert_eq!(p.debited_work,Work::ZERO.limbs);
}
#[test]
fn one_reserve_pays_actual_thermal_and_all_constant_power_ports(){
    let s=state(&[],3);let old=s.total_work().unwrap();let p=prepare(&s,0,Vec::new()).unwrap();
    assert_eq!(p.powered_offset.ticks,work_store::FULL_TICKS);assert!(p.discharges.is_empty());
    let thermal=Work::thermal_interval(41_500_000).unwrap();
    let electrical=Work::output_regulator_interval(G,VS).unwrap().mul(TERMINALS as u64).unwrap();
    let debit=thermal.add(electrical).unwrap();assert_eq!(p.debited_work,debit.limbs);
    assert_eq!(p.paid_thermal.len(),1);assert_eq!(p.paid_thermal[0].units,thermal.limbs);
    assert_eq!(old.sub(debit).unwrap(),p.successor.total_work().unwrap());
    assert_eq!(p.supplied_work_units,electrical.limbs);
}
#[test]
fn real_environmental_input_continues_when_reserve_is_zero(){
    let s=state(&[],0);let p=prepare(&s,0,vec![optical(0)]).unwrap();
    assert_eq!(p.powered_offset.ticks,0);assert_eq!(p.successor.source_reserve_micrograms(),0);
    assert!(!p.successor.gates[0].q.magnitude.is_zero());assert!(p.successor.power.is_empty());
    assert_eq!(p.paid_thermal[0].units,Work::ZERO.limbs);assert!(p.discharges.is_empty());
    assert_eq!(p.supplied_work_units,Work::finite_joules(1e-22).unwrap().limbs);
}
#[test]
fn cold_restore_preserves_dormant_history_and_next_physical_successor(){
    let s=state(&[(0,-0.0),(1,4.25),((RAW_SLOTS-1)as u32,-2.0)],0);
    let p=prepare(&s,0,vec![optical(0)]).unwrap();let bytes=p.successor.encode(1<<26,source_bounds()).unwrap();
    let cold=Functional64Material::decode(&bytes,1<<26,source_bounds()).unwrap();
    assert_eq!(bytes,cold.encode(1<<26,source_bounds()).unwrap());
    let continued=prepare(&p.successor,1,vec![optical(1)]).unwrap();let restored=prepare(&cold,1,vec![optical(1)]).unwrap();
    assert_eq!(continued.successor.encode(1<<26,source_bounds()).unwrap(),restored.successor.encode(1<<26,source_bounds()).unwrap());
    assert_eq!(continued.supplied_work_units,restored.supplied_work_units);
    assert_eq!(continued.transducer_heat_units,restored.transducer_heat_units);
}
#[test]
fn invalid_source_and_unresolved_minimum_cut_leave_predecessor_exact(){
    let mut s=state(&[],0);let cost=Work::thermal_interval(41_500_000).unwrap().add(Work::output_regulator_interval(G,VS).unwrap().mul(TERMINALS as u64).unwrap()).unwrap();
    s.work=cost.shr(work_store::CUT_BITS);let before=s.encode(1<<26,source_bounds()).unwrap();
    assert!(matches!(prepare(&s,0,Vec::new()),Err(MaterialError::UnresolvedEvent(_))));
    assert_eq!(before,s.encode(1<<26,source_bounds()).unwrap());
    let mut wrong=optical(0);wrong.origin=PowerOrigin::BodyReserve;
    assert!(matches!(prepare(&s,0,vec![wrong]),Err(MaterialError::Source(_))));
    assert_eq!(before,s.encode(1<<26,source_bounds()).unwrap());
}
#[test]
fn fractional_work_and_assimilation_share_one_canonical_reserve(){
    let mut s=state(&[],499_999);s.work=Work::finite_joules(1e-25).unwrap();let work=s.work;
    let result=s.prepare_assimilation(7).unwrap();assert_eq!(result.assimilated_ug,1);assert_eq!(result.remaining_digestible_ug,6);
    assert_eq!(result.successor.reserve_ug,500_000);assert_eq!(result.successor.work,work);
}
#[test]
fn material_yield_requires_stress_and_accounts_released_contact_energy(){
    // Controlled physical-coordinate fixture for the local return law only.
    // This is not organism experience or a claim of learned behavior.
    let mut anatomy=Arc::try_unwrap(anatomy()).unwrap();
    anatomy.geometry=Geometry::new(vec![false;4096].into(),[g0();64],g0()).unwrap();
    let mut s=Functional64Material::commission(Arc::new(anatomy),at_ms(0),&[],0).unwrap();
    let edge=s.anatomy.contact(2).unwrap();assert_eq!(s.anatomy.geometry.baseline(edge),0.0);
    s.phases.set(edge.from as usize,PhasePair{send:0.1,receive:0.0}).unwrap();
    s.phases.set(edge.to as usize,PhasePair{send:0.0,receive:0.1}).unwrap();
    Arc::make_mut(&mut s.nonzero_nodes).extend([edge.from,edge.to]);
    let mut count=WorkCount::default();let a=admission();let f=Frontier::new(&s,&vec![0.0;INPUTS],&mut count,a).unwrap();
    let old=f.view(&s).unwrap();let mut next=old.clone();
    next.nodes[f.index[edge.from as usize]].send=0.3;next.nodes[f.index[edge.to as usize]].receive=0.3;
    let elastic=s.plastic_return(&f,&old,&old,&mut count,a).unwrap();assert!(elastic.changes.is_empty());
    let yielded=s.plastic_return(&f,&old,&next,&mut count,a).unwrap();
    assert_eq!(yielded.changes.len(),1);assert_eq!(yielded.changes[0].0,2);assert!(yielded.changes[0].1>0.0);
    let v=0.3f64.sin();let w=yielded.changes[0].1;let stress=v*(v-w*v);
    assert!(stress.abs()<=edge.threshold);
    assert!(yielded.heat_j>0.0);assert!(yielded.numerical_dissipation_j>=0.0);
    let released=0.5*s.anatomy.lambda(edge)*(v*v-(v-w*v)*(v-w*v));
    let accounted=yielded.heat_j+yielded.numerical_dissipation_j;
    assert!((released-accounted).abs()<=16.0*f64::EPSILON*released.abs());
}

#[test]
fn query_allowance_does_not_reserve_unreached_contact_pages(){
    let s=state(&[(0,-0.0),(1,4.25),((RAW_SLOTS-1)as u32,-2.0)],0);
    let before=s.encode(1<<26,source_bounds()).unwrap();
    let mut a=admission();a.max_yield_queries=10_000_000;
    let basis=s.allocation_basis(a).unwrap();let mut no_queries=a;no_queries.max_yield_queries=0;
    assert_eq!(basis.next_preparation_payload_bound(),s.logical_size(no_queries).unwrap().preparation_peak_bound);
    assert_eq!(basis.next_admission(0).unwrap().max_staged_bytes,a.max_staged_bytes);
    assert!(basis.next_admission(usize::MAX).is_err());
    // The ordinary numerical transition still runs through its full producer.
    let p=s.prepare_boundary(MaterialInputs{start:at_ms(0),end:at_ms(1),actual_reserve_ug:0,
        power:Vec::new(),field:None,admission:basis.next_admission(0).unwrap()}).unwrap();
    assert_eq!(p.work.contact_growth_bytes,0);assert!(p.discharges.is_empty());
    assert_eq!(before,s.encode(1<<26,source_bounds()).unwrap());
}
#[test]
fn actual_contact_batch_is_admitted_before_any_persistent_page_or_index_write(){
    // Allocation fixture only; these writes are not claimed physical learning.
    let s=state(&[],0);let before=s.encode(1<<26,source_bounds()).unwrap();
    let changes=[(0,0.5),(1,-0.25),(PAGE*FAN,0.125)];
    let a=admission();let mut count=WorkCount::default();let mut successor=s.clone();
    successor.change_weights(&changes,&mut count,a).unwrap();
    assert!(count.contact_growth_bytes>0);
    let actual=successor.logical_size(a).unwrap().retained_material_bytes;
    let prior=s.logical_size(a).unwrap().retained_material_bytes;
    assert!(actual-prior<=count.contact_growth_bytes);
    let mut insufficient=a;insufficient.max_staged_bytes=count.staged_bytes-1;
    let mut refused=s.clone();let mut refused_count=WorkCount::default();
    assert!(matches!(refused.change_weights(&changes,&mut refused_count,insufficient),Err(MaterialError::Capacity("reached contact allocation"))));
    assert_eq!(refused_count.contact_growth_bytes,0);
    assert!(Arc::ptr_eq(&refused.weights.root,&s.weights.root));
    assert!(Arc::ptr_eq(&refused.contact_changes.root,&s.contact_changes.root));
    assert!(Arc::ptr_eq(&refused.incident.root,&s.incident.root));
    assert_eq!(before,refused.encode(1<<26,source_bounds()).unwrap());
    assert_eq!(before,s.encode(1<<26,source_bounds()).unwrap());
    // Same-support deformation does not manufacture more page/index growth.
    let growth=count.contact_growth_bytes;
    successor.change_weights(&[(0,0.75)],&mut count,a).unwrap();
    assert_eq!(growth,count.contact_growth_bytes);
}
#[test]
fn rejected_trial_population_remains_admitted_within_the_same_finite_envelope(){
    let s=state(&[],0);let changes=[(0,0.5)];let a=admission();let mut count=WorkCount::default();
    {let mut discarded=s.clone();discarded.change_weights(&changes,&mut count,a).unwrap();}
    let once=count.contact_growth_bytes;assert!(once>0);
    {let mut discarded=s.clone();discarded.change_weights(&changes,&mut count,a).unwrap();}
    assert_eq!(count.contact_growth_bytes,2*once);
    let mut limited=a;limited.max_staged_bytes=count.staged_bytes+5*once-1;
    let mut refused=s.clone();let old_count=count;
    assert!(matches!(refused.change_weights(&changes,&mut count,limited),Err(MaterialError::Capacity("reached contact allocation"))));
    assert_eq!(count.contact_growth_bytes,old_count.contact_growth_bytes);
    assert_eq!(count.staged_bytes,old_count.staged_bytes);
    assert!(Arc::ptr_eq(&refused.weights.root,&s.weights.root));
    // The next real interval receives the unspent part of this SAME envelope.
    let basis=s.allocation_basis(a).unwrap();let next=basis.next_admission(count.contact_growth_bytes).unwrap();
    assert_eq!(next.max_staged_bytes+5*count.contact_growth_bytes,a.max_staged_bytes);
    assert_eq!(next.max_yield_queries,a.max_yield_queries);
    let mut scratch=WorkCount::default();scratch.contact_growth_bytes=once;
    let too_much=a.max_staged_bytes-5*once+1;
    assert!(matches!(scratch.scratch(too_much,a),Err(MaterialError::Capacity("reached material scratch"))));
}

fn retained_field_fixture(seed:u8,b:AdmissionBounds)->Arc<SharedJointField>{
    use crate::joint_uf_vector::{JointSource,CoordinateDeclaration,EvidenceRef,SourceFrame,ExactRelevance,IntersampleLaw,SourceCompletion};
    let e=EvidenceRef{start:0,end:16};let mut evidence=vec![seed;32];evidence[..16].copy_from_slice(b"component source");
    let source=Arc::new(JointSource{body:evidence.into(),occurrence:e,clock_coordinate_law:e,clock_unit:e,joint_relevance_law:e,
        coordinates:vec![CoordinateDeclaration{physical_quantity:e,physical_unit:e,physical_location:e,source_lineage:e,coordinate_law:e,physical_evidence:e}].into_boxed_slice(),
        groups:vec![vec![0].into_boxed_slice()].into_boxed_slice(),contacts:Vec::new().into_boxed_slice(),
        frames:(0..46).map(|i|SourceFrame{time:at_ms(i*10),coordinates:vec![1.0+(i as f64)*(seed as f64+1.0)/1000.0].into_boxed_slice(),joint_relevance:ExactRelevance::new(1,1).unwrap()}).collect::<Vec<_>>().into_boxed_slice(),
        first_evaluation_index:19,last_evaluation_index:44,
        intersample_law:IntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear{evidence:e},
        completion:Some(SourceCompletion{final_source_index:44,evidence:e})});
    evaluate_joint_source(source,b).unwrap()
}
#[test]
fn occupied_field_cold_restore_admits_actual_payload_with_equal_outer_ceiling(){
    // Two genuine full evaluator results from declared component input series.
    // This fixture is custody/resource evidence, never organism learning.
    let limit=1usize<<24;let mut b=source_bounds();b.max_payload_bytes=limit;
    let mut s=state(&[(0,-0.0),(1,4.25)],0);s.clock=at_ms(500);
    for seed in 1..=2u8{
        let field=retained_field_fixture(seed,b);let durations=validate_field_durations(&field).unwrap();
        assert!(field.admitted_payload_bound()<limit/2);
        s.delivery.push_back(Delivery{field,identity:Arc::from(vec![seed]),published:at_ms(450),gate:0,remaining_ms:durations[0],installed:false});
    }
    let encoded=s.encode(limit,b).unwrap();let original=encoded.clone();
    let restored=Functional64Material::decode(&encoded,limit,b).unwrap();
    assert_eq!(restored.delivery.len(),2);assert_eq!(encoded,original);
    assert_eq!(restored.encode(limit,b).unwrap(),encoded);
    for(a,c)in s.delivery.iter().zip(&restored.delivery){
        assert_eq!(a.field.admitted_payload_bound(),c.field.admitted_payload_bound());
        assert_eq!(encode_joint_source(a.field.source(),b).unwrap(),encode_joint_source(c.field.source(),b).unwrap());
    }
}

#[test]
fn actual_full_uf_negative_field_digits_reach_material_without_second_sign(){
    use crate::joint_uf_vector::{JointSource,CoordinateDeclaration,EvidenceRef,SourceFrame,ExactRelevance,IntersampleLaw,SourceCompletion};
    // Disclosed raw-source kernel fixture, not receptor work or learned behavior.
    // Equal linear-window variance yields repeated identical gates. L4 breathing
    // then becomes negative under its unchanged uncertainty term.
    let e=EvidenceRef{start:0,end:16};
    let source=Arc::new(JointSource{body:Arc::from(&b"negative UF test"[..]),occurrence:e,clock_coordinate_law:e,clock_unit:e,joint_relevance_law:e,
        coordinates:vec![CoordinateDeclaration{physical_quantity:e,physical_unit:e,physical_location:e,source_lineage:e,coordinate_law:e,physical_evidence:e}].into_boxed_slice(),
        groups:vec![vec![0].into_boxed_slice()].into_boxed_slice(),contacts:Vec::new().into_boxed_slice(),
        frames:(0..46).map(|i|SourceFrame{time:at_ms(i*10),coordinates:vec![100.0*i as f64].into_boxed_slice(),
            joint_relevance:ExactRelevance::new(0,1).unwrap()}).collect::<Vec<_>>().into_boxed_slice(),
        first_evaluation_index:19,last_evaluation_index:44,
        intersample_law:IntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear{evidence:e},
        completion:Some(SourceCompletion{final_source_index:44,evidence:e})});
    let field=evaluate_joint_source(source,source_bounds()).unwrap();
    assert_eq!(field.gates().len(),25);assert!(field.gates()[1].dsf.b_k<0.0);
    let mut negative_fields=0usize;
    for(gate_index,gate)in field.gates().iter().enumerate(){
        let facts=Functional64Material::facts_for(&field,gate_index).unwrap();
        for(family,value)in gate.dsf.ordered().iter().enumerate(){
            if *value<0.0{negative_fields+=1;}
            let rational=float_to_rational_trits(*value).unwrap();
            for(role,digits)in[&rational.numerator_trits,&rational.denominator_trits].iter().enumerate(){
                for position in 0..679{
                    let fact=facts[(role*679+position)*7+family];
                    assert_eq!(fact.present,position<digits.len());
                    assert_eq!(fact.digit,digits.get(position).copied().unwrap_or(0));
                }
            }
        }
    }
    assert!(negative_fields>0);
}

#[test]
fn source_ceiling_is_not_occupied_material_and_shared_sources_are_counted_once(){
    let b=source_bounds();let a=admission();let mut s=state(&[],0);
    let first=retained_field_fixture(1,b);let second=retained_field_fixture(2,b);
    let identity:Arc<[u8]>=Arc::from(&b"actual fixture field identity"[..]);
    s.delivery.push_back(Delivery{field:first.clone(),identity:identity.clone(),published:at_ms(0),gate:0,remaining_ms:1,installed:false});
    let before=s.encode(1<<24,b).unwrap();let small=s.logical_size(a).unwrap();
    let mut larger=a;larger.max_source_bytes=usize::MAX;
    assert_eq!(small.preparation_peak_bound,s.logical_size(larger).unwrap().preparation_peak_bound);
    let basis=s.allocation_basis(a).unwrap();
    assert_eq!(basis.source_payload_bound(&s,0,0).unwrap(),first.admitted_payload_bound()+identity.len());
    assert_eq!(basis.next_preparation_payload_bound()+first.admitted_payload_bound(),small.preparation_peak_bound);
    let mut successor=s.clone();successor.delivery.clear();
    successor.delivery.push_back(Delivery{field:second.clone(),identity:identity.clone(),published:at_ms(0),gate:0,remaining_ms:1,installed:false});
    assert_eq!(basis.source_payload_bound(&successor,0,0).unwrap(),
        first.admitted_payload_bound()+second.admitted_payload_bound()+identity.len());
    assert_eq!(before,s.encode(1<<24,b).unwrap());
    // Multiple ports can borrow one real acquisition identity. Its bytes are
    // retained once; this is allocation custody, not repeated physical power.
    let mut p=optical(0);p.identity=identity.clone();let mut q=p.clone();q.receiver=1;
    assert_eq!(material_source_payload(&successor,&[Some(first),None],&[p,q],None).unwrap(),
        basis.source_payload_bound(&successor,0,0).unwrap());
}


#[test]
fn recovered_baselines_follow_only_the_existing_skeleton_and_inter_masks(){
    let g=anatomy().geometry.clone();
    for &(from,to,b)in &[(160,32,0.5),(160,33,0.5),(160,34,0.0),(32,224,0.5),(33,224,0.0),(224,288,0.5),(225,288,0.0),(32,32,0.0)]{
        assert_eq!(g.baseline(g.between(from,to).unwrap()),b);
    }
    for(width,offset)in[(128,32),(64,224)]{for i in 0..width{
        let mask=Geometry::inter_mask(i,width).unwrap();
        for j in 0..width{let edge=g.between(offset+i,320+offset+j);let mounted=mask[j/64]&(1u64<<(j%64))!=0;
            assert_eq!(edge.is_some(),mounted);if let Some(e)=edge{assert_eq!(g.baseline(e).to_bits(),g0().to_bits());}
        }
    }}
}

#[test]
fn recovered_skeleton_contact_at_old_fixture_stress_remains_elastic(){
    // Same phase path as the original return-law fixture, now explicitly on
    // the recovered .5 skeleton. Its stress is below the unchanged yield.
    let mut an=Arc::try_unwrap(anatomy()).unwrap();an.geometry=Geometry::new(vec![true;4096].into(),[g0();64],g0()).unwrap();
    let mut s=Functional64Material::commission(Arc::new(an),at_ms(0),&[],0).unwrap();let e=s.anatomy.contact(0).unwrap();
    assert_eq!(s.anatomy.geometry.baseline(e),0.5);
    s.phases.set(e.from as usize,PhasePair{send:0.1,receive:0.0}).unwrap();s.phases.set(e.to as usize,PhasePair{send:0.0,receive:0.1}).unwrap();
    Arc::make_mut(&mut s.nonzero_nodes).extend([e.from,e.to]);let mut count=WorkCount::default();let a=admission();
    let f=Frontier::new(&s,&vec![0.0;INPUTS],&mut count,a).unwrap();let old=f.view(&s).unwrap();let mut next=old.clone();
    next.nodes[f.index[e.from as usize]].send=0.3;next.nodes[f.index[e.to as usize]].receive=0.3;
    let stress=0.3f64.sin()*(0.3f64.sin()-0.5*0.3f64.sin());assert!(stress.abs()<e.threshold);
    let returned=s.plastic_return(&f,&old,&next,&mut count,a).unwrap();assert!(returned.changes.iter().all(|&(slot,_)|slot!=0));
    assert_eq!(*s.weights.get(0),0.0);
}

fn two_column_contact_fixture()->Functional64Material{
    // Algebra/geometry fixture only; these coordinates are not learned state.
    let mut an=Arc::try_unwrap(anatomy()).unwrap();let mut severed=vec![true;4096];severed[1]=false;severed[64]=false;
    an.geometry=Geometry::new(severed.into(),[1.0;64],1.0).unwrap();
    let canceled=an.geometry.between(32,352).unwrap().authentic_slot;
    let reversed=an.geometry.between(33,354).unwrap().authentic_slot;
    let mut s=Functional64Material::commission(Arc::new(an),at_ms(0),&[(2,0.125),(canceled,-g0()),(reversed,-0.25)],0).unwrap();
    for(node,phase)in[(160,PhasePair{send:0.1,receive:-0.05}),(352,PhasePair{send:-0.15,receive:0.2})]{
        s.phases.set(node,phase).unwrap();Arc::make_mut(&mut s.nonzero_nodes).insert(node as u16);
    }s
}

#[test]
fn aggregate_contacts_enclose_direct_positive_squares_and_reciprocal_work(){
    let s=two_column_contact_fixture();let mut count=WorkCount::default();let a=admission();
    let f=Frontier::new(&s,&vec![0.0;INPUTS],&mut count,a).unwrap();let old=f.view(&s).unwrap();let mut new=old.clone();
    for(i,p)in new.nodes.iter_mut().enumerate(){p.send+=((i%7)as f64-3.0)/10000.0;p.receive+=((i%5)as f64-2.0)/10000.0;}
    let start=contact_operator::energy(&s,&f,&old,&[],&mut count,a).unwrap();
    let end=contact_operator::energy(&s,&f,&new,&[],&mut count,a).unwrap();
    let force=contact_operator::forces(&s,&f,&old,&new,&mut count,a).unwrap();
    let mut direct_energy=Interval::point(0.0);let mut direct_forces=vec![[Interval::point(0.0);2];f.nodes.len()];let mut direct_count=0usize;
    for &to in &f.nodes{
        s.anatomy.geometry.visit_incoming(to,|e|{
            let gain=s.anatomy.geometry.baseline(e)+*s.weights.get(e.authentic_slot as usize);let l=s.anatomy.lambda(e);
            let p=f.pair(&old,&s,e.from as usize);let q=f.pair(&new,&s,e.from as usize);
            let r=f.pair(&old,&s,e.to as usize);let t=f.pair(&new,&s,e.to as usize);
            let v=0.5*(p.send.sin()+q.send.sin());let u=0.5*(r.receive.sin()+t.receive.sin());
            let residual=Interval::point(u).sub(Interval::point(gain).mul(Interval::point(v)));
            let source=if gain==0.0{Interval::point(0.0)}else{Interval::point(-l).mul(Interval::point(gain)).mul(residual).mul(Interval::point(dsin(p.send,q.send)))};
            let target=Interval::point(l).mul(residual).mul(Interval::point(dsin(r.receive,t.receive)));
            let i=f.index[e.from as usize];let j=f.index[e.to as usize];
            if i!=usize::MAX{direct_forces[i][0]=direct_forces[i][0].add(source);}else{assert_eq!(source.lo,0.0);assert_eq!(source.hi,0.0);}
            direct_forces[j][1]=direct_forces[j][1].add(target);
            let z=Interval::point(t.receive.sin()).sub(Interval::point(gain).mul(Interval::point(q.send.sin())));
            direct_energy=direct_energy.add(Interval::point(0.5*l).mul(z.mul(z)));direct_count+=1;Ok(())
        }).unwrap();
    }
    assert!(direct_count>f.nodes.len());assert!(start.value>=0.0&&end.value>=0.0);
    assert!(end.range.lo<=direct_energy.hi&&direct_energy.lo<=end.range.hi);
    let mut work=Interval::point(0.0);
    for i in 0..f.nodes.len(){
        for role in 0..2{let lhs=force.ranges[i][role];let rhs=direct_forces[i][role];assert!(lhs.lo<=rhs.hi&&rhs.lo<=lhs.hi);}
        work=work.add(force.ranges[i][0].mul(Interval::point(new.nodes[i].send-old.nodes[i].send)));
        work=work.add(force.ranges[i][1].mul(Interval::point(new.nodes[i].receive-old.nodes[i].receive)));
    }
    let delta=Interval{lo:down(end.range.lo-start.range.hi),hi:up(end.range.hi-start.range.lo)};
    // Finite sine/divided-sine evaluation is reported separately from exact
    // real DG algebra; its ordinary roundoff must fit the unchanged tolerance.
    let gap=(delta.lo-work.hi).max(work.lo-delta.hi).max(0.0);
    let scale=start.value.abs()+end.value.abs()+work.absmax();assert!(gap<=SOLVE_TOL*scale);
}

#[test]
fn canceled_bridge_contributes_no_source_force_even_with_other_contact_activity(){
    let s=two_column_contact_fixture();let mut count=WorkCount::default();let a=admission();let f=Frontier::new(&s,&vec![0.0;INPUTS],&mut count,a).unwrap();
    let mut x=f.view(&s).unwrap();for p in &mut x.nodes{*p=PhasePair::default();}
    x.nodes[f.index[352]].receive=0.2;
    let force=contact_operator::forces(&s,&f,&x,&x,&mut count,a).unwrap();
    // All send phases and all other receive phases are zero. The only path
    // from source32 to this receive352 has finite b+w exactly zero.
    assert_eq!(force.nodes[f.index[32]].send.to_bits(),0.0f64.to_bits());
    assert!(force.nodes[f.index[33]].send!=0.0);
    assert_eq!((*s.weights.get(s.anatomy.geometry.between(32,352).unwrap().authentic_slot as usize)).to_bits(),(-g0()).to_bits());
}

#[test]
fn real_full_field_starts_resting_paths_and_cold_replays_the_same_material_transition(){
    // Complete raw-source evaluation, never a fabricated SharedJointField or
    // pre-excited motor state. This is causal component evidence, not language.
    let field=retained_field_fixture(1,source_bounds());let an=anatomy();
    let s=Functional64Material::commission(an,at_ms(450),&[],500_000).unwrap();let before=s.encode(1<<26,source_bounds()).unwrap();
    let first=s.prepare_boundary(MaterialInputs{start:at_ms(450),end:at_ms(451),actual_reserve_ug:500_000,power:Vec::new(),
        field:Some((field,Arc::from(&b"real-evaluator-fixture"[..]),at_ms(450))),admission:admission()}).unwrap();
    assert_eq!(before,s.encode(1<<26,source_bounds()).unwrap());
    assert!(first.successor.nonzero_nodes.iter().any(|&n|n/320==0));
    assert!(first.successor.nonzero_nodes.iter().any(|&n|n/320==63));
    assert!(first.successor.gates[INPUTS..].iter().any(|g|g.y!=REST),
        "one-ms gate failure: changed_columns={}; terminal maxima [send, receive, difference, sine difference] \
         rows=(terminal,node,metric,send,receive,send_bits,receive_bits,gate_y_bits)={:?}; \
         largest_gate_delta=(terminal,node,delta,y,y_bits)={:?}; \
         respiration=(node,send,receive,send_bits,receive_bits,y_bits)={:?}; rest_bits={:#018x}",
        {
            let mut changed=[false;64];
            for &node in first.successor.nonzero_nodes.iter(){changed[node as usize/320]=true;}
            changed.iter().filter(|&&value|value).count()
        },
        {
            let mut maxima=[(0usize,0.0f64);4];
            for terminal in 0..TERMINALS{
                let phase=*first.successor.phases.get(Anatomy::terminal_node(terminal));
                let values=[phase.send.abs(),phase.receive.abs(),(phase.receive-phase.send).abs(),
                    (phase.receive.sin()-phase.send.sin()).abs()];
                for metric in 0..4{if values[metric]>maxima[metric].1{maxima[metric]=(terminal,values[metric]);}}
            }
            maxima.map(|(terminal,value)|{
                let node=Anatomy::terminal_node(terminal);let phase=*first.successor.phases.get(node);
                (terminal,node,value,phase.send,phase.receive,phase.send.to_bits(),phase.receive.to_bits(),
                    first.successor.gates[INPUTS+terminal].y.to_bits())
            })
        },
        {
            let mut maximum=(0usize,0.0f64);
            for terminal in 0..TERMINALS{let delta=(first.successor.gates[INPUTS+terminal].y-REST).abs();
                if delta>maximum.1{maximum=(terminal,delta);}}
            let y=first.successor.gates[INPUTS+maximum.0].y;
            (maximum.0,Anatomy::terminal_node(maximum.0),maximum.1,y,y.to_bits())
        },
        {
            let node=Anatomy::terminal_node(96);let phase=*first.successor.phases.get(node);
            (node,phase.send,phase.receive,phase.send.to_bits(),phase.receive.to_bits(),
                first.successor.gates[INPUTS+96].y.to_bits())
        },REST.to_bits());
    assert!(first.evidence.contact_energy_change_lower_j<=first.evidence.contact_energy_change_upper_j);
    let bytes=first.successor.encode(1<<26,source_bounds()).unwrap();let restored=Functional64Material::decode(&bytes,1<<26,source_bounds()).unwrap();
    let live=prepare(&first.successor,451,Vec::new()).unwrap();let cold=prepare(&restored,451,Vec::new()).unwrap();
    assert_eq!(live.successor.encode(1<<26,source_bounds()).unwrap(),cold.successor.encode(1<<26,source_bounds()).unwrap());
    assert_eq!(live.discharges.iter().map(|d|(d.terminal,d.carriers,d.at.parts())).collect::<Vec<_>>(),cold.discharges.iter().map(|d|(d.terminal,d.carriers,d.at.parts())).collect::<Vec<_>>());
    assert_eq!(live.evidence.contact_energy_change_j.to_bits(),cold.evidence.contact_energy_change_j.to_bits());
    assert_eq!(live.evidence.contact_energy_change_lower_j.to_bits(),cold.evidence.contact_energy_change_lower_j.to_bits());
    assert_eq!(live.evidence.contact_energy_change_upper_j.to_bits(),cold.evidence.contact_energy_change_upper_j.to_bits());
}

#[test]
fn contact_stress_extrema_keep_repeated_coordinate_dependency_for_both_gain_signs(){
    let path=Interval::sin_path(0.1,0.3).unwrap();
    let tensile=contact_stress_range(path,path,0.5).unwrap();
    // For this entire rectangle, the concave maximum is at v=u_max,
    // with value u_max²/2. The old independent-product box falsely crossed Y.
    let maximum=0.5*path.hi*path.hi;
    assert!(tensile.lo<=maximum&&maximum<=tensile.hi);
    assert!(tensile.absmax()<g0());
    let reverse=contact_stress_range(Interval{lo:-0.5,hi:0.25},Interval{lo:-0.3,hi:0.4},-0.75).unwrap();
    // Convex minimum at u=.4,v=-4/15; maximum at u=-.3,v=-.5.
    assert!(reverse.lo<=-4.0/75.0);assert!(reverse.hi>=27.0/80.0);
    let zero=contact_stress_range(Interval{lo:-0.5,hi:0.25},Interval{lo:-0.3,hi:0.4},0.0).unwrap();
    assert!(zero.lo<=-0.2);assert!(zero.hi>=0.15);
}

#[test]
fn packet_voltage_rounding_certifies_subnormal_work_and_preserves_valid_drives(){
    fn old_candidate(j:f64,ms:u8)->f64{
        if j==0.0{return 0.0;}
        let p=down(j/up(ms as f64/1000.0)).max(0.0);
        let ratio=down(p/G).max(0.0);down(ratio.sqrt()).max(0.0)
    }
    for ms in [1u8,10]{
        let mut packet=optical(0);packet.receiver=if ms==10{480}else{0};packet.release_end=at_ms(ms as i64);
        if ms==10{packet.acquired_start=at_ms(-10);}
        packet.admitted_j=f64::from_bits(1);packet.lower_j=packet.admitted_j;packet.upper_j=packet.admitted_j;
        let old=old_candidate(packet.admitted_j,ms);let duration=up(ms as f64/1000.0);
        let rejected=packet_voltage_power_upper(old,duration);
        assert!(rejected>packet.admitted_j,"work_bits={} old_voltage_bits={} upper_bits={} release_ms={ms}",packet.admitted_j.to_bits(),old.to_bits(),rejected.to_bits());
        let actual=packet_source_voltage(&packet,ms).unwrap();
        assert!(actual<=old);assert!(packet_voltage_power_upper(actual,duration)<=packet.admitted_j);
        assert!(actual.to_bits()<old.to_bits());
        assert!(packet_voltage_power_upper(f64::from_bits(actual.to_bits()+1),duration)>packet.admitted_j);
        packet.admitted_j=1e-22;packet.lower_j=packet.admitted_j;packet.upper_j=packet.admitted_j;
        let accepted=old_candidate(packet.admitted_j,ms);
        assert!(packet_voltage_power_upper(accepted,duration)<=packet.admitted_j);
        assert_eq!(packet_source_voltage(&packet,ms).unwrap().to_bits(),accepted.to_bits());
        packet.admitted_j=0.0;packet.lower_j=0.0;packet.upper_j=0.0;
        assert_eq!(packet_source_voltage(&packet,ms).unwrap().to_bits(),0.0f64.to_bits());
    }
}

// Frozen endpoint elastic reaction only. The moving-capacitance path now
// supplies its own integrated capacitor reaction; the retired endpoint DG
// capacitor force is deliberately not asserted as the active law.
#[test]
fn endpoint_elastic_gate_terms_match_frozen_mechanical_bits(){
    let s=state(&[],0);let limit=admission();let mut count=WorkCount::default();
    let f=Frontier::new(&s,&vec![1.0;INPUTS],&mut count,limit).unwrap();
    let mut before=f.view(&s).unwrap();let mut after=before.clone();
    let phases=[-0.75,-0.0,0.0,0.125,0.625];
    for i in 0..f.nodes.len(){
        before.nodes[i]=PhasePair{send:phases[i%5],receive:phases[(i+1)%5]};
        after.nodes[i]=PhasePair{send:phases[(i+2)%5],receive:phases[(i+3)%5]};
    }
    let apertures=[REST,0.0,1.0,0.375,0.75];let charges=[0.0,1e-22,3e-20,2e-19,0.0];
    for i in 0..before.gates.len(){
        before.gates[i]=NumericalGate{y:apertures[i%5],q:charges[i%5],qm:charges[(i+1)%5],qr:charges[(i+2)%5]};
        after.gates[i]=NumericalGate{y:apertures[(i+1)%5],q:charges[(i+2)%5],qm:charges[(i+3)%5],qr:charges[(i+4)%5]};
    }
    let mut input_count=0;let mut output_count=0;let mut stops=0;let mut rest=0;
    for i in 0..before.gates.len(){
        let input=i<INPUTS;
        let node=if input{s.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-INPUTS)};
        let p=f.pair(&before,&s,node);let q=f.pair(&after,&s,node);
        let e0=before.gates[i].y-REST-ALPHA*(p.receive.sin()-p.send.sin());
        let e1=after.gates[i].y-REST-ALPHA*(q.receive.sin()-q.send.sin());
        let expected=0.5*(e0+e1);
        let actual=gate_reaction_terms(p,q,before.gates[i],after.gates[i]);
        assert_eq!(actual.to_bits(),expected.to_bits(),"gate elastic term {i}");
        if input{input_count+=1;}else{output_count+=1;}
        stops+=usize::from(after.gates[i].y==0.0||after.gates[i].y==1.0);
        rest+=usize::from(before.gates[i].y==REST||after.gates[i].y==REST);
    }
    assert_eq!(input_count,INPUTS);assert_eq!(output_count,TERMINALS);assert!(stops>0&&rest>0);
}

// Component arithmetic equivalence, not organism learning or live readiness.
#[test]
fn common_start_matches_two_fresh_starts_in_every_physical_bit(){
    fn evidence_bits(e:WorkEvidence)->[u64;19]{[
        e.supply_j,e.field_switch_j,e.source_heat_j,e.contact_heat_j,e.phase_heat_j,e.gate_heat_j,
        e.exported_j,e.plastic_heat_j,e.return_map_dissipation_j,e.stop_dissipation_j,e.energy_residual_j,
        e.nonlinear_bound,e.error_estimate,e.circuit_tail_charge_c,e.circuit_tail_work_j,e.circuit_projection_defect_v,
        e.contact_energy_change_j,e.contact_energy_change_lower_j,e.contact_energy_change_upper_j,
    ].map(f64::to_bits)}
    fn same(a:&TrialStep,b:&TrialStep){
        assert_eq!(a.state.encode(1<<26,source_bounds()).unwrap(),b.state.encode(1<<26,source_bounds()).unwrap());
        assert_eq!(a.emitted,b.emitted);assert_eq!(a.supplied,b.supplied);assert_eq!(a.transducer_heat,b.transducer_heat);
        assert_eq!(evidence_bits(a.evidence),evidence_bits(b.evidence));
    }
    let mut s=state(&[(0,-0.0),((RAW_SLOTS-1)as u32,-2.0)],0);
    let packet=optical(0);let release_ms=packet_release_ms(&packet).unwrap();
    let source_voltage=packet_source_voltage(&packet,release_ms).unwrap();
    s.last_power[0]=Some(packet.release_end);
    s.power.push(PendingPower{remaining:Work::finite_joules(packet.admitted_j).unwrap(),packet,source_voltage,release_ms});
    let before=s.encode(1<<26,source_bounds()).unwrap();let drive=s.physical_drives(false).unwrap();let limit=admission();
    let span=work_store::FULL_TICKS;let half=span/2;
    let mut shared_work=WorkCount::default();
    let(shared_coarse,shared_half)={
        let mut start=CommonStart::new(&s,&drive,&mut shared_work,limit).unwrap();
        assert!(start.initial_gradient.is_none()&&start.initial_energy.is_none());
        let coarse=start.trial(span,&mut shared_work,limit).unwrap();
        assert!(start.initial_gradient.is_some()&&start.initial_energy.is_some());
        let shared_bound=start.frontier.scratch_base;
        let first=start.trial(half,&mut shared_work,limit).unwrap();
        assert_eq!(start.frontier.scratch_base,shared_bound);
        (coarse,first)
    };
    let mut fresh_work=WorkCount::default();
    let fresh_coarse=s.trial(span,&drive,&mut fresh_work,limit).unwrap();
    let fresh_half=s.trial(half,&drive,&mut fresh_work,limit).unwrap();
    same(&shared_coarse,&fresh_coarse);same(&shared_half,&fresh_half);
    assert!(!shared_half.state.gates[0].q.magnitude.is_zero());
    assert_eq!(s.encode(1<<26,source_bounds()).unwrap(),before);
    assert!(shared_work.force_terms<fresh_work.force_terms);
    eprintln!("common_start force_terms shared={} fresh={} saved={}",shared_work.force_terms,fresh_work.force_terms,fresh_work.force_terms-shared_work.force_terms);
}

// Captured Build12 output-circuit component state, not a reconstructed organism.
// All 97 actual output gates had this same qm, REST aperture and zero qr.
// The independent reference is the existing closed RC law, not another call
// to the positive-uniformization circuit operator.
#[test]
fn captured_closed_output_headroom_survives_subdivision_and_current_codec(){
    fn within(actual:f64,expected:f64,label:&str){
        assert!(actual.is_finite()&&expected.is_finite(),"{label}: nonfinite evidence");
        let scale=actual.abs().max(expected.abs());
        if scale==0.0{assert_eq!(actual,expected,"{label}");}
        else{assert!((actual-expected).abs()/scale<=RTOL,
            "{label}: actual={actual:e}, expected={expected:e}, relative_error={:e}, RTOL={RTOL:e}",
            (actual-expected).abs()/scale);}
    }
    fn run(gate:Gate,h:f64)->CircuitStep{
        output_circuit(gate,REST,h,true,&mut WorkCount::default(),admission()).unwrap()
    }
    fn same_gate(a:Gate,b:Gate){
        assert_eq!(a.y.to_bits(),b.y.to_bits());assert_eq!(a.q,b.q);
        assert_eq!(a.qm,b.qm);assert_eq!(a.qr,b.qr);assert_eq!(a.load,b.load);
    }
    fn same_step(a:&CircuitStep,b:&CircuitStep){
        same_gate(a.gate,b.gate);
        assert_eq!([a.source_j,a.resistor_j,a.exported_j,a.load_c,a.tail_charge_c,a.tail_work_j,a.projection_defect_v].map(f64::to_bits),
            [b.source_j,b.resistor_j,b.exported_j,b.load_c,b.tail_charge_c,b.tail_work_j,b.projection_defect_v].map(f64::to_bits));
    }
    let qm=Charge{negative:false,magnitude:crate::mathloom::Uint1152{limbs:[
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        2432999329942732800,14137321013748821445,365,0,
    ]}};
    qm.validate().unwrap();
    let mut gate=Gate::new();gate.qm=qm;
    let product=CM*VS;
    let equilibrium=Charge::packet(product).unwrap().add_packet(CM.mul_add(VS,-product)).unwrap();
    let deficit=equilibrium.add(qm.neg()).unwrap();
    assert!(!deficit.negative&&!deficit.magnitude.is_zero());
    let deficit_c=deficit.projection().unwrap();
    // Independently calculated from the actual captured limbs and the exact
    // fixed binary64 CM/VS operands in the Build12 Fraction receipt.
    assert_eq!(deficit_c.to_bits(),1.2926374171271613e-24f64.to_bits());
    let gap_v=deficit_c/CM;
    let legacy_gap=VS-qm.projection().unwrap()/CM;
    assert!((legacy_gap-gap_v).abs()/gap_v>RTOL,
        "captured state must expose the original cancellation defect");
    assert_eq!(source_voltage_headroom(qm).unwrap().to_bits(),gap_v.to_bits());

    let h=0.001;
    let exponent=-G*h/CM;
    let expected_charge=deficit_c*(-exponent.exp_m1());
    let expected_remaining=deficit_c*exponent.exp();
    let expected_source=VS*expected_charge;
    let expected_heat=0.5*CM*gap_v*gap_v*(-(2.0*exponent).exp_m1());
    assert!(expected_charge>0.0&&expected_remaining>0.0&&expected_source>0.0&&expected_heat>0.0);
    let whole=run(gate,h);let half=run(gate,h/2.0);let split=run(half.gate,h/2.0);
    let whole_charge=whole.gate.qm.add(qm.neg()).unwrap().projection().unwrap();
    let split_charge=split.gate.qm.add(qm.neg()).unwrap().projection().unwrap();
    let whole_remaining=equilibrium.add(whole.gate.qm.neg()).unwrap().projection().unwrap();
    let split_remaining=equilibrium.add(split.gate.qm.neg()).unwrap().projection().unwrap();
    within(whole_charge,expected_charge,"whole source charge vs closed RC law");
    within(split_charge,expected_charge,"split source charge vs closed RC law");
    within(whole_remaining,expected_remaining,"whole retained deficit vs closed RC law");
    within(split_remaining,expected_remaining,"split retained deficit vs closed RC law");
    within(whole.source_j,expected_source,"whole source work vs closed RC law");
    within(half.source_j+split.source_j,expected_source,"split source work vs closed RC law");
    within(whole.resistor_j,expected_heat,"whole resistor heat vs closed RC law");
    within(half.resistor_j+split.resistor_j,expected_heat,"split resistor heat vs closed RC law");
    within(whole.source_j,half.source_j+split.source_j,"coarse/fine source work");
    within(whole.resistor_j,half.resistor_j+split.resistor_j,"coarse/fine resistor heat");
    for step in [&whole,&half,&split]{
        assert_eq!(step.gate.y.to_bits(),REST.to_bits());assert_eq!(step.gate.qr,Charge::ZERO);
        assert_eq!(step.load_c,0.0);assert_eq!(step.exported_j,0.0);
    }

    // Only the captured output state is transplanted into this disclosed codec
    // fixture. The rest of this new fixture is not claimed as captured history.
    let mut original=state(&[],500_000);
    Arc::make_mut(&mut original.gates)[INPUTS..].fill(gate);
    let bytes=original.encode(1<<26,source_bounds()).unwrap();
    let cold=Functional64Material::decode(&bytes,1<<26,source_bounds()).unwrap();
    assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),bytes);
    for retained in &cold.gates[INPUTS..]{same_gate(*retained,gate);}
    let restored_gate=cold.gates[INPUTS];
    same_step(&whole,&run(restored_gate,h));
    let cold_half=run(restored_gate,h/2.0);same_step(&half,&cold_half);
    same_step(&split,&run(cold_half.gate,h/2.0));
    assert_eq!(original.encode(1<<26,source_bounds()).unwrap(),bytes);
}

// Closed input-RC arithmetic regimes. Coordinates here are explicitly
// constructed component fixtures, not captured mature-organism experience.
#[test]
fn input_current_packet_custody_and_heat_cover_equilibrium_signs_and_cold(){
    fn within(actual:f64,expected:f64,label:&str){
        assert!(actual.is_finite()&&expected.is_finite(),"{label}: nonfinite evidence");
        let scale=actual.abs().max(expected.abs());
        if scale==0.0{assert_eq!(actual,expected,"{label}");}
        else{assert!((actual-expected).abs()/scale<=RTOL,
            "{label}: actual={actual:e}, expected={expected:e}, relative_error={:e}, RTOL={RTOL:e}",
            (actual-expected).abs()/scale);}
    }
    fn reference_equilibrium(capacitance:f64,voltage:f64)->Charge{
        let product=capacitance*voltage;
        Charge::packet(product).unwrap().add_packet(capacitance.mul_add(voltage,-product)).unwrap()
    }
    fn step(q0:Charge,capacitance:f64,voltage:f64,h:f64)->(Charge,f64,f64,f64){
        let path=input_path_step(q0,capacitance,capacitance,voltage,h,&mut WorkCount::default(),admission()).unwrap();
        let dq=path.dq;let heat=path.resistor_heat;
        assert!(heat.is_finite()&&heat>=0.0,"negative/nonfinite input resistor work");
        let next=q0.add_packet(dq).unwrap();assert!(!next.negative);
        (next,dq,voltage*dq,heat)
    }
    fn check(q0:Charge,capacitance:f64,voltage:f64,h:f64){
        let equilibrium=reference_equilibrium(capacitance,voltage);
        assert_eq!(equilibrium_charge(capacitance,voltage).unwrap(),equilibrium);
        let deficit=equilibrium.add(q0.neg()).unwrap();let delta=deficit.projection().unwrap();
        let exponent=-G*h/capacitance;
        let expected_dq=delta*(-exponent.exp_m1());
        let expected_remaining=delta*exponent.exp();
        let gap=delta/capacitance;
        let expected_heat=0.5*capacitance*gap*gap*(-(2.0*exponent).exp_m1());
        let whole=step(q0,capacitance,voltage,h);
        let first=step(q0,capacitance,voltage,h/2.0);
        let second=step(first.0,capacitance,voltage,h/2.0);
        // Actual custody must contain exactly the one admitted finite packet.
        assert_eq!(whole.0.add(q0.neg()).unwrap(),Charge::packet(whole.1).unwrap());
        let split_packet=Charge::packet(first.1).unwrap().add_packet(second.1).unwrap();
        assert_eq!(second.0.add(q0.neg()).unwrap(),split_packet);
        let split_dq=split_packet.projection().unwrap();
        within(whole.1,expected_dq,"whole input charge vs independent RC exponential");
        within(split_dq,expected_dq,"split input charge vs independent RC exponential");
        within(equilibrium.add(whole.0.neg()).unwrap().projection().unwrap(),expected_remaining,
            "whole retained charge deficit");
        within(equilibrium.add(second.0.neg()).unwrap().projection().unwrap(),expected_remaining,
            "split retained charge deficit");
        within(whole.2,voltage*expected_dq,"whole signed source work");
        within(first.2+second.2,voltage*expected_dq,"split signed source work");
        within(whole.3,expected_heat,"whole discrete-gradient heat vs independent RC exponential");
        within(first.3+second.3,expected_heat,"split discrete-gradient heat vs independent RC exponential");
        within(whole.1,split_dq,"coarse/fine input charge");
        within(whole.2,first.2+second.2,"coarse/fine input source work");
        within(whole.3,first.3+second.3,"coarse/fine input resistor heat");
        if deficit.magnitude.is_zero(){
            assert_eq!(whole.0,q0);assert_eq!(second.0,q0);
            for value in [whole.1,whole.2,whole.3,first.1,first.2,first.3,second.1,second.2,second.3]{assert_eq!(value,0.0);}
        }else{
            assert_eq!(whole.1.is_sign_negative(),deficit.negative);
            assert_eq!(split_dq.is_sign_negative(),deficit.negative);
            assert!(whole.3>0.0&&first.3+second.3>0.0);
        }
    }
    let voltage=packet_source_voltage(&optical(0),1).unwrap();assert!(voltage>0.0);
    let capacities=[CM,CM+CR,2.0/(1.0/CM+1.0/(CM+CR))];
    // The largest ordinary interval and the smallest span whose two halves
    // both lie on the existing exact event grid; no new elapsed horizon.
    let durations=[physical_duration(work_store::FULL_TICKS).unwrap(),physical_duration(2).unwrap()];
    for capacitance in capacities{
        let equilibrium=reference_equilibrium(capacitance,voltage);
        let product=capacitance*voltage;let ulp=up(product)-product;assert!(ulp>0.0);
        for delta in [-ulp,-ulp/16.0,0.0,ulp/16.0,ulp]{
            let q0=equilibrium.add(Charge::packet(delta).unwrap().neg()).unwrap();assert!(!q0.negative);
            assert_eq!(equilibrium.add(q0.neg()).unwrap(),Charge::packet(delta).unwrap());
            for h in durations{check(q0,capacitance,voltage,h);}
        }
        // Same capacitor after source removal: authentic stored charge may
        // discharge, with zero source work and nonnegative resistor heat.
        for h in durations{check(equilibrium,capacitance,0.0,h);}
    }

    // Preserve an exact sub-ULP retained charge through the actual current
    // codec, then use that same original charge for the next circuit interval.
    let product=CM*voltage;let ulp=up(product)-product;
    let original_charge=reference_equilibrium(CM,voltage).add_packet(ulp/16.0).unwrap();
    let mut original=state(&[],500_000);
    {let gate=&mut Arc::make_mut(&mut original.gates)[0];gate.y=0.0;gate.q=original_charge;}
    let bytes=original.encode(1<<26,source_bounds()).unwrap();
    let cold=Functional64Material::decode(&bytes,1<<26,source_bounds()).unwrap();
    assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),bytes);
    assert_eq!(cold.gates[0].q,original_charge);assert_eq!(cold.gates[0].y.to_bits(),0.0f64.to_bits());
    let live=step(original_charge,CM,voltage,0.001);
    let restored=step(cold.gates[0].q,CM,voltage,0.001);
    assert_eq!(live.0,restored.0);
    assert_eq!([live.1,live.2,live.3].map(f64::to_bits),[restored.1,restored.2,restored.3].map(f64::to_bits));
    assert_eq!(original.encode(1<<26,source_bounds()).unwrap(),bytes);
}

// Exact arithmetic equivalence only. The finite coordinates/override rows are
// disclosed operator fixtures, not manufactured organism behavior or learning.
#[test]
fn cross_column_contact_moments_enclose_exact_edge_law_and_cold_inputs(){
    // Independent test-only signed dyadics. Every finite factor is decoded
    // exactly; products and alignment refuse width overflow, never truncate.
    #[derive(Clone,Copy)]
    struct Dyad{negative:bool,magnitude:Uint1152,exponent:i32}
    impl Dyad{
        fn zero()->Self{Self{negative:false,magnitude:Uint1152::ZERO,exponent:0}}
        fn point(x:f64)->Self{
            assert!(x.is_finite());let bits=x.to_bits();let e=((bits>>52)&2047)as i32;
            let m=(bits&((1u64<<52)-1))|if e==0{0}else{1u64<<52};
            if m==0{return Self::zero();}
            Self{negative:bits>>63!=0,magnitude:Uint1152::from_u64(m),exponent:if e==0{-1074}else{e-1075}}
        }
        fn neg(mut self)->Self{if !self.magnitude.is_zero(){self.negative=!self.negative;}self}
        fn abs(mut self)->Self{self.negative=false;self}
        fn mul_float(self,x:f64)->Self{
            let b=Self::point(x);if self.magnitude.is_zero()||b.magnitude.is_zero(){return Self::zero();}
            assert!(b.magnitude.limbs[1..].iter().all(|&v|v==0));
            let mut magnitude=Uint1152::ZERO;let mut carry=0u128;
            for i in 0..18{let v=self.magnitude.limbs[i]as u128*b.magnitude.limbs[0]as u128+carry;
                magnitude.limbs[i]=v as u64;carry=v>>64;}
            assert_eq!(carry,0,"test dyadic product width");
            Self{negative:self.negative!=b.negative,magnitude,exponent:self.exponent.checked_add(b.exponent).unwrap()}
        }
        fn product(factors:&[f64])->Self{factors.iter().fold(Self::point(1.0),|p,&x|p.mul_float(x))}
        fn add(self,b:Self)->Self{
            if self.magnitude.is_zero(){return b;}if b.magnitude.is_zero(){return self;}
            let exponent=self.exponent.min(b.exponent);
            let a=self.magnitude.shl(usize::try_from(self.exponent.checked_sub(exponent).unwrap()).unwrap()).expect("test dyadic alignment width");
            let bmag=b.magnitude.shl(usize::try_from(b.exponent.checked_sub(exponent).unwrap()).unwrap()).expect("test dyadic alignment width");
            let(magnitude,negative)=if self.negative==b.negative{
                let mut sum=Uint1152::ZERO;let mut carry=0u128;
                for i in 0..18{let value=a.limbs[i]as u128+bmag.limbs[i]as u128+carry;sum.limbs[i]=value as u64;carry=value>>64;}
                assert_eq!(carry,0,"test dyadic sum width");(sum,self.negative)
            }else if a.gte(&bmag){(a.sub(&bmag).unwrap(),self.negative)}else{(bmag.sub(&a).unwrap(),b.negative)};
            if magnitude.is_zero(){Self::zero()}else{Self{negative,magnitude,exponent}}
        }
        fn le(self,b:Self)->bool{let d=b.add(self.neg());!d.negative}
    }
    fn evidence(real:Dyad,value:f64,bound:Interval){
        assert!(Dyad::point(bound.lo).le(real)&&real.le(Dyad::point(bound.hi)),"exact edge sum outside range");
        let error=contact_operator::error(value,bound).unwrap();
        assert!(real.add(Dyad::point(value).neg()).abs().le(Dyad::point(error)),"selected force/energy discrepancy understated");
    }
    fn point(s:&Functional64Material,f:&Frontier,v:&LocalVector,node:usize)->PhasePair{
        if f.index[node]==usize::MAX{*s.phases.get(node)}else{v.nodes[f.index[node]]}
    }
    fn exact_energy(s:&Functional64Material,f:&Frontier,v:&LocalVector)->Dyad{
        let mut total=Dyad::zero();
        for &to in &f.nodes{
            s.anatomy.geometry.visit_incoming(to,|edge|{
                let send=point(s,f,v,edge.from as usize).send.sin();let receive=point(s,f,v,to).receive.sin();
                let gain=s.anatomy.geometry.baseline(edge)+*s.weights.get(edge.authentic_slot as usize);
                let half_lambda=0.5*(LAMBDA/s.anatomy.geometry.degree(to)as f64);
                // Full positive-square identity, evaluated as exact dyadics;
                // no rounded residual, Moment, tree, or predecessor operator.
                total=total.add(Dyad::product(&[half_lambda,receive,receive]))
                    .add(Dyad::product(&[-2.0,half_lambda,gain,receive,send]))
                    .add(Dyad::product(&[half_lambda,gain,gain,send,send]));Ok(())
            }).unwrap();
        }assert!(!total.negative);total
    }
    fn check(s:&Functional64Material)->Vec<u64>{
        let limit=admission();let mut frontier_work=WorkCount::default();
        let f=Frontier::new(s,&vec![0.0;INPUTS],&mut frontier_work,limit).unwrap();
        let a=f.view(s).unwrap();let mut b=a.clone();
        for(index,phase)in b.nodes.iter_mut().enumerate(){
            phase.send+=((index%7)as f64-3.0)/10000.0;
            phase.receive+=((index%5)as f64-2.0)/10000.0;
        }
        let actual=contact_operator::forces(s,&f,&a,&b,&mut WorkCount::default(),limit).unwrap();
        let mut real=vec![[Dyad::zero();2];f.nodes.len()];
        for(index,&to)in f.nodes.iter().enumerate(){
            s.anatomy.geometry.visit_incoming(to,|edge|{
                let from=edge.from as usize;let p=point(s,&f,&a,from);let q=point(s,&f,&b,from);
                let r=point(s,&f,&a,to);let t=point(s,&f,&b,to);
                let v=0.5*(p.send.sin()+q.send.sin());let u=0.5*(r.receive.sin()+t.receive.sin());
                let ds=dsin(p.send,q.send);let dr=dsin(r.receive,t.receive);
                let gain=s.anatomy.geometry.baseline(edge)+*s.weights.get(edge.authentic_slot as usize);
                let lambda=LAMBDA/s.anatomy.geometry.degree(to)as f64;
                let receive=Dyad::product(&[lambda,u,dr]).add(Dyad::product(&[-lambda,gain,v,dr]));
                let send=Dyad::product(&[-lambda,gain,u,ds]).add(Dyad::product(&[lambda,gain,gain,v,ds]));
                real[index][1]=real[index][1].add(receive);
                if f.index[from]==usize::MAX{assert!(send.magnitude.is_zero(),"nonzero edge outside frontier");}
                else{real[f.index[from]][0]=real[f.index[from]][0].add(send);}Ok(())
            }).unwrap();
        }
        assert_eq!(actual.nodes.len(),real.len());assert_eq!(actual.ranges.len(),real.len());
        let mut bits=Vec::new();
        for(index,p)in actual.nodes.iter().enumerate(){for(role,value)in [p.send,p.receive].into_iter().enumerate(){
            let bound=actual.ranges[index][role];evidence(real[index][role],value,bound);
            bits.extend([value.to_bits(),bound.lo.to_bits(),bound.hi.to_bits()]);
        }}
        for v in [&a,&b]{
            let actual=contact_operator::energy(s,&f,v,&[],&mut WorkCount::default(),limit).unwrap();
            assert!(actual.value>=0.0);evidence(exact_energy(s,&f,v),actual.value,actual.range);
            bits.extend([actual.value,actual.range.lo,actual.range.hi].map(f64::to_bits));
        }
        // Same existing ordinary post-return path: new sparse override was
        // absent from the predecessor frontier and must be included once.
        let edge=s.anatomy.geometry.between(35,3*320+41).unwrap();
        assert_eq!(*s.weights.get(edge.authentic_slot as usize),0.0);
        assert!(f.edges.binary_search_by_key(&edge.authentic_slot,|row|row.contact.authentic_slot).is_err());
        let changes=[(edge.authentic_slot as usize,0.0625)];let mut next=s.clone();
        next.change_weights(&changes,&mut WorkCount::default(),limit).unwrap();
        let actual=contact_operator::energy(&next,&f,&b,&changes,&mut WorkCount::default(),limit).unwrap();
        assert!(actual.value>=0.0);evidence(exact_energy(&next,&f,&b),actual.value,actual.range);
        bits.extend([actual.value,actual.range.lo,actual.range.hi].map(f64::to_bits));bits
    }
    let mut an=Arc::try_unwrap(anatomy()).unwrap();let mut severed=vec![true;4096];
    // Nonconsecutive, asymmetric actual column links exercise both adjacency
    // directions and reuse of one immutable source across several recipients.
    for(from,to)in [(0,1),(0,3),(0,5),(1,0),(3,0),(3,1),(5,3)]{severed[from*64+to]=false;}
    an.geometry=Geometry::new(severed.into(),[1.0;64],1.0).unwrap();
    let mut weights=std::collections::BTreeMap::new();
    weights.insert(0u32,-0.0);weights.insert((RAW_SLOTS-1)as u32,-2.0);
    for(from,to,w)in [
        (32,320+32,-g0()),(39,320+43,-0.125),(32,320+128,0.25),
        (320+159,143,-0.0625),(224,320+232,0.3),(287,320+281,-g0()),
        (3*320+48,320+112,-0.0),(5*320+240,3*320+240,0.125),
    ]{weights.insert(an.geometry.between(from,to).unwrap().authentic_slot,w);}
    let rows=weights.into_iter().collect::<Vec<_>>();
    let mut s=Functional64Material::commission(Arc::new(an),at_ms(0),&rows,0).unwrap();
    let values=[-0.0,0.0,-0.125,0.0625,0.25];
    for column in [0,1,3,5]{for local in 0..320{
        let node=column*320+local;let phase=PhasePair{send:values[node%5],receive:values[(node+2)%5]};
        s.phases.set(node,phase).unwrap();
        if phase.send!=0.0||phase.receive!=0.0{Arc::make_mut(&mut s.nonzero_nodes).insert(node as u16);}
    }}
    assert!(s.anatomy.geometry.fasciculated(0,5));assert!(!s.anatomy.geometry.fasciculated(5,0));
    assert!(!s.anatomy.geometry.fasciculated(0,2));
    let before=s.encode(1<<26,source_bounds()).unwrap();let warm=check(&s);
    assert_eq!(s.encode(1<<26,source_bounds()).unwrap(),before);
    let cold=Functional64Material::decode(&before,1<<26,source_bounds()).unwrap();
    assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),before);
    for(slot,value)in rows{assert_eq!(cold.weights.get(slot as usize).to_bits(),value.to_bits());}
    assert_eq!(check(&cold),warm);assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),before);
}

// Independent closed-form references for dq/dt=G(V-q/C), C linear in time.
// Generated by reference_values.py at 150 and190 decimal digits from exact
// finite operand ratios; both precisions round to the same f64 expected bits.
// The first row is actual captured port537. Other rows are labeled component
// regimes; none reconstructs a body, learned state or behavioral experience.
#[test]
fn linear_capacitance_current_heat_and_gate_reaction_match_independent_law(){
    struct Fixture{name:&'static str,q0:[u64;18],c0:u64,c1:u64,voltage:u64,h:u64,split:bool,expected:[f64;3]}
    fn within(actual:f64,expected:f64,label:&str){
        assert!(actual.is_finite()&&expected.is_finite(),"{label}: nonfinite evidence");
        let scale=actual.abs().max(expected.abs());
        if scale==0.0{assert_eq!(actual,expected,"{label}");}
        else{assert!((actual-expected).abs()/scale<=RTOL,
            "{label}: actual={actual:e}, expected={expected:e}, relative_error={:e}, RTOL={RTOL:e}",
            (actual-expected).abs()/scale);}
    }
    fn run(q:Charge,c0:f64,c1:f64,v:f64,h:f64)->InputPathStep{
        input_path_step(q,c0,c1,v,h,&mut WorkCount::default(),admission()).unwrap()
    }
    fn bits(p:&InputPathStep)->[u64;5]{[
        p.dq,p.resistor_heat,p.cap_reaction,p.tail_charge_c,p.tail_work_j,
    ].map(f64::to_bits)}
    assert_eq!(CM.to_bits(),4443823839625945783);assert_eq!(CR.to_bits(),4427486594234968593);assert_eq!(G.to_bits(),4490332669453059439);
    let cases=[
        Fixture{name:"captured_port537",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,18318549092449386496,663761049713665210,0,0],c0:4443885736727688142,c1:4443885736727796859,voltage:4523068004479520666,h:4557750909289998844,split:false,
            expected:[4.5635411826311975e-28,2.651707464290121e-44,-3.1830988616912978e-24]},
        Fixture{name:"opening_capacity_limits",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,13283339507582107648,658520700054560468,0,0],c0:4443823839625945783,c1:4444442809645588473,voltage:4523068004479520666,h:4562254508917369340,split:true,
            expected:[1.044426220386425e-18,8.44864335915111e-26,-3.0180244659738247e-24]},
        Fixture{name:"closing_capacity_limits",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,17711457012608925696,710924112325569770,0,0],c0:4444442809645588473,c1:4443823839625945783,voltage:4523068004479520666,h:4562254508917369340,split:true,
            expected:[-1.0664267078550376e-18,8.972214041814402e-26,-3.357252374453432e-24]},
        Fixture{name:"source_removed_opening",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,13283339507582107648,658520700054560468,0,0],c0:4443823839625945783,c1:4444442809645588473,voltage:0,h:4562254508917369340,split:true,
            expected:[-2.218303804976093e-17,3.552638742588547e-23,-1.1308400338054857e-24]},
        Fixture{name:"source_removed_closing",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,17711457012608925696,710924112325569770,0,0],c0:4444442809645588473,c1:4443823839625945783,voltage:0,h:4562254508917369340,split:true,
            expected:[-2.3948308128968453e-17,4.02585789421702e-23,-1.2814703681003348e-24]},
        Fixture{name:"held_exact_equilibrium",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,13283339507582107648,658520700054560468,0,0],c0:4443823839625945783,c1:4443823839625945783,voltage:4523068004479520666,h:4562254508917369340,split:true,
            expected:[0.0,0.0,-3.183098861837904e-24]},
        Fixture{name:"held_surplus",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,13283339507582107648,658520700054560596,0,0],c0:4443823839625945783,c1:4443823839625945783,voltage:4523068004479520666,h:4562254508917369340,split:true,
            expected:[-4.397253686091563e-33,1.3872142320005017e-54,-3.1830988618379047e-24]},
        Fixture{name:"near_rate_minus_g",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,17711457012608925696,710924112325569770,0,0],c0:4444442809645588473,c1:4443823839625945783,voltage:4523068004479520666,h:4544325849194711170,split:true,
            expected:[-9.536516957586374e-20,1.220398190102165e-26,-3.429819813613244e-24]},
        Fixture{name:"near_rate_minus_2g",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,17711457012608925696,710924112325569770,0,0],c0:4444442809645588473,c1:4443823839625945783,voltage:4523068004479520666,h:4539822249567340674,split:true,
            expected:[-4.829299828411884e-20,6.2796795307154166e-27,-3.433077810481667e-24]},
        Fixture{name:"uncharged_moving",q0:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],c0:4443823839625945783,c1:4444442809645588473,voltage:0,h:4562254508917369340,split:true,
            expected:[0.0,0.0,-0.0]},
    ];
    for case in &cases{
        let q0=Charge{negative:false,magnitude:crate::mathloom::Uint1152{limbs:case.q0}};
        q0.validate().unwrap();
        let c0=f64::from_bits(case.c0);let c1=f64::from_bits(case.c1);
        let v=f64::from_bits(case.voltage);let h=f64::from_bits(case.h);
        let whole=run(q0,c0,c1,v,h);
        for(actual,expected)in [whole.dq,whole.resistor_heat,whole.cap_reaction].into_iter().zip(case.expected){
            within(actual,expected,case.name);
        }
        assert!(whole.resistor_heat>=0.0&&whole.cap_reaction<=0.0);
        assert!(whole.tail_charge_c.is_finite()&&whole.tail_charge_c>=0.0);
        assert!(whole.tail_work_j.is_finite()&&whole.tail_work_j>=0.0);
        let q1=q0.add_packet(whole.dq).unwrap();assert!(!q1.negative);
        assert_eq!(q1.add(q0.neg()).unwrap(),Charge::packet(whole.dq).unwrap());
        // Stable capacitor-energy difference, avoiding subtraction of two
        // almost equal total stored energies. Gy*dy is the actual path work.
        let q=q0.projection().unwrap();
        let delta_u=whole.dq*(2.0*q+whole.dq)/(2.0*c1)-q*q*(c1-c0)/(2.0*c0*c1);
        let source=v*whole.dq;let mechanical=whole.cap_reaction*((c1-c0)/CR);
        let residual=delta_u-source+whole.resistor_heat-mechanical;
        let energy_scale=delta_u.abs()+source.abs()+whole.resistor_heat+mechanical.abs();
        if energy_scale==0.0{assert_eq!(residual,0.0);}
        else{assert!(residual.abs()/energy_scale<=RTOL,"{}: capacitor work identity",case.name);}
        if case.split{
            // The fixture generator proved this midpoint is EXACTLY
            // representable. Both halves follow this same linear C path.
            let middle=0.5*(c0+c1);
            let first=run(q0,c0,middle,v,h/2.0);
            let half_q=q0.add_packet(first.dq).unwrap();
            let second=run(half_q,middle,c1,v,h/2.0);
            let packet=Charge::packet(first.dq).unwrap().add_packet(second.dq).unwrap();
            let split_q=half_q.add_packet(second.dq).unwrap();
            assert_eq!(split_q.add(q0.neg()).unwrap(),packet);
            within(packet.projection().unwrap(),whole.dq,"same-path split charge");
            within(first.resistor_heat+second.resistor_heat,whole.resistor_heat,"same-path split resistor heat");
            within(0.5*(first.cap_reaction+second.cap_reaction),whole.cap_reaction,"same-path split gate reaction");
        }
    }
    // Actual captured charge/y only, inside a disclosed codec fixture. Its
    // unrelated neutral coordinates are not represented as captured history.
    let captured=&cases[0];let q0=Charge{negative:false,magnitude:crate::mathloom::Uint1152{limbs:captured.q0}};
    let y0=f64::from_bits(4591870191682656188);let y1=f64::from_bits(4591870191695312461);
    assert_eq!((CM+CR*y0).to_bits(),captured.c0);assert_eq!((CM+CR*y1).to_bits(),captured.c1);
    let mut original=state(&[],500_000);
    {let gate=&mut Arc::make_mut(&mut original.gates)[537];gate.y=y0;gate.q=q0;}
    let encoded=original.encode(1<<26,source_bounds()).unwrap();
    let cold=Functional64Material::decode(&encoded,1<<26,source_bounds()).unwrap();
    assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),encoded);
    assert_eq!(cold.gates[537].q,q0);assert_eq!(cold.gates[537].y.to_bits(),y0.to_bits());
    let c0=f64::from_bits(captured.c0);let c1=f64::from_bits(captured.c1);
    let v=f64::from_bits(captured.voltage);let h=f64::from_bits(captured.h);
    let live=run(q0,c0,c1,v,h);let restored=run(cold.gates[537].q,c0,c1,v,h);
    assert_eq!(bits(&live),bits(&restored));
    assert_eq!(q0.add_packet(live.dq).unwrap(),cold.gates[537].q.add_packet(restored.dq).unwrap());
    assert_eq!(original.encode(1<<26,source_bounds()).unwrap(),encoded);
}

// Same actual port537 operands captured in Build16, now referenced to exact
// C(y)=CM+CR*y before any endpoint rounding. These are three INDEPENDENT paths:
// the third begins at its actual captured old charge, not a newly generated
// first-half successor. Reference derivation is in exact-affine reference0ef2.
#[test]
fn captured_affine_gate_paths_match_independent_charge_heat_and_reaction(){
    struct Fixture{name:&'static str,q:[u64;18],y0:u64,y1:u64,voltage:u64,h:u64,expected:[f64;3]}
    fn within(actual:f64,expected:f64,label:&str){
        assert!(actual.is_finite()&&expected.is_finite(),"{label}: nonfinite evidence");
        let scale=actual.abs().max(expected.abs());
        if scale==0.0{assert_eq!(actual,expected,"{label}");}
        else{assert!((actual-expected).abs()/scale<=RTOL,
            "{label}: actual={actual:e}, expected={expected:e}, relative_error={:e}, RTOL={RTOL:e}",
            (actual-expected).abs()/scale);}
    }
    fn run(q:Charge,y0:f64,y1:f64,v:f64,h:f64)->InputPathStep{
        input_gate_path_step(q,y0,y1,v,h,&mut WorkCount::default(),admission()).unwrap()
    }
    fn bits(path:&InputPathStep)->[u64;5]{[
        path.dq,path.resistor_heat,path.cap_reaction,path.tail_charge_c,path.tail_work_j,
    ].map(f64::to_bits)}
    let cases=[
        Fixture{name:"coarse",q:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,18318549092449386496,663761049713665210,0,0],y0:4591870191682656188,y1:4591870191695312461,voltage:4523068004479520666,h:4557750909289998844,
            expected:[4.563538077682944e-28,2.651703872018669e-44,-3.183098861691298e-24]},
        Fixture{name:"first_half",q:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,18318549092449386496,663761049713665210,0,0],y0:4591870191682656188,y1:4591870191688986293,voltage:4523068004479520666,h:4553247309662628348,
            expected:[2.2920064206494454e-28,1.3377517925577368e-44,-3.1830988616906403e-24]},
        Fixture{name:"second_half_actual_predecessor",q:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,4483228219528445952,663761049718393874,0,0],y0:4591870191688986293,y1:4591870191695312460,voltage:4523068004479520666,h:4553247309662628348,
            expected:[2.275751670552163e-28,1.3188406310319366e-44,-3.1830988616916846e-24]},
    ];
    for case in &cases{
        let q=Charge{negative:false,magnitude:crate::mathloom::Uint1152{limbs:case.q}};q.validate().unwrap();
        let actual=run(q,f64::from_bits(case.y0),f64::from_bits(case.y1),f64::from_bits(case.voltage),f64::from_bits(case.h));
        for(value,expected)in [actual.dq,actual.resistor_heat,actual.cap_reaction].into_iter().zip(case.expected){within(value,expected,case.name);}
        assert!(actual.resistor_heat>=0.0&&actual.cap_reaction<=0.0);
        assert!(actual.tail_charge_c.is_finite()&&actual.tail_charge_c>=0.0);
        assert!(actual.tail_work_j.is_finite()&&actual.tail_work_j>=0.0);
        let successor=q.add_packet(actual.dq).unwrap();assert!(!successor.negative);
        assert_eq!(successor.add(q.neg()).unwrap(),Charge::packet(actual.dq).unwrap());
    }
    // Ordinary current codec, preserving actual captured charge and aperture.
    // The fixture's other coordinates are explicitly new and are not claimed
    // to reconstruct the captured organism or any prior learned history.
    let case=&cases[0];let q=Charge{negative:false,magnitude:crate::mathloom::Uint1152{limbs:case.q}};
    let y0=f64::from_bits(case.y0);let y1=f64::from_bits(case.y1);
    let v=f64::from_bits(case.voltage);let h=f64::from_bits(case.h);
    let mut original=state(&[],500_000);
    {let gate=&mut Arc::make_mut(&mut original.gates)[537];gate.q=q;gate.y=y0;}
    let encoded=original.encode(1<<26,source_bounds()).unwrap();
    let cold=Functional64Material::decode(&encoded,1<<26,source_bounds()).unwrap();
    assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),encoded);
    assert_eq!(cold.gates[537].q,q);assert_eq!(cold.gates[537].y.to_bits(),case.y0);
    let live=run(q,y0,y1,v,h);let restored=run(cold.gates[537].q,cold.gates[537].y,y1,v,h);
    assert_eq!(bits(&live),bits(&restored));
    assert_eq!(q.add_packet(live.dq).unwrap(),cold.gates[537].q.add_packet(restored.dq).unwrap());
    assert_eq!(original.encode(1<<26,source_bounds()).unwrap(),encoded);
}

// Exact product equation only. The adjacent negative-residual aperture is an
// arithmetic fixture, never a sensory/body driver or a learning observation.
#[test]
fn affine_equilibrium_retains_positive_negative_and_zero_product_residuals(){
    let voltage=f64::from_bits(4523068004479520666);
    let cases=[
        (4591870191682656188, 1, 4443885736727688142, [0,0,0,0,0,0,0,0,0,0,0,0,0,12382912116082868224,2109676359665505029,663761049729101863,0,0]),
        (4591870191682656186, -1, 4443885736727688142, [0,0,0,0,0,0,0,0,0,0,0,0,0,7018912147576979456,12172617424327840096,663761049729101861,0,0]),
        (4602678819172646912, 0, 4444133324635767128, [0,0,0,0,0,0,0,0,0,0,0,0,0,0,2425895487583715328,684722406190065125,0,0]),
    ];
    for(y_bits,residual_sign,denominator_bits,expected_limbs)in cases{
        let y=f64::from_bits(y_bits);let product=CR*y;let residual=CR.mul_add(y,-product);
        let observed_sign=if residual>0.0{1}else if residual<0.0{-1}else{0};
        assert_eq!(observed_sign,residual_sign);
        let(denominator,actual)=input_affine_equilibrium(y,voltage,&mut WorkCount::default(),admission()).unwrap();
        assert_eq!(denominator.to_bits(),denominator_bits);
        let expected=Charge{negative:false,magnitude:crate::mathloom::Uint1152{limbs:expected_limbs}};
        assert_eq!(actual,expected,"exact (CM+CR*y)*V at aperture bits {y_bits}");
        let held=input_gate_path_step(expected,y,y,voltage,0.001,&mut WorkCount::default(),admission()).unwrap();
        assert_eq!(held.dq,0.0);assert_eq!(held.resistor_heat,0.0);
        assert_eq!(expected.add_packet(held.dq).unwrap(),expected);
    }
}


// The SI denominator and the exact binary64 RTOL define these integer
// boundaries. This is arithmetic custody evidence, not a physical stimulus.
#[test]
fn exact_carrier_error_uses_signed_numerators_and_preserves_cold_boundaries(){
    assert_eq!(RTOL.to_bits(),4517329193108106637);
    // RTOL=4722366482869645/2^72; D=801088317*2^1048.
    // Their product is an integer, independently calculated before this test.
    let threshold=Uint1152{limbs:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,7110692112514482176,13440031729,0]};
    let unit=Uint1152::from_u64(1);
    let less=threshold.sub(&unit).unwrap();
    let greater=Charge{negative:false,magnitude:threshold}.add(Charge{negative:false,magnitude:unit}).unwrap().magnitude;
    let half=threshold.shr(1);
    let half_plus=Charge{negative:false,magnitude:half}.add(Charge{negative:false,magnitude:unit}).unwrap().magnitude;
    let r=|magnitude,negative|Remainder{magnitude,negative};
    let zero=Remainder::ZERO;
    assert!(zero.within_one_carrier_error(&zero,0.0).unwrap());
    assert!(!zero.within_one_carrier_error(&r(unit,false),0.0).unwrap());
    for negative in [false,true]{
        for(magnitude,expected)in [(less,true),(threshold,true),(greater,false)]{
            let value=r(magnitude,negative);
            assert_eq!(zero.within_one_carrier_error(&value,RTOL).unwrap(),expected);
            assert_eq!(value.within_one_carrier_error(&zero,RTOL).unwrap(),expected);
            let mut bytes=Vec::new();value.encode(&mut bytes);assert_eq!(bytes.len(),145);
            let cold=Remainder::decode(&bytes).unwrap();assert_eq!(cold,value);
            assert_eq!(zero.within_one_carrier_error(&cold,RTOL).unwrap(),expected);
            let mut restored=Vec::new();cold.encode(&mut restored);assert_eq!(restored,bytes);
        }
        let a=r(half,negative);let b=r(half,!negative);let outside=r(half_plus,!negative);
        assert!(a.within_one_carrier_error(&b,RTOL).unwrap());
        assert!(!a.within_one_carrier_error(&outside,RTOL).unwrap());
        assert!(a.within_one_carrier_error(&a,0.0).unwrap());
    }
    assert!(zero.within_one_carrier_error(&r(Uint1152::ZERO,true),RTOL).is_err());
    let mut denominator=[0u64;18];denominator[16]=13440031729385472;
    assert!(zero.within_one_carrier_error(&r(Uint1152{limbs:denominator},false),RTOL).is_err());
    for invalid in [-1.0,f64::NAN,f64::INFINITY,2.0]{
        assert!(zero.within_one_carrier_error(&zero,invalid).is_err());
    }
}

// Actual ordinary optical source -> coarse and two-half TrialSteps. Only the
// comparison inputs below are altered to falsify admission; none is published
// or presented as organism experience, learned output or an accepted trajectory.
#[test]
fn adaptive_comparison_uses_physical_successor_and_discrete_custody(){
    fn copy(t:&TrialStep)->TrialStep{TrialStep{state:t.state.clone(),emitted:t.emitted,
        evidence:t.evidence,supplied:t.supplied,transducer_heat:t.transducer_heat}}
    fn refused(a:&TrialStep,b:&TrialStep){
        let comparison=adaptive_comparison(a,b).unwrap();
        assert!(!comparison.accepted());assert!(comparison.causal_mismatch.is_some());
    }
    let mut s=state(&[(0,-0.0),((RAW_SLOTS-1)as u32,-2.0)],0);
    let packet=optical(0);let release_ms=packet_release_ms(&packet).unwrap();
    let source_voltage=packet_source_voltage(&packet,release_ms).unwrap();
    s.last_power[0]=Some(packet.release_end);
    s.power.push(PendingPower{remaining:Work::finite_joules(packet.admitted_j).unwrap(),packet,source_voltage,release_ms});
    let before=s.encode(1<<26,source_bounds()).unwrap();
    let drive=s.physical_drives(false).unwrap();let limit=admission();let span=work_store::FULL_TICKS;
    let mut count=WorkCount::default();
    let(coarse,first)={let mut start=CommonStart::new(&s,&drive,&mut count,limit).unwrap();
        (start.trial(span,&mut count,limit).unwrap(),start.trial(span/2,&mut count,limit).unwrap())};
    let second=first.state.trial(span-span/2,&drive,&mut count,limit).unwrap();
    let fine=combine_steps(first,second).unwrap();
    let coarse_bytes=coarse.state.encode(1<<26,source_bounds()).unwrap();
    let fine_bytes=fine.state.encode(1<<26,source_bounds()).unwrap();
    assert!(!fine.state.gates[0].q.magnitude.is_zero());
    for step in [&coarse,&fine]{
        assert!(step.evidence.contact_heat_j>=0.0&&step.evidence.plastic_heat_j>=0.0);
        assert!(step.evidence.energy_residual_j.is_finite());
        assert_eq!(step.state.weights.get(0).to_bits(),(-0.0f64).to_bits());
        assert_eq!(step.state.weights.get(RAW_SLOTS-1).to_bits(),(-2.0f64).to_bits());
    }
    let original=adaptive_comparison(&coarse,&fine).unwrap();
    // This test does not assume the measured pair already converges. Whatever
    // the physical decision is, an observation-only change cannot change it.
    for lane in 0..4{
        let mut observed=copy(&fine);
        let value=match lane{0=>&mut observed.evidence.supply_j,1=>&mut observed.evidence.exported_j,
            2=>&mut observed.evidence.contact_heat_j,_=>&mut observed.evidence.plastic_heat_j};
        let old_bits=value.to_bits();*value=if *value==0.0{f64::MIN_POSITIVE}else{*value*2.0};
        assert_ne!(value.to_bits(),old_bits);
        let comparison=adaptive_comparison(&coarse,&observed).unwrap();
        assert_eq!(comparison.state_error.to_bits(),original.state_error.to_bits());
        assert_eq!(comparison.causal_mismatch,original.causal_mismatch);
        assert_eq!(comparison.accepted(),original.accepted());
        assert_eq!(observed.state.encode(1<<26,source_bounds()).unwrap(),fine_bytes);
        assert_eq!(observed.emitted,fine.emitted);
    }
    assert!(adaptive_comparison(&fine,&copy(&fine)).unwrap().accepted());
    let mut carrier=copy(&fine);carrier.emitted[96]=carrier.emitted[96].checked_add(1).unwrap();refused(&fine,&carrier);
    let mut flags=copy(&fine);let old=*flags.state.contact_changes.get(2);
    flags.state.contact_changes.set(2,!old).unwrap();refused(&fine,&flags);
    let mut support=copy(&fine);assert_eq!(*support.state.weights.get(2),0.0);
    support.state.weights.set(2,f64::from_bits(1)).unwrap();refused(&fine,&support);
    // Both raw weights remain nonzero and differ by far less than RTOL, but
    // the selected effective bridge changes from exactly absent to present.
    let edge=fine.state.anatomy.geometry.between(160,32).unwrap();
    let baseline=fine.state.anatomy.geometry.baseline(edge);assert_eq!(baseline,0.5);
    let mut canceled=copy(&fine);let mut surviving=copy(&fine);
    canceled.state.weights.set(edge.authentic_slot as usize,-baseline).unwrap();
    surviving.state.weights.set(edge.authentic_slot as usize,f64::from_bits((-baseline).to_bits()-1)).unwrap();
    assert_eq!(baseline+*canceled.state.weights.get(edge.authentic_slot as usize),0.0);
    assert_ne!(baseline+*surviving.state.weights.get(edge.authentic_slot as usize),0.0);
    refused(&canceled,&surviving);
    assert_eq!(fine.state.gates[INPUTS].load,Remainder::ZERO);
    let mut fractional=copy(&fine);
    let threshold=Uint1152{limbs:[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,7110692112514482176,13440031729,0]};
    Arc::make_mut(&mut fractional.state.gates)[INPUTS].load=Remainder{negative:false,magnitude:threshold};
    assert!(adaptive_comparison(&fine,&fractional).unwrap().accepted());
    let greater=Charge{negative:false,magnitude:threshold}.add(Charge{negative:false,magnitude:Uint1152::from_u64(1)}).unwrap().magnitude;
    Arc::make_mut(&mut fractional.state.gates)[INPUTS].load=Remainder{negative:false,magnitude:greater};refused(&fine,&fractional);
    let quantum=Work{limbs:{let mut limbs=[0u64;19];limbs[0]=1;limbs}};
    let mut supplied=copy(&fine);supplied.supplied=supplied.supplied.add(quantum).unwrap();
    assert!(adaptive_comparison(&fine,&supplied).is_err());
    let mut reserve=copy(&fine);reserve.state.reserve_ug+=1;assert!(adaptive_comparison(&fine,&reserve).is_err());
    let mut work=copy(&fine);work.state.work=work.state.work.add(quantum).unwrap();assert!(adaptive_comparison(&fine,&work).is_err());
    let mut scheduled=copy(&fine);assert_eq!(scheduled.state.power.len(),1);
    scheduled.state.power[0].remaining=scheduled.state.power[0].remaining.add(quantum).unwrap();
    assert!(adaptive_comparison(&fine,&scheduled).is_err());
    assert_eq!(coarse.state.encode(1<<26,source_bounds()).unwrap(),coarse_bytes);
    assert_eq!(fine.state.encode(1<<26,source_bounds()).unwrap(),fine_bytes);
    assert_eq!(s.encode(1<<26,source_bounds()).unwrap(),before);
}

#[test]
fn adaptive_charge_difference_retains_sub_ulp_custody_through_cold(){
    // Arithmetic-only current fixture: the two exact charges have the same
    // correctly rounded voltage operand but differ by a retained quarter ULP.
    let q=equilibrium_charge(CM,VS).unwrap();let projected=q.projection().unwrap();
    let next=f64::from_bits(projected.to_bits()+1);let packet=(next-projected)/4.0;
    assert!(packet>0.0);
    let mut a=state(&[(0,-0.0),((RAW_SLOTS-1)as u32,-2.0)],0);
    // Start from the exact rounded packet to make the tie location independent
    // of any product residual in the original equilibrium multiplication.
    let start=Charge::packet(projected).unwrap();let end=start.add_packet(packet).unwrap();
    assert_eq!(start.projection().unwrap().to_bits(),end.projection().unwrap().to_bits());
    Arc::make_mut(&mut a.gates)[0].q=start;
    let mut b=a.clone();Arc::make_mut(&mut b.gates)[0].q=end;
    let expected=packet/projected.abs();let difference=a.difference(&b).unwrap();
    assert!(difference>0.0&&difference<RTOL);assert_eq!(difference.to_bits(),expected.to_bits());
    let a_bytes=a.encode(1<<26,source_bounds()).unwrap();let b_bytes=b.encode(1<<26,source_bounds()).unwrap();
    assert_ne!(a_bytes,b_bytes);
    let cold_a=Functional64Material::decode(&a_bytes,1<<26,source_bounds()).unwrap();
    let cold_b=Functional64Material::decode(&b_bytes,1<<26,source_bounds()).unwrap();
    assert_eq!(cold_a.encode(1<<26,source_bounds()).unwrap(),a_bytes);
    assert_eq!(cold_b.encode(1<<26,source_bounds()).unwrap(),b_bytes);
    assert_eq!(cold_a.gates[0].q,start);assert_eq!(cold_b.gates[0].q,end);
    assert_eq!(cold_a.difference(&cold_b).unwrap().to_bits(),difference.to_bits());
}


#[test]
fn derived_phase_index_uses_continuous_error_and_rebuilds_through_cold(){
    // Ordinary current with no pending interval. Comparator-only coordinates,
    // never a supplied action, learned output or published organism experience.
    let quiet=TrialStep{state:state(&[],0),emitted:[0;TERMINALS],
        evidence:WorkEvidence::default(),supplied:Work::ZERO,transducer_heat:Work::ZERO};
    for value in [RTOL/2.0,RTOL*2.0]{
        let mut active=TrialStep{state:quiet.state.clone(),emitted:quiet.emitted,
            evidence:quiet.evidence,supplied:quiet.supplied,transducer_heat:quiet.transducer_heat};
        active.state.phases.set(0,PhasePair{send:value,receive:0.0}).unwrap();
        Arc::make_mut(&mut active.state.nonzero_nodes).insert(0);
        assert!(!quiet.state.nonzero_nodes.contains(&0));
        let comparison=adaptive_comparison(&quiet,&active).unwrap();
        assert_eq!(comparison.state_error.to_bits(),value.to_bits());
        assert_eq!(comparison.causal_mismatch,None);
        assert_eq!(comparison.accepted(),value<=RTOL);
        for original in [&quiet.state,&active.state]{
            let bytes=original.encode(1<<26,source_bounds()).unwrap();
            let cold=Functional64Material::decode(&bytes,1<<26,source_bounds()).unwrap();
            assert_eq!(cold.encode(1<<26,source_bounds()).unwrap(),bytes);
            assert_eq!(cold.phases.get(0).send.to_bits(),original.phases.get(0).send.to_bits());
            assert_eq!(cold.nonzero_nodes,original.nonzero_nodes);
        }
    }
}

#[test]
fn comparison_only_coarse_preserves_physical_successor_and_complete_half_receipt(){
    fn evidence_bits(e:WorkEvidence)->[u64;19]{[
        e.supply_j,e.field_switch_j,e.source_heat_j,e.contact_heat_j,e.phase_heat_j,e.gate_heat_j,
        e.exported_j,e.plastic_heat_j,e.return_map_dissipation_j,e.stop_dissipation_j,e.energy_residual_j,
        e.nonlinear_bound,e.error_estimate,e.circuit_tail_charge_c,e.circuit_tail_work_j,e.circuit_projection_defect_v,
        e.contact_energy_change_j,e.contact_energy_change_lower_j,e.contact_energy_change_upper_j,
    ].map(f64::to_bits)}
    // Same disclosed optical component setup used by the common-start test;
    // no seeded actuator, contact learning, or mature-history claim.
    let mut s=state(&[(0,-0.0),((RAW_SLOTS-1)as u32,-2.0)],0);
    let packet=optical(0);let release_ms=packet_release_ms(&packet).unwrap();
    let source_voltage=packet_source_voltage(&packet,release_ms).unwrap();
    s.last_power[0]=Some(packet.release_end);
    s.power.push(PendingPower{remaining:Work::finite_joules(packet.admitted_j).unwrap(),packet,source_voltage,release_ms});
    let predecessor=s.encode(1<<26,source_bounds()).unwrap();
    let drive=s.physical_drives(false).unwrap();let limit=admission();
    let span=work_store::FULL_TICKS;let half=span/2;
    let mut complete_count=WorkCount::default();
    let(complete,complete_half)={
        let mut start=CommonStart::new(&s,&drive,&mut complete_count,limit).unwrap();
        let coarse=start.trial(span,&mut complete_count,limit).unwrap();
        assert!(start.initial_energy.is_some());
        let first=start.trial(half,&mut complete_count,limit).unwrap();(coarse,first)
    };
    let mut comparison_count=WorkCount::default();
    let(comparison,comparison_half)={
        let mut start=CommonStart::new(&s,&drive,&mut comparison_count,limit).unwrap();
        let coarse=start.comparison_trial(span,&mut comparison_count,limit).unwrap();
        assert!(start.initial_gradient.is_some());assert!(start.initial_energy.is_none());
        let first=start.trial(half,&mut comparison_count,limit).unwrap();
        assert!(start.initial_energy.is_some());(coarse,first)
    };
    // These are internal trial successors with the original parent clock;
    // byte equality is checked directly, without pretending they are cold mounts.
    assert_eq!(complete.state.encode(1<<26,source_bounds()).unwrap(),comparison.state.encode(1<<26,source_bounds()).unwrap());
    assert_eq!(complete.emitted,comparison.emitted);assert_eq!(complete.supplied,comparison.supplied);
    assert_eq!(complete.transducer_heat,comparison.transducer_heat);
    assert_eq!([complete.evidence.supply_j,complete.evidence.exported_j,complete.evidence.contact_heat_j,complete.evidence.plastic_heat_j].map(f64::to_bits),comparison.caloric.map(f64::to_bits));
    assert_eq!(complete_half.state.encode(1<<26,source_bounds()).unwrap(),comparison_half.state.encode(1<<26,source_bounds()).unwrap());
    assert_eq!(complete_half.emitted,comparison_half.emitted);assert_eq!(complete_half.supplied,comparison_half.supplied);
    assert_eq!(complete_half.transducer_heat,comparison_half.transducer_heat);
    assert_eq!(evidence_bits(complete_half.evidence),evidence_bits(comparison_half.evidence));
    assert!(!comparison.state.gates[0].q.magnitude.is_zero());
    assert_eq!(s.encode(1<<26,source_bounds()).unwrap(),predecessor);
    assert!(comparison_count.force_terms<complete_count.force_terms);
    eprintln!("coarse_energy force_terms complete={} comparison={} saved={}",complete_count.force_terms,
        comparison_count.force_terms,complete_count.force_terms-comparison_count.force_terms);
}
