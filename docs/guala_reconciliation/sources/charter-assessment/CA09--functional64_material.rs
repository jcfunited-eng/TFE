//! Source candidate: exact current material custody and explicit new anatomy.
//! Authentic history means the exact supplied bytes and raw contact rows only.
//! Commissioning does not reconstruct voltages or other state absent from those bytes.
use std::collections::{BTreeMap,BTreeSet,VecDeque};
use std::sync::Arc;
use crate::arcloom_neuron as material;
use crate::joint_uf_vector::{ExactTime,SharedJointField,AdmissionBounds,evaluate_joint_source};
use crate::joint_uf_vector::source_codec::{encode_joint_source,decode_joint_source};
use crate::mathloom::{Uint1152,float_to_rational_trits};
#[path="exact_carrier.rs"] mod exact_carrier;
#[path="functional64_geometry.rs"] mod geometry;
#[path="functional64_charge.rs"] mod exact_charge;
#[path="functional64_work.rs"] mod work_store;
#[path="functional64_contact.rs"] mod contact_operator;
#[cfg(test)] #[path="functional64_contact_predecessor.rs"] mod predecessor_contact;
use exact_carrier::Remainder;
use exact_charge::Charge;
use work_store::Work;
pub(crate) use geometry::Geometry;
use geometry::{Contact,RAW_SLOTS,NODES};
const FACTS:usize=9506;
const INPUTS:usize=608;
const TERMINALS:usize=97;
const PAGE:usize=128;
const FAN:usize=256;
const RTOL:f64=1e-6;
const SOLVE_TOL:f64=128.0*f64::EPSILON;
const MAX_ITERATIONS:usize=48;
const MAX_REFINEMENT:usize=12;
const LAMBDA:f64=material::GATE_PHASE_COUPLING_J;
const DRAG:f64=material::PHASE_DRAG_GAMMA_J_S;
const NG:f64=material::CHANNEL_POPULATIONS[3] as f64;
const REST:f64=material::RESTING_APERTURES[3];
const K:f64=NG*material::GATE_STIFFNESS_K_J;
const ZETA:f64=NG*material::GATE_DRAG_ZETA_J_S;
const COUPLING:f64=NG*material::GATE_PHASE_COUPLING_J;
const ALPHA:f64=COUPLING/K;
const CM:f64=material::MEMBRANE_CAPACITANCE_F;
const CR:f64=material::RECEIVING_CAPACITANCE_F;
const G:f64=material::CONTACT_MATERIAL_CONDUCTIVITY_S_PER_M*material::CONTACT_AREA_REF_M2/material::CONTACT_LENGTH_REF_M;
const VS:f64=material::KT_J/material::ELEMENTARY_CHARGE_C;
const MAGIC:&[u8;8]=b"GLF64M01";
const CONSTITUTION:&[u8]=b"functional64:reciprocal-contact-v2;resting-intra-L4[i=j/2]-L23[i=2j]-L5[i=2j]-L6=.5;inter-band-or-residue-g0;positive-moments-excluded-overrides-v1;shunt-v1;work-q-125x2^1127;clock-grid-52;inputs-608;outputs-97;discrete-gradient-v1;positive-held-circuit-v1;input-linear-capacitance-v1;input-affine-capacitance-v1;causal-successor-admission-v2;baseline-cross-column-moments-v1";
// Fixed-size failure evidence for the most recently rejected span in one
// advance call. This is never material state or a retained trial result.
#[derive(Clone,Copy,Debug,PartialEq)]
pub(crate) struct RefinementRejection{
    span_ticks:u64,depth:usize,
    coarse_unresolved_reason:Option<&'static str>,fine_unresolved_reason:Option<&'static str>,
    state_difference:Option<f64>,causal_mismatch:Option<&'static str>,
    // Original comparison order: supply, exported, contact heat, plastic heat;
    // each pair is (coarse, combined fine), without recomputing either value.
    evidence_pairs:Option<[(f64,f64);4]>,total_error:Option<f64>,
    // Predecessor, coarse, combined fine: exact representative membrane
    // charge and whether all97 outputs have that charge, y==REST, qr==0.
    closed_outputs:Option<[(Charge,bool);3]>,
}
#[derive(Clone,Debug,PartialEq)]
pub(crate) enum MaterialError{
    Invalid(&'static str),Capacity(&'static str),Arithmetic(&'static str),
    UnresolvedEvent(&'static str),Source(&'static str),
    ForceCapacity{reason:&'static str,used:u64,requested:u64,limit:u64,file:&'static str,line:u32,
        nonlinear_iteration:Option<usize>,adaptive_stage:Option<&'static str>,trial_span_ticks:Option<u64>,
        refinement_depth:Option<usize>,trial_entry_force_terms:Option<u64>,preceding_refinement:Option<RefinementRejection>},
}
impl MaterialError{
    // Failure-only context; no retained state, extra work counter or success
    // allocation. Span is the actual trial duration on the existing52-bit grid.
    fn force_trial_context(mut self,stage:&'static str,span:u64,depth:usize,entry:u64,last_rejection:Option<RefinementRejection>)->Self{
        if let Self::ForceCapacity{adaptive_stage,trial_span_ticks,refinement_depth,trial_entry_force_terms,preceding_refinement,..}=&mut self{
            *adaptive_stage=Some(stage);*trial_span_ticks=Some(span);
            *refinement_depth=Some(depth);*trial_entry_force_terms=Some(entry);
            *preceding_refinement=last_rejection;
        }self
    }
}
type Result<T>=std::result::Result<T,MaterialError>;
fn finite(x:f64)->Result<f64>{if x.is_finite(){Ok(x)}else{Err(MaterialError::Arithmetic("nonfinite material value"))}}
fn nonnegative(x:f64)->Result<f64>{if x.is_finite()&&x>=0.0{Ok(x)}else{Err(MaterialError::Arithmetic("negative/nonfinite physical quantity"))}}
fn g0()->f64{crate::cortical_column::G_ELASTIC_BASELINE as f64}
fn sinc(x:f64)->f64{if x==0.0{1.0}else{x.sin()/x}}
fn dsin(a:f64,b:f64)->f64{(0.5*(a+b)).cos()*sinc(0.5*(b-a))}
fn aperture(y:f64)->f64{if y<=REST{0.0}else{let z=(y-REST)/(1.0-REST);NG*z/(material::R_P0+material::R_A0*z.sqrt())}}
fn time_le(a:ExactTime,b:ExactTime)->Result<bool>{
    let(an,ad)=a.parts();let(bn,bd)=b.parts();
    let left=(an as i128).checked_mul(bd as i128).ok_or(MaterialError::Arithmetic("physical clock product"))?;
    let right=(bn as i128).checked_mul(ad as i128).ok_or(MaterialError::Arithmetic("physical clock product"))?;
    Ok(left<=right)
}
fn positive_duration(a:ExactTime,b:ExactTime)->Result<(u128,u128)>{
    let(an,ad)=a.parts();let(bn,bd)=b.parts();
    let end=(bn as i128).checked_mul(ad as i128).ok_or(MaterialError::Arithmetic("physical clock product"))?;
    let start=(an as i128).checked_mul(bd as i128).ok_or(MaterialError::Arithmetic("physical clock product"))?;
    let n=end.checked_sub(start).ok_or(MaterialError::Arithmetic("physical clock difference"))?;
    if n<=0{return Err(MaterialError::Invalid("nonpositive physical duration"));}
    Ok((n as u128,(ad as u128)*(bd as u128)))
}
fn elapsed(a:ExactTime,b:ExactTime)->Result<f64>{let(n,d)=positive_duration(a,b)?;finite(n as f64/d as f64)}
fn gcd_u128(mut a:u128,mut b:u128)->u128{while b!=0{let r=a%b;a=b;b=r;}a}
fn ratio_milliseconds(n:u128,d:u128)->Result<u64>{
    if n==0||d==0{return Err(MaterialError::Invalid("nonpositive material duration"));}
    let common=gcd_u128(n,d);let n=n/common;let d=d/common;
    let scale=gcd_u128(d,1000);let divisor=d/scale;
    let scaled=n.checked_mul(1000/scale).ok_or(MaterialError::Arithmetic("millisecond duration product"))?;
    if scaled%divisor!=0{return Err(MaterialError::Invalid("nonintegral material millisecond duration"));}
    u64::try_from(scaled/divisor).map_err(|_|MaterialError::Capacity("material millisecond width"))
}
fn duration_ms(a:ExactTime,b:ExactTime)->Result<u64>{let(n,d)=positive_duration(a,b)?;ratio_milliseconds(n,d)}
fn one_millisecond(a:ExactTime,b:ExactTime)->Result<bool>{Ok(duration_ms(a,b)?==1)}
fn packet_release_ms(packet:&PowerPacket)->Result<u8>{
    let receiver=packet.receiver as usize;
    if receiver>=INPUTS{return Err(MaterialError::Invalid("physical input receiver"));}
    let release_ms=if (480..512).contains(&receiver){10}else{1};
    let origin=if receiver<512{PowerOrigin::MeasuredEnvironmental}else{PowerOrigin::BodyReserve};
    if packet.identity.is_empty()||packet.origin!=origin
        ||!time_le(packet.acquired_start,packet.acquired_end)?
        ||((480..512).contains(&receiver)&&packet.acquired_start==packet.acquired_end)
        ||!time_le(packet.acquired_end,packet.available)?||!time_le(packet.available,packet.release_start)?{
        return Err(MaterialError::Source("physical input origin or acquisition custody"));
    }
    nonnegative(packet.lower_j)?;nonnegative(packet.admitted_j)?;nonnegative(packet.upper_j)?;
    if packet.lower_j>packet.admitted_j||packet.admitted_j>packet.upper_j{
        return Err(MaterialError::Source("physical work enclosure"));
    }
    if duration_ms(packet.release_start,packet.release_end)?!=release_ms as u64{
        return Err(MaterialError::Source("physical receptor release duration"));
    }
    Work::packet_interval(packet.admitted_j,release_ms).map_err(MaterialError::Arithmetic)?;
    Ok(release_ms)
}
fn validate_field_durations(field:&SharedJointField)->Result<Vec<u16>>{
    if field.gates().is_empty()||field.gates().len()>25{return Err(MaterialError::Source("whole-field gate count"));}
    let mut total=0u16;let mut durations=Vec::with_capacity(field.gates().len());
    for g in field.gates(){
        let duration=ratio_milliseconds(g.l1.duration.numerator,g.l1.duration.denominator)?;
        if duration==0||duration>250{return Err(MaterialError::Source("whole-field gate duration"));}
        let duration=duration as u16;
        total=total.checked_add(duration).ok_or(MaterialError::Arithmetic("whole-field duration"))?;
        durations.push(duration);
    }
    if total!=250{return Err(MaterialError::Source("whole-field duration is not one quarter"));}
    Ok(durations)
}

/// Two-level COW pages. Absent pages contain the declared exact zero only.
/// Comparison skips identical branches/leaves; it does not walk old learning.
type Leaf<T> = Arc<Vec<T>>;
type Branch<T> = Arc<Vec<Option<Leaf<T>>>>;
#[derive(Clone,Debug)]
struct Pages<T:Clone>{len:usize,zero:T,root:Arc<Vec<Option<Branch<T>>>>}
impl<T:Clone> Pages<T>{
    fn new(len:usize,zero:T)->Self{Self{len,zero,root:Arc::new(vec![None;(len+PAGE*FAN-1)/(PAGE*FAN)])}}
    fn get(&self,i:usize)->&T{assert!(i<self.len);self.root[i/(PAGE*FAN)].as_ref().and_then(|b|b[(i/PAGE)%FAN].as_ref()).map_or(&self.zero,|p|&p[i%PAGE])}
    fn set(&mut self,i:usize,value:T)->Result<()>{
        if i>=self.len{return Err(MaterialError::Invalid("material address"));}
        let branch=&mut Arc::make_mut(&mut self.root)[i/(PAGE*FAN)];
        if branch.is_none(){*branch=Some(Arc::new(vec![None;FAN]));}
        let leaf=&mut Arc::make_mut(branch.as_mut().unwrap())[(i/PAGE)%FAN];
        if leaf.is_none(){*leaf=Some(Arc::new(vec![self.zero.clone();PAGE]));}
        Arc::make_mut(leaf.as_mut().unwrap())[i%PAGE]=value;Ok(())
    }
    fn allocated(&self)->impl Iterator<Item=(usize,&T)>{
        self.root.iter().enumerate().flat_map(move|(a,branch)|branch.iter().flat_map(move|b|b.iter().enumerate().flat_map(move|(c,page)|page.iter().flat_map(move|p|p.iter().enumerate().filter_map(move|(d,v)|{let i=(a*FAN+c)*PAGE+d;if i<self.len{Some((i,v))}else{None}})))))
    }
    fn different_pages<F:FnMut(usize,&T,&T)>(&self,other:&Self,mut visit:F){
        assert_eq!(self.len,other.len);
        if Arc::ptr_eq(&self.root,&other.root){return;}
        for a in 0..self.root.len(){
            let left=self.root[a].as_ref();let right=other.root[a].as_ref();
            if match(left,right){(None,None)=>true,(Some(x),Some(y))=>Arc::ptr_eq(x,y),_=>false}{continue;}
            for c in 0..FAN{
                let l=left.and_then(|b|b[c].as_ref());let r=right.and_then(|b|b[c].as_ref());
                if match(l,r){(None,None)=>true,(Some(x),Some(y))=>Arc::ptr_eq(x,y),_=>false}{continue;}
                for d in 0..PAGE{let i=(a*FAN+c)*PAGE+d;if i>=self.len{break;}
                    visit(i,l.map_or(&self.zero,|p|&p[d]),r.map_or(&other.zero,|p|&p[d]));
                }
            }
        }
    }
    /// Logical population added by this sorted actual write batch. Existing COW
    /// storage is already covered by the five-state coexistence reservation.
    /// Inspection touches only addresses in the batch and allocates nothing.
    fn planned_growth<I:Iterator<Item=usize>>(&self,addresses:I)->Result<usize>{
        let(mut prior,mut prior_branch,mut prior_leaf)=(None,None,None);
        let mut bytes=0usize;
        for i in addresses{
            if i>=self.len||prior.map_or(false,|p|p>=i){return Err(MaterialError::Invalid("planned page address order"));}
            prior=Some(i);let branch_index=i/(PAGE*FAN);let leaf_index=i/PAGE;
            let branch=self.root[branch_index].as_ref();
            if prior_branch!=Some(branch_index)&&branch.is_none(){
                bytes=add_bytes(bytes,add_bytes(std::mem::size_of::<Vec<Option<Leaf<T>>>>(),checked_bytes(FAN,std::mem::size_of::<Option<Leaf<T>>>())?)?)?;
            }
            if prior_leaf!=Some(leaf_index)&&branch.and_then(|b|b[leaf_index%FAN].as_ref()).is_none(){
                bytes=add_bytes(bytes,add_bytes(std::mem::size_of::<Vec<T>>(),checked_bytes(PAGE,std::mem::size_of::<T>())?)?)?;
            }
            prior_branch=Some(branch_index);prior_leaf=Some(leaf_index);
        }Ok(bytes)
    }
    fn logical_payload(&self)->Result<usize>{
        let mut bytes=checked_bytes(self.root.capacity(),std::mem::size_of::<Option<Branch<T>>>())?;
        for branch in self.root.iter().flatten(){
            bytes=add_bytes(bytes,checked_bytes(branch.capacity(),std::mem::size_of::<Option<Leaf<T>>>())?)?;
            for leaf in branch.iter().flatten(){bytes=add_bytes(bytes,checked_bytes(leaf.capacity(),std::mem::size_of::<T>())?)?;}
        }Ok(bytes)
    }
}
fn checked_bytes(n:usize,size:usize)->Result<usize>{n.checked_mul(size).ok_or(MaterialError::Capacity("logical material size product"))}
fn add_bytes(a:usize,b:usize)->Result<usize>{a.checked_add(b).ok_or(MaterialError::Capacity("logical material size sum"))}
#[derive(Clone,Copy,Debug,Default)]
pub(crate) struct PhasePair{pub(crate) send:f64,pub(crate) receive:f64}
#[derive(Clone,Copy,Debug)]struct Ring{phase:[f64;3]}
#[derive(Clone,Copy,Debug)]struct Fact{digit:i8,present:bool}
#[derive(Clone,Copy,Debug)]struct Gate{y:f64,q:Charge,qm:Charge,qr:Charge,load:Remainder}
impl Gate{fn new()->Self{Self{y:REST,q:Charge::ZERO,qm:Charge::ZERO,qr:Charge::ZERO,load:Remainder::ZERO}}}
#[derive(Clone,Copy)]struct NumericalGate{y:f64,q:f64,qm:f64,qr:f64}
impl NumericalGate{fn project(g:Gate)->Result<Self>{Ok(Self{y:g.y,q:g.q.projection().map_err(|_|MaterialError::Arithmetic("input charge projection"))?,qm:g.qm.projection().map_err(|_|MaterialError::Arithmetic("membrane charge projection"))?,qr:g.qr.projection().map_err(|_|MaterialError::Arithmetic("receiver charge projection"))?})}}

#[derive(Clone,Debug)]
pub(crate) struct ThermalLoad{pub(crate) identity:Arc<[u8]>,pub(crate) microwatts:u64}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) struct PoweredOffset{pub(crate) ticks:u64,pub(crate) fractional_bits:u8}
#[derive(Clone,Debug)]
pub(crate) struct PaidThermalWork{pub(crate) identity:Arc<[u8]>,pub(crate) units:[u64;19]}
#[derive(Clone,Debug)]
pub(crate) struct Anatomy{
    geometry:Geometry,input_nodes:Arc<[u16]>,complete_authentic_history:Arc<[u8]>,
    reserve_capacity_ug:u64,thermal_loads:Arc<[ThermalLoad]>,
}
impl Anatomy{
    pub(crate) fn declare(geometry:Geometry,input_nodes:Arc<[u16]>,history:Arc<[u8]>,reserve_capacity_ug:u64,thermal_loads:Arc<[ThermalLoad]>)->Result<Self>{
        if history.is_empty()||input_nodes.len()!=INPUTS{return Err(MaterialError::Invalid("missing supplied history or incomplete input anatomy"));}
        for(index,&node)in input_nodes.iter().enumerate(){
            let expected=if index<480{
                let column=index/60;let within=index%60;column*320+160+within
            }else if index<512{
                let index=index-480;let ear=index/16;let band=index%16;
                (8+4*ear+band/4)*320+160+band%4
            }else{let t=index-512;(16+t%8)*320+160+t/8};
            if node as usize!=expected{return Err(MaterialError::Invalid("receptor incidence differs from complete608 anatomy"));}
        }
        // This constitution mounts the authenticated existing41.5W core source.
        // Different physical thermal anatomy requires an explicit constitution.
        if thermal_loads.len()!=1||thermal_loads[0].identity.is_empty()||thermal_loads[0].microwatts!=41_500_000{
            return Err(MaterialError::Invalid("authenticated core thermal load required"));
        }
        let thermal=Work::thermal_interval(thermal_loads[0].microwatts).map_err(MaterialError::Arithmetic)?;
        if !thermal.low_zero(work_store::CUT_BITS){return Err(MaterialError::Invalid("thermal load has no common exact event grid"));}
        Work::nutrition(reserve_capacity_ug).map_err(MaterialError::Arithmetic)?;
        Ok(Self{geometry,input_nodes,complete_authentic_history:history,reserve_capacity_ug,thermal_loads})
    }
    fn terminal_node(t:usize)->usize{(40+t%8)*320+224+t/8}
    fn fact_node(site:usize)->usize{let round=site/64;site%64*320+[0,32,160,224,288][round%5]+round/5}
    fn contact(&self,slot:usize)->Result<Contact>{self.geometry.contact(slot).ok_or(MaterialError::Invalid("unmounted contact used as active incidence"))}
    fn lambda(&self,e:Contact)->f64{self.geometry.edge_lambda(e,LAMBDA)}
    pub(crate) fn input_count(&self)->usize{INPUTS}
    pub(crate) fn reserve_capacity_micrograms(&self)->u64{self.reserve_capacity_ug}
    pub(crate) fn raw_coordinate_count(&self)->usize{2*NODES+3*FACTS+2*INPUTS+3*TERMINALS}
    pub(crate) fn input_q_reference_c(&self)->f64{(CM+CR*REST)*material::RECEIVING_RESTING_V.abs()}
    pub(crate) fn output_membrane_q_reference_c(&self)->f64{CM*material::RECEIVING_RESTING_V.abs()}
    pub(crate) fn output_receiving_q_reference_c(&self)->f64{CR*material::RECEIVING_RESTING_V.abs()}
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]pub(crate) enum PowerOrigin{MeasuredEnvironmental,BodyReserve}
#[derive(Clone,Debug)]pub(crate) struct PowerPacket{
    pub(crate) identity:Arc<[u8]>,pub(crate) receiver:u16,pub(crate) origin:PowerOrigin,
    pub(crate) acquired_start:ExactTime,pub(crate) acquired_end:ExactTime,pub(crate) available:ExactTime,
    pub(crate) release_start:ExactTime,pub(crate) release_end:ExactTime,
    pub(crate) admitted_j:f64,pub(crate) lower_j:f64,pub(crate) upper_j:f64,
}
#[derive(Clone,Debug)]struct PendingPower{packet:PowerPacket,remaining:Work,source_voltage:f64,release_ms:u8}
#[derive(Clone,Debug)]struct Delivery{field:Arc<SharedJointField>,identity:Arc<[u8]>,published:ExactTime,gate:usize,remaining_ms:u16,installed:bool}
#[derive(Clone,Copy,Debug,Default)]pub(crate) struct WorkEvidence{
    pub(crate) supply_j:f64,pub(crate) field_switch_j:f64,pub(crate) source_heat_j:f64,
    pub(crate) contact_heat_j:f64,pub(crate) phase_heat_j:f64,pub(crate) gate_heat_j:f64,
    pub(crate) exported_j:f64,pub(crate) plastic_heat_j:f64,pub(crate) return_map_dissipation_j:f64,
    pub(crate) stop_dissipation_j:f64,pub(crate) energy_residual_j:f64,
    pub(crate) nonlinear_bound:f64,pub(crate) error_estimate:f64,
    pub(crate) circuit_tail_charge_c:f64,pub(crate) circuit_tail_work_j:f64,pub(crate) circuit_projection_defect_v:f64,
    pub(crate) contact_energy_change_j:f64,pub(crate) contact_energy_change_lower_j:f64,pub(crate) contact_energy_change_upper_j:f64,
}
impl WorkEvidence{fn add(&mut self,b:Self){
    self.supply_j+=b.supply_j;self.field_switch_j+=b.field_switch_j;self.source_heat_j+=b.source_heat_j;self.contact_heat_j+=b.contact_heat_j;
    self.phase_heat_j+=b.phase_heat_j;self.gate_heat_j+=b.gate_heat_j;self.exported_j+=b.exported_j;self.plastic_heat_j+=b.plastic_heat_j;
    self.return_map_dissipation_j+=b.return_map_dissipation_j;self.stop_dissipation_j+=b.stop_dissipation_j;self.energy_residual_j+=b.energy_residual_j;
    self.nonlinear_bound=self.nonlinear_bound.max(b.nonlinear_bound);self.error_estimate=self.error_estimate.max(b.error_estimate);
    self.circuit_tail_charge_c+=b.circuit_tail_charge_c;self.circuit_tail_work_j+=b.circuit_tail_work_j;
    self.circuit_projection_defect_v=self.circuit_projection_defect_v.max(b.circuit_projection_defect_v);
    self.contact_energy_change_j+=b.contact_energy_change_j;
    self.contact_energy_change_lower_j=down(self.contact_energy_change_lower_j+b.contact_energy_change_lower_j);
    self.contact_energy_change_upper_j=up(self.contact_energy_change_upper_j+b.contact_energy_change_upper_j);
}}
#[derive(Clone,Copy,Debug)]pub(crate) struct Admission{
    pub(crate) max_force_terms:u64,pub(crate) max_yield_queries:u64,
    /// Aggregate numerical scratch and actual five-state contact growth.
    pub(crate) max_staged_bytes:usize,
    /// Shared source/identity payload bound, independent of numerical scratch.
    pub(crate) max_source_bytes:usize,
}
#[derive(Clone,Copy,Debug,Default)]pub(crate) struct WorkCount{
    pub(crate) force_terms:u64,pub(crate) yield_queries:u64,
    /// Aggregate logical scratch plus five-state actual population growth.
    pub(crate) staged_bytes:usize,
    /// Transient admission evidence, not material state or a learning count.
    /// Includes every admitted trial batch, even when its trial is discarded.
    pub(crate) contact_growth_bytes:usize,
}
impl WorkCount{
    #[track_caller]
    fn preflight_force(&self,n:usize,a:Admission)->Result<()>{
        let end=self.force_terms.checked_add(n as u64).ok_or(MaterialError::Capacity("force counter"))?;
        if end>a.max_force_terms{
            let caller=std::panic::Location::caller();
            Err(MaterialError::ForceCapacity{reason:"reached force work",used:self.force_terms,
                requested:n as u64,limit:a.max_force_terms,file:caller.file(),line:caller.line(),
                nonlinear_iteration:None,adaptive_stage:None,trial_span_ticks:None,refinement_depth:None,trial_entry_force_terms:None,preceding_refinement:None})
        }else{Ok(())}
    }
    #[track_caller]
    fn force(&mut self,n:usize,a:Admission)->Result<()>{self.preflight_force(n,a)?;self.force_terms+=n as u64;Ok(())}
    fn query(&mut self,n:usize,a:Admission)->Result<()>{self.yield_queries=self.yield_queries.checked_add(n as u64).ok_or(MaterialError::Capacity("query counter"))?;if self.yield_queries>a.max_yield_queries{Err(MaterialError::Capacity("yield query work"))}else{Ok(())}}
    fn scratch(&mut self,n:usize,a:Admission)->Result<()>{
        let aggregate=add_bytes(n,checked_bytes(self.contact_growth_bytes,5)?)?;
        if aggregate>a.max_staged_bytes{return Err(MaterialError::Capacity("reached material scratch"));}
        self.staged_bytes=self.staged_bytes.max(aggregate);Ok(())
    }
    fn admit_contact_growth(&mut self,bytes:usize,a:Admission)->Result<()>{
        let growth=add_bytes(self.contact_growth_bytes,bytes)?;
        let aggregate=add_bytes(self.staged_bytes,checked_bytes(bytes,5)?)?;
        if aggregate>a.max_staged_bytes{return Err(MaterialError::Capacity("reached contact allocation"));}
        self.contact_growth_bytes=growth;self.staged_bytes=aggregate;Ok(())
    }
}
#[derive(Clone,Debug)]pub(crate) struct TimedDischarge{pub(crate) at:ExactTime,pub(crate) terminal:u8,pub(crate) carriers:u64}

#[derive(Clone,Debug)]pub(crate) struct Functional64Material{
    anatomy:Arc<Anatomy>,clock:ExactTime,phases:Pages<PhasePair>,rings:Pages<Ring>,weights:Pages<f64>,
    incident:Pages<Arc<Vec<u32>>>,nonzero_nodes:Arc<BTreeSet<u16>>,facts:Arc<[Fact]>,gates:Arc<Vec<Gate>>,
    power:Vec<PendingPower>,last_power:Vec<Option<ExactTime>>,delivery:VecDeque<Delivery>,
    reserve_ug:u64,work:Work,unavailable_since:Option<ExactTime>,contact_changes:Pages<bool>,
}
pub(crate) struct MaterialInputs{pub(crate) start:ExactTime,pub(crate) end:ExactTime,pub(crate) actual_reserve_ug:u64,pub(crate) power:Vec<PowerPacket>,pub(crate) field:Option<(Arc<SharedJointField>,Arc<[u8]>,ExactTime)>,pub(crate) admission:Admission}
pub(crate) struct PreparedMaterial{
    pub(crate) successor:Functional64Material,pub(crate) discharges:Vec<TimedDischarge>,
    pub(crate) reserve_consumed_ug:u64,pub(crate) evidence:WorkEvidence,pub(crate) work:WorkCount,
    pub(crate) powered_offset:PoweredOffset,pub(crate) paid_thermal:Vec<PaidThermalWork>,
    /// All positive native reserve debits: field installation plus funded rates.
    pub(crate) debited_work:[u64;19],
    /// Actual fixed-state constraint removal returns to this same work store.
    pub(crate) recovered_field_work:[u64;19],
    /// Electrical supplies only; thermal already appears in paid_thermal.
    pub(crate) supplied_work_units:[u64;19],pub(crate) transducer_heat_units:[u64;19],
}
pub(crate) struct PreparedAssimilation{pub(crate) successor:Functional64Material,pub(crate) assimilated_ug:u64,pub(crate) remaining_digestible_ug:u64}
impl Functional64Material{
    /// Explicit new material commissioning; ordinary decode never calls this.
    pub(crate) fn commission(anatomy:Arc<Anatomy>,clock:ExactTime,authentic_weights:&[(u32,f64)],reserve_ug:u64)->Result<Self>{
        if reserve_ug>anatomy.reserve_capacity_ug{return Err(MaterialError::Invalid("reserve exceeds authenticated capacity"));}
        let mut s=Self{anatomy,clock,phases:Pages::new(NODES,PhasePair::default()),rings:Pages::new(FACTS,Ring{phase:[0.0;3]}),weights:Pages::new(RAW_SLOTS,0.0),incident:Pages::new(NODES,Arc::new(Vec::new())),nonzero_nodes:Arc::new(BTreeSet::new()),facts:vec![Fact{digit:0,present:false};FACTS].into(),gates:Arc::new(vec![Gate::new();INPUTS+TERMINALS]),power:Vec::new(),last_power:vec![None;INPUTS],delivery:VecDeque::new(),reserve_ug,work:Work::ZERO,unavailable_since:None,contact_changes:Pages::new(RAW_SLOTS,false)};
        let mut prior=None;
        for &(slot,w)in authentic_weights{
            if slot as usize>=RAW_SLOTS||!w.is_finite()||w.to_bits()==0||prior.map_or(false,|p|p>=slot){return Err(MaterialError::Invalid("authentic sparse raw contact custody"));}
            prior=Some(slot);s.weights.set(slot as usize,w)?;
        }
        s.rebuild_incident()?;Ok(s)
    }
    fn rebuild_incident(&mut self)->Result<()>{
        let mut rows:BTreeMap<u16,Vec<u32>>=BTreeMap::new();
        for(slot,&w)in self.weights.allocated(){if w!=0.0{if let Some(e)=self.anatomy.geometry.contact(slot){
            rows.entry(e.from).or_default().push(slot as u32);if e.to!=e.from{rows.entry(e.to).or_default().push(slot as u32);}
        }}}
        let mut incident=Pages::new(NODES,Arc::new(Vec::new()));
        for(node,slots)in rows{incident.set(node as usize,Arc::new(slots))?;}
        self.incident=incident;Ok(())
    }
    /// One sorted merge per affected node, never one degree-sized copy per edge.
    /// Plan the entire actual batch before persistent page/index allocation.
    fn change_weights(&mut self,changes:&[(usize,f64)],count:&mut WorkCount,admission:Admission)->Result<()>{
        // The plastic-return frontier already admits this candidate workspace
        // together with its live numerical arrays. This also covers direct
        // component callers, without charging hypothetical query opportunities.
        count.scratch(checked_bytes(changes.len(),8*(std::mem::size_of::<u32>()+std::mem::size_of::<(usize,f64)>()))?,admission)?;
        let mut edits:BTreeMap<u16,Vec<(u32,bool)>>=BTreeMap::new();let mut prior=None;
        for &(slot,w)in changes{
            finite(w)?;if slot>=RAW_SLOTS||prior.map_or(false,|p|p>=slot){return Err(MaterialError::Invalid("plastic contact batch order"));}prior=Some(slot);
            let old=*self.weights.get(slot);
            if (old==0.0)!=(w==0.0){let e=self.anatomy.contact(slot)?;
                edits.entry(e.from).or_default().push((slot as u32,w!=0.0));
                if e.to!=e.from{edits.entry(e.to).or_default().push((slot as u32,w!=0.0));}
            }
        }
        let mut growth=self.weights.planned_growth(changes.iter().map(|&(slot,_)|slot))?;
        growth=add_bytes(growth,self.contact_changes.planned_growth(changes.iter().map(|&(slot,_)|slot))?)?;
        growth=add_bytes(growth,self.incident.planned_growth(edits.keys().map(|&node|node as usize))?)?;
        for(&node,rows)in &edits{
            let old=self.incident.get(node as usize);let capacity=add_bytes(old.len(),rows.len())?;
            if Arc::ptr_eq(old,&self.incident.zero){growth=add_bytes(growth,std::mem::size_of::<Vec<u32>>())?;}
            growth=add_bytes(growth,checked_bytes(capacity.saturating_sub(old.capacity()),std::mem::size_of::<u32>())?)?;
        }
        count.admit_contact_growth(growth,admission)?;
        // All range/order/geometry/size/admission checks precede these writes.
        for &(slot,w)in changes{self.weights.set(slot,w)?;self.contact_changes.set(slot,true)?;}
        for(node,edits)in edits{
            let old=self.incident.get(node as usize);let mut rows=Vec::with_capacity(old.len()+edits.len());let(mut i,mut j)=(0,0);
            while i<old.len()||j<edits.len(){
                if j==edits.len()||(i<old.len()&&old[i]<edits[j].0){rows.push(old[i]);i+=1;}
                else if i==old.len()||edits[j].0<old[i]{if edits[j].1{rows.push(edits[j].0);}j+=1;}
                else{if edits[j].1{rows.push(edits[j].0);}i+=1;j+=1;}
            }
            self.incident.set(node as usize,Arc::new(rows))?;
        }Ok(())
    }
    pub(crate) fn can_accept_field(&self)->bool{self.delivery.len()<2}
    pub(crate) fn clock(&self)->ExactTime{self.clock}
    pub(crate) fn thermal_loads(&self)->&[ThermalLoad]{&self.anatomy.thermal_loads}
}

/// Directed lower voltage for the declared constant-power transducer. The
/// exact finite packet funds the interval; the difference is transducer heat.
/// Every stage derives from this packet's own real release duration.
fn packet_voltage_power_upper(voltage:f64,upper_duration:f64)->f64{
    // Zero is exact physical zero; do not create a subnormal charge of work.
    if voltage==0.0{0.0}else{up(up(up(voltage*voltage)*G)*upper_duration)}
}
fn packet_source_voltage(packet:&PowerPacket,release_ms:u8)->Result<f64>{
    if packet.admitted_j==0.0{return Ok(0.0);}
    let duration=release_ms as f64/1000.0;
    // Preserve every formerly certified drive bit-for-bit. Only the rejected
    // rounding boundary below needs a further downward representable search.
    let p=finite(packet.admitted_j/up(duration))?;
    let p=if p==0.0{0.0}else{down(p).max(0.0)};
    let ratio=finite(p/G)?;let ratio=if ratio==0.0{0.0}else{down(ratio).max(0.0)};
    let root=ratio.sqrt();let voltage=if root==0.0{0.0}else{down(root).max(0.0)};
    nonnegative(voltage)?;let upper_duration=up(duration);
    let fits=|v:f64|{let upper=packet_voltage_power_upper(v,upper_duration);upper.is_finite()&&upper<=packet.admitted_j};
    if fits(voltage){return Ok(voltage);}
    // Nonnegative finite binary64 bit patterns preserve numerical order. Each
    // positive multiplication and next_up is monotone; zero always fits. The
    // original candidate is the upper endpoint, so no source gain is added.
    let(mut low,mut high)=(0u64,voltage.to_bits());
    for _ in 0..(u64::BITS-1){
        if low==high{break;}
        let middle=low+(high-low+1)/2;
        if fits(f64::from_bits(middle)){low=middle;}else{high=middle-1;}
    }
    if low!=high{return Err(MaterialError::UnresolvedEvent("source voltage power enclosure search"));}
    Ok(f64::from_bits(low))
}

// Evaluation-local immutable-anatomy lookup. No material/cache state is retained.
struct ColumnAdjacency{incoming:[u64;64],outgoing:[u64;64],present:u64}
impl ColumnAdjacency{
    fn new()->Self{Self{incoming:[0;64],outgoing:[0;64],present:0}}
    fn row(&mut self,geometry:&Geometry,column:usize,count:&mut WorkCount,admission:Admission)->Result<(u64,u64)>{
        if self.present&(1u64<<column)==0{
            let mut incoming=0u64;let mut outgoing=0u64;
            for other in 0..64{count.force(1,admission)?;
                if geometry.fasciculated(other,column){incoming|=1u64<<other;}
                if geometry.fasciculated(column,other){outgoing|=1u64<<other;}
            }
            self.incoming[column]=incoming;self.outgoing[column]=outgoing;self.present|=1u64<<column;
        }Ok((self.incoming[column],self.outgoing[column]))
    }
}
#[derive(Clone)]struct LocalVector{nodes:Vec<PhasePair>,rings:Vec<[f64;3]>,gates:Vec<NumericalGate>}
#[derive(Clone,Copy)]struct ActiveEdge{contact:Contact,weight:f64,lambda:f64}
struct Frontier{nodes:Vec<usize>,rings:Vec<usize>,edges:Vec<ActiveEdge>,index:Vec<usize>,scratch_base:usize}
impl Frontier{
    fn scratch_bound(nodes:usize,rings:usize,edge_slots:usize)->Result<usize>{
        // At most ten simultaneous local/gradient/interval arrays per trial,
        // plus BFS, incidence slots and the bounded positive circuit series.
        let a=checked_bytes(nodes,10*std::mem::size_of::<PhasePair>()+8*8)?;
        let b=checked_bytes(rings,10*3*8+2*std::mem::size_of::<usize>())?;
        let c=checked_bytes(edge_slots,2*(std::mem::size_of::<ActiveEdge>()+std::mem::size_of::<u32>()))?;
        let fixed=checked_bytes(NODES,1+8*std::mem::size_of::<usize>())?;
        let gates=checked_bytes(INPUTS+TERMINALS,10*std::mem::size_of::<NumericalGate>()+std::mem::size_of::<Gate>())?;
        let drive=checked_bytes(INPUTS,2*(std::mem::size_of::<Work>()+8))?;
        // One moved608-path receipt heap, both handoff headers and one
        // bounded coefficient/moment workspace reused across input ports.
        let input_paths=add_bytes(checked_bytes(INPUTS,std::mem::size_of::<InputPathStep>())?,2*std::mem::size_of::<Vec<InputPathStep>>())?;
        let path_scratch=input_path_scratch_bytes()?;
        let series=add_bytes(checked_bytes(circuit_series_limit(),2*8)?,checked_bytes(2*(MAX_REFINEMENT+1),std::mem::size_of::<(u64,usize)>())?)?;
        // One moved immediate-left trial adds inline custody, never another
        // heap state beyond the existing five-state preparation envelope.
        let immediate_left=std::mem::size_of::<Option<(u64,usize,TrialStep)>>();
        [b,c,fixed,gates,drive,input_paths,path_scratch,series,immediate_left,causal_comparison_scratch_bytes()?,contact_operator::scratch_bytes()?,std::mem::size_of::<ColumnAdjacency>(),checked_bytes(64*3,8)?].into_iter().try_fold(a,add_bytes)
    }
    fn new(s:&Functional64Material,voltage:&[f64],count:&mut WorkCount,admission:Admission)->Result<Self>{
        count.scratch(Self::scratch_bound(NODES,FACTS,0)?,admission)?;
        let mut reached=vec![false;NODES];let mut queue=Vec::with_capacity(NODES);
        let mut seen23=[[0u64;2];64];let mut seen5=[0u64;64];
        fn reach(n:usize,seen:&mut[bool],queue:&mut Vec<usize>,seen23:&mut[[u64;2];64],seen5:&mut[u64;64]){
            if seen[n]{return;}seen[n]=true;queue.push(n);let c=n/320;let i=n%320;
            if(32..160).contains(&i){let j=i-32;seen23[c][j/64]|=1u64<<(j%64);}
            else if(224..288).contains(&i){seen5[c]|=1u64<<(i-224);}
        }
        fn coupled(s:&Functional64Material,n:usize,m:usize,count:&mut WorkCount,a:Admission)->Result<bool>{
            let mut result=false;
            for(from,to)in[(n,m),(m,n)]{if let Some(e)=s.anatomy.geometry.between(from,to){
                let b=s.anatomy.geometry.baseline(e);if b!=0.0{count.query(1,a)?;
                    result|=finite(b+*s.weights.get(e.authentic_slot as usize))?!=0.0;
                }
            }}Ok(result)
        }
        for &n in s.nonzero_nodes.iter(){reach(n as usize,&mut reached,&mut queue,&mut seen23,&mut seen5);}
        for(i,g)in s.gates.iter().enumerate(){let active=if i<INPUTS{g.y!=REST||!g.q.magnitude.is_zero()||voltage[i]!=0.0}else{g.y!=REST};
            if active{reach(if i<INPUTS{s.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-INPUTS)},&mut reached,&mut queue,&mut seen23,&mut seen5);}}
        for(site,fact)in s.facts.iter().enumerate(){if fact.present&&(fact.digit!=0||s.rings.get(site).phase.iter().any(|&x|x!=0.0)){
            reach(Anatomy::fact_node(site),&mut reached,&mut queue,&mut seen23,&mut seen5);}}
        let mut cursor=0;let mut slots=Vec::new();let mut adjacency=ColumnAdjacency::new();
        while cursor<queue.len(){let n=queue[cursor];cursor+=1;
            for &slot in s.incident.get(n).iter(){count.query(1,admission)?;
                let next=slots.len().checked_add(1).ok_or(MaterialError::Capacity("frontier slot count"))?;
                count.scratch(Self::scratch_bound(NODES,FACTS,next)?,admission)?;
                let e=s.anatomy.contact(slot as usize)?;let a=finite(s.anatomy.geometry.baseline(e)+*s.weights.get(slot as usize))?;
                if a!=0.0{reach(e.from as usize,&mut reached,&mut queue,&mut seen23,&mut seen5);reach(e.to as usize,&mut reached,&mut queue,&mut seen23,&mut seen5);}
                slots.push(slot);
            }
            for other in Geometry::baseline_intra_neighbors(n).into_iter().flatten(){
                if !reached[other]&&coupled(s,n,other,count,admission)?{reach(other,&mut reached,&mut queue,&mut seen23,&mut seen5);}
            }
            let local=n%320;let family=if(32..160).contains(&local){Some((32,128,local-32))}
                else if(224..288).contains(&local){Some((224,64,local-224))}else{None};
            if let Some((offset,width,index))=family{let mask=Geometry::inter_mask(index,width).map_err(MaterialError::Invalid)?;
                let(incoming,outgoing)=adjacency.row(&s.anatomy.geometry,n/320,count,admission)?;
                let mut columns=incoming|outgoing;
                while columns!=0{let column=columns.trailing_zeros()as usize;columns&=columns-1;count.force(1,admission)?;
                    let seen=if width==128{seen23[column]}else{[seen5[column],0]};
                    for word in 0..2{let mut candidates=mask[word]&!seen[word];while candidates!=0{
                        let bit=candidates.trailing_zeros()as usize;candidates&=candidates-1;let other=column*320+offset+word*64+bit;
                        if !reached[other]&&coupled(s,n,other,count,admission)?{reach(other,&mut reached,&mut queue,&mut seen23,&mut seen5);}
                    }}
                }
            }
        }
        queue.sort_unstable();slots.sort_unstable();slots.dedup();
        let mut index=vec![usize::MAX;NODES];for(i,&n)in queue.iter().enumerate(){index[n]=i;}
        let rings=s.facts.iter().enumerate().filter_map(|(i,f)|if f.present&&reached[Anatomy::fact_node(i)]{Some(i)}else{None}).collect::<Vec<_>>();
        let edges=slots.into_iter().map(|slot|{let contact=s.anatomy.contact(slot as usize)?;Ok(ActiveEdge{contact,weight:*s.weights.get(slot as usize),lambda:s.anatomy.lambda(contact)})}).collect::<Result<Vec<_>>>()?;
        let scratch_base=Self::scratch_bound(queue.len(),rings.len(),edges.len())?;count.scratch(scratch_base,admission)?;
        Ok(Self{nodes:queue,rings,edges,index,scratch_base})
    }
    fn view(&self,s:&Functional64Material)->Result<LocalVector>{Ok(LocalVector{nodes:self.nodes.iter().map(|&n|*s.phases.get(n)).collect(),rings:self.rings.iter().map(|&i|s.rings.get(i).phase).collect(),gates:s.gates.iter().copied().map(NumericalGate::project).collect::<Result<Vec<_>>>()?})}
    fn pair(&self,v:&LocalVector,s:&Functional64Material,n:usize)->PhasePair{let i=self.index[n];if i==usize::MAX{*s.phases.get(n)}else{v.nodes[i]}}
}
// Elastic gate extension only. The input circuit's integrated electrical
// reaction is duration-dependent and belongs to its one coupled path receipt.
fn gate_reaction_terms(p:PhasePair,q:PhasePair,before:NumericalGate,after:NumericalGate)->f64{
    let e0=before.y-REST-ALPHA*(p.receive.sin()-p.send.sin());let e1=after.y-REST-ALPHA*(q.receive.sin()-q.send.sin());
    0.5*(e0+e1)
}
struct Gradient{nodes:Vec<PhasePair>,rings:Vec<[f64;3]>,gate_e:Vec<f64>,contact_error:f64}
impl Functional64Material{
    fn gradient(&self,f:&Frontier,a:&LocalVector,b:&LocalVector,count:&mut WorkCount,admission:Admission)->Result<Gradient>{
        count.force(f.nodes.len()+f.edges.len()+f.rings.len()*4+self.gates.len(),admission)?;
        let mut g=Gradient{nodes:vec![PhasePair::default();f.nodes.len()],rings:vec![[0.0;3];f.rings.len()],gate_e:vec![0.0;a.gates.len()],contact_error:0.0};
        // Trigonometric operands are computed once per actually reached node,
        // never once for every one of its incident contacts.
        let terms=a.nodes.iter().zip(&b.nodes).map(|(p,q)|[
            0.5*(p.send.sin()+q.send.sin()),0.5*(p.receive.sin()+q.receive.sin()),dsin(p.send,q.send),dsin(p.receive,q.receive),
        ]).collect::<Vec<_>>();
        for(i,_)in f.nodes.iter().enumerate(){
            let[v,u,dv,du]=terms[i];
            g.nodes[i].send=LAMBDA*(v-u)*dv;g.nodes[i].receive=LAMBDA*(u-v)*du;
        }
        let contact=contact_operator::forces(self,f,a,b,count,admission)?;
        for i in 0..f.nodes.len(){
            let send=Interval::point(g.nodes[i].send).add(contact.ranges[i][0]);
            let receive=Interval::point(g.nodes[i].receive).add(contact.ranges[i][1]);
            g.nodes[i].send+=contact.nodes[i].send;g.nodes[i].receive+=contact.nodes[i].receive;
            g.contact_error=g.contact_error.max(contact_operator::error(g.nodes[i].send,send)?).max(contact_operator::error(g.nodes[i].receive,receive)?);
        }
        for(i,&site)in f.rings.iter().enumerate(){
            let tau=self.facts[site].digit as f64*std::f64::consts::TAU/3.0;
            for(edge,k)in[LAMBDA,LAMBDA,LAMBDA/std::f64::consts::SQRT_2].iter().enumerate(){
                let next=(edge+1)%3;let d0=a.rings[i][next]-a.rings[i][edge];let d1=b.rings[i][next]-b.rings[i][edge];
                let force=k*(0.5*(d0+d1)-tau).sin()*sinc(0.5*(d1-d0));g.rings[i][edge]-=force;g.rings[i][next]+=force;
            }
            let n=f.index[Anatomy::fact_node(site)];let d0=a.rings[i][0]-a.nodes[n].receive;let d1=b.rings[i][0]-b.nodes[n].receive;
            let force=LAMBDA*(0.5*(d0+d1)).sin()*sinc(0.5*(d1-d0));g.rings[i][0]+=force;g.nodes[n].receive-=force;
        }
        for i in 0..a.gates.len(){
            let node=if i<self.anatomy.input_count(){self.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-self.anatomy.input_count())};
            let p=f.pair(a,self,node);let q=f.pair(b,self,node);
            let e=gate_reaction_terms(p,q,a.gates[i],b.gates[i]);
            g.gate_e[i]=e;let n=f.index[node];
            if n!=usize::MAX{g.nodes[n].send+=COUPLING*e*dsin(p.send,q.send);g.nodes[n].receive-=COUPLING*e*dsin(p.receive,q.receive);}
        }
        if g.nodes.iter().any(|p|!p.send.is_finite()||!p.receive.is_finite())||g.rings.iter().flatten().any(|x|!x.is_finite())||g.gate_e.iter().any(|x|!x.is_finite()){
            return Err(MaterialError::Arithmetic("nonfinite reciprocal gradient"));
        }Ok(g)
    }
    fn contraction(&self,f:&Frontier,_a:&LocalVector,voltage:&[f64],h:f64)->Result<f64>{
        let point=Interval::point;let l=point(LAMBDA);let two=point(2.0);
        let mut rows=Vec::with_capacity(f.nodes.len());
        for &node in &f.nodes{let b=self.anatomy.geometry.baseline_inverse_bounds(node);
            let receive=if self.anatomy.geometry.degree(node)==0{point(0.0)}else{
                let d=point(self.anatomy.geometry.degree(node)as f64);l.positive_div(d)?.mul(d)};
            rows.push((l.mul(point(b[0])).add(l.mul(point(b[1]))).add(two.mul(l)),receive.add(l.mul(point(b[2]))).add(two.mul(l))));
        }
        for edge in &f.edges{let e=edge.contact;let baseline=self.anatomy.geometry.baseline(e);let b=point(baseline);
            let selected=finite(baseline+edge.weight)?;let effective=b.add(point(edge.weight));
            if !effective.lo.is_finite()||!effective.hi.is_finite(){return Err(MaterialError::UnresolvedEvent("effective contact bound"));}
            // W dominates both authentic |w| and A-b, where A encloses the
            // real operand sum and its selected rounded gain. Thus b+W>=A,
            // and the positive expansion below bounds BOTH gain definitions.
            let amplitude=effective.absmax().max(selected.abs());
            let envelope=finite(edge.weight.abs().max(up(amplitude-baseline)))?;let w=point(envelope);
            let lambda=l.positive_div(point(self.anatomy.geometry.degree(e.to as usize)as f64))?;
            let extra=lambda.mul(w.mul(w).add(two.mul(b).mul(w)).add(w));let send=f.index[e.from as usize];let receive=f.index[e.to as usize];
            if send!=usize::MAX{rows[send].0=rows[send].0.add(extra);}if receive!=usize::MAX{rows[receive].1=rows[receive].1.add(lambda.mul(w));}
        }
        let opening=point(1.0).sub(point(REST));
        let emax=Interval{lo:opening.lo.max(REST),hi:opening.hi.max(REST)}.add(two.mul(point(ALPHA)));
        for i in 0..self.gates.len(){let node=if i<INPUTS{self.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-INPUTS)};
            let n=f.index[node];if n!=usize::MAX{let r=point(COUPLING).mul(point(ALPHA).add(point(0.5).mul(emax)).add(point(0.5)));
                rows[n].0=rows[n].0.add(r);rows[n].1=rows[n].1.add(r);}}
        for &site in &f.rings{let n=f.index[Anatomy::fact_node(site)];rows[n].1=rows[n].1.add(l);}
        let phase_scale=point(h).positive_div(point(DRAG))?;let row=rows.iter().fold(0.0f64,|v,r|v.max(r.0.hi).max(r.1.hi));
        let mut q=phase_scale.mul(point(row)).hi;if !f.rings.is_empty(){q=q.max(point(3.0).mul(phase_scale).mul(l).hi);}
        let denominator=point(1.0).add(point(h).mul(point(K)).positive_div(two.mul(point(ZETA)))?);
        for(i,gate)in self.gates.iter().enumerate(){
            let mut row=two.mul(point(h)).mul(point(COUPLING)).positive_div(point(ZETA).mul(denominator))?;
            if i<INPUTS{let actual=up(gate.q.projection().map_err(|_|MaterialError::Arithmetic("contraction charge projection"))?);
                let capacity=point(CM).add(point(CR));let qb=point(actual.max(capacity.mul(point(voltage[i])).hi));
                let first=point(CR).mul(qb).mul(qb).positive_div(two.mul(point(CM)).mul(point(CM)))?;
                let second=point(CR).mul(point(CR)).mul(qb).mul(qb).positive_div(two.mul(point(CM)).mul(point(CM)).mul(point(CM)))?;
                row=row.add(point(h).positive_div(point(ZETA).mul(denominator))?.mul(first.add(second)));
                q=q.max(point(3.0).mul(point(CR)).positive_div(point(CM))?.hi);
            }q=q.max(row.hi);
        }
        if !q.is_finite()||q<0.0{return Err(MaterialError::UnresolvedEvent("global contraction enclosure"));}Ok(q)
    }
    fn solve_elastic(&self,f:&mut Frontier,a:&LocalVector,voltage:&[f64],h:f64,initial_gradient:&mut Option<Gradient>,count:&mut WorkCount,admission:Admission)->Result<(LocalVector,WorkEvidence,Vec<InputPathStep>)>{
        let q=self.contraction(f,a,voltage,h)?;if q>=1.0{return Err(MaterialError::UnresolvedEvent("global numerical map is not contractive"));}
        let mut b=a.clone();let mut bound=f64::INFINITY;let mut input_paths=vec![InputPathStep::default();INPUTS];
        for iteration in 0..MAX_ITERATIONS{
            let at_iteration=|mut error|{
                // One-based current nonlinear iteration, only when its force
                // evaluation is the actual capacity-refusal source.
                if let MaterialError::ForceCapacity{nonlinear_iteration,..}=&mut error{*nonlinear_iteration=Some(iteration+1);}error
            };
            let fresh;
            let g=if iteration==0{
                if initial_gradient.is_none(){
                    // Only after this duration's successful contraction check.
                    // Derive the original base, never re-add to an augmented one.
                    let base=Frontier::scratch_bound(f.nodes.len(),f.rings.len(),f.edges.len())?;
                    let retained=CommonStart::retained_gradient_bytes(f,a.gates.len())?;
                    let shared_base=add_bytes(base,retained)?;count.scratch(shared_base,admission)?;
                    f.scratch_base=shared_base;
                    *initial_gradient=Some(self.gradient(f,a,&b,count,admission).map_err(at_iteration)?);
                }
                initial_gradient.as_ref().unwrap()
            }else{
                fresh=self.gradient(f,a,&b,count,admission).map_err(at_iteration)?;&fresh
            };
            let mut next=b.clone();let mut residual=0.0f64;let mut path_error=0.0f64;
            for i in 0..f.nodes.len(){next.nodes[i].send=a.nodes[i].send-h*g.nodes[i].send/DRAG;next.nodes[i].receive=a.nodes[i].receive-h*g.nodes[i].receive/DRAG;
                residual=residual.max(up((next.nodes[i].send-b.nodes[i].send).abs())).max(up((next.nodes[i].receive-b.nodes[i].receive).abs()));}
            for i in 0..f.rings.len(){for j in 0..3{next.rings[i][j]=a.rings[i][j]-h*g.rings[i][j]/DRAG;residual=residual.max(up((next.rings[i][j]-b.rings[i][j]).abs()));}}
            for i in 0..a.gates.len(){
                let node=if i<self.anatomy.input_count(){self.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-self.anatomy.input_count())};
                let p=f.pair(a,self,node);let r=f.pair(&b,self,node);let s=0.5*(p.receive.sin()-p.send.sin()+r.receive.sin()-r.send.sin());let k=h*K/(2.0*ZETA);
                let path=if i<INPUTS{
                    Some(input_gate_path_step(self.gates[i].q,a.gates[i].y,b.gates[i].y,voltage[i],h,count,admission)?)
                }else{None};
                let cap=path.map_or(0.0,|p|p.cap_reaction);
                // Same elastic increment and stop law; the capacitor force is
                // the time-integrated reaction of this very charge trajectory.
                let trial=a.gates[i].y+(h/ZETA)*(K*(REST-a.gates[i].y+ALPHA*s)-cap)/(1.0+k);
                finite(trial)?;next.gates[i].y=trial.max(0.0).min(1.0);residual=residual.max(up((next.gates[i].y-b.gates[i].y).abs()));
                if let Some(path)=path{
                    let charge=self.gates[i].q.add_packet(path.dq).map_err(|_|MaterialError::Arithmetic("input exact current custody"))?;
                    next.gates[i].q=charge.projection().map_err(|_|MaterialError::Arithmetic("input charge projection"))?;
                    input_paths[i]=path;
                    nonnegative(next.gates[i].q)?;let scale=a.gates[i].q.max((CM+CR)*voltage[i]);
                    if scale>0.0{
                        residual=residual.max(up(up((next.gates[i].q-b.gates[i].q).abs())/scale));
                        path_error=path_error.max(Interval::point(path.tail_charge_c).positive_div(Interval::point(scale))?.hi);
                    }else if next.gates[i].q!=0.0{return Err(MaterialError::Arithmetic("unpowered charge genesis"));}
                    // tail_work also encloses generalized gate work for
                    // |dy|<=1, hence bounds its J-valued cap-reaction error.
                    let gate_tail=Interval::point(h).mul(Interval::point(path.tail_work_j))
                        .positive_div(Interval::point(ZETA).mul(Interval::point(1.0+k)))?.hi;
                    path_error=path_error.max(gate_tail);
                }
            }
            finite(residual)?;
            let denominator=down(1.0-q);if denominator<=0.0{return Err(MaterialError::UnresolvedEvent("positive global residual denominator"));}
            let force_error=Interval::point(h).positive_div(Interval::point(DRAG))?.mul(Interval::point(g.contact_error)).hi;
            bound=finite(up(up(up(residual+force_error)+path_error)/denominator))?;b=next;if bound<=SOLVE_TOL{break;}
        }
        if bound>SOLVE_TOL{return Err(MaterialError::UnresolvedEvent("global nonlinear residual budget"));}
        count.force(a.gates.len(),admission)?;let mut evidence=WorkEvidence::default();evidence.nonlinear_bound=bound;
        for i in 0..f.nodes.len(){let ds=b.nodes[i].send-a.nodes[i].send;let dr=b.nodes[i].receive-a.nodes[i].receive;evidence.phase_heat_j+=DRAG*(ds*ds+dr*dr)/h;}
        for i in 0..f.rings.len(){for j in 0..3{let d=b.rings[i][j]-a.rings[i][j];evidence.phase_heat_j+=DRAG*d*d/h;}}
        for i in 0..a.gates.len(){
            let dy=b.gates[i].y-a.gates[i].y;evidence.gate_heat_j+=ZETA*dy*dy/h;
            let node=if i<self.anatomy.input_count(){self.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-self.anatomy.input_count())};
            let p=f.pair(a,self,node);let q=f.pair(&b,self,node);
            let gate_e=gate_reaction_terms(p,q,a.gates[i],b.gates[i]);
            let gate_cap=if i<INPUTS{input_paths[i].cap_reaction}else{0.0};
            if !gate_e.is_finite()||!gate_cap.is_finite(){return Err(MaterialError::Arithmetic("nonfinite reciprocal gradient"));}
            let reaction=K*gate_e+gate_cap+ZETA*dy/h;let work=-reaction*dy;
            if b.gates[i].y==0.0||b.gates[i].y==1.0{if work<0.0{return Err(MaterialError::UnresolvedEvent("mechanical stop reaction sign"));}evidence.stop_dissipation_j+=work;}
            else{evidence.energy_residual_j+=work;}
            if i<INPUTS{
                let path=input_paths[i];
                evidence.contact_heat_j+=path.resistor_heat;evidence.supply_j+=voltage[i]*path.dq;
                evidence.circuit_tail_charge_c+=path.tail_charge_c;evidence.circuit_tail_work_j+=path.tail_work_j;
            }
        }Ok((b,evidence,input_paths))
    }
}

#[derive(Clone,Copy,Debug)]struct Interval{lo:f64,hi:f64}
fn down(x:f64)->f64{if x==f64::NEG_INFINITY{x}else if x==0.0{-f64::from_bits(1)}else{f64::from_bits(if x>0.0{x.to_bits()-1}else{x.to_bits()+1})}}
fn up(x:f64)->f64{if x==f64::INFINITY{x}else if x==0.0{f64::from_bits(1)}else{f64::from_bits(if x>0.0{x.to_bits()+1}else{x.to_bits()-1})}}
impl Interval{
    fn point(x:f64)->Self{Self{lo:x,hi:x}}
    fn add(self,b:Self)->Self{Self{lo:down(self.lo+b.lo),hi:up(self.hi+b.hi)}}
    fn neg(self)->Self{Self{lo:-self.hi,hi:-self.lo}}
    fn sub(self,b:Self)->Self{self.add(b.neg())}
    fn mul(self,b:Self)->Self{let p=[self.lo*b.lo,self.lo*b.hi,self.hi*b.lo,self.hi*b.hi];Self{lo:down(p.iter().copied().fold(f64::INFINITY,f64::min)),hi:up(p.iter().copied().fold(f64::NEG_INFINITY,f64::max))}}
    fn positive_div(self,b:Self)->Result<Self>{if b.lo<=0.0{return Err(MaterialError::UnresolvedEvent("positive yield denominator enclosure"));}
        let p=[self.lo/b.lo,self.lo/b.hi,self.hi/b.lo,self.hi/b.hi];Ok(Self{lo:down(p.iter().copied().fold(f64::INFINITY,f64::min)),hi:up(p.iter().copied().fold(f64::NEG_INFINITY,f64::max))})}
    fn absmax(self)->f64{self.lo.abs().max(self.hi.abs())}
    fn sin_path(a:f64,b:f64)->Result<Self>{
        finite(a)?;finite(b)?;if a==b{return Ok(Self::point(a.sin()));}
        let lo=a.min(b);let hi=a.max(b);if hi-lo>=std::f64::consts::TAU{return Ok(Self{lo:-1.0,hi:1.0});}
        let mut value=Self{lo:down(a.sin().min(b.sin())).max(-1.0),hi:up(a.sin().max(b.sin())).min(1.0)};
        let k0=((lo-std::f64::consts::FRAC_PI_2)/std::f64::consts::PI).ceil();let k1=((hi-std::f64::consts::FRAC_PI_2)/std::f64::consts::PI).floor();
        if k0.abs()>9_007_199_254_740_992.0||k1.abs()>9_007_199_254_740_992.0{return Err(MaterialError::UnresolvedEvent("phase critical point indexing"));}
        for k in k0 as i64..=k1 as i64{if k%2==0{value.hi=1.0}else{value.lo=-1.0}}Ok(value)
    }
    fn cos_path(a:f64,b:f64)->Result<Self>{Self::sin_path(a+std::f64::consts::FRAC_PI_2,b+std::f64::consts::FRAC_PI_2)}
}
/// Enclose uv-a*v² over the entire admitted phase rectangle. At each fixed
/// v the stress is affine in u, so extrema lie on its two u boundaries. Each
/// boundary is a quadratic in v: only its endpoints and stationary point can
/// be extrema. This retains the repeated v dependency without a path guess.
fn contact_stress_range(v:Interval,u:Interval,gain:f64)->Result<Interval>{
    finite(gain)?;
    if !v.lo.is_finite()||!v.hi.is_finite()||!u.lo.is_finite()||!u.hi.is_finite()||v.lo>v.hi||u.lo>u.hi{
        return Err(MaterialError::UnresolvedEvent("finite contact stress rectangle"));
    }
    let coefficient=Interval::point(gain);
    let evaluate=|x:Interval,y:f64|x.mul(Interval::point(y).sub(coefficient.mul(x)));
    let mut result=Interval{lo:f64::INFINITY,hi:f64::NEG_INFINITY};
    let mut include=|bound:Interval|->Result<()>{
        if !bound.lo.is_finite()||!bound.hi.is_finite()||bound.lo>bound.hi{return Err(MaterialError::UnresolvedEvent("contact stress extremum enclosure"));}
        result.lo=result.lo.min(bound.lo);result.hi=result.hi.max(bound.hi);Ok(())
    };
    for y in [u.lo,u.hi]{
        include(evaluate(Interval::point(v.lo),y))?;include(evaluate(Interval::point(v.hi),y))?;
        if gain!=0.0{
            let denominator=Interval::point(2.0).mul(Interval::point(gain.abs()));
            let mut stationary=Interval::point(y).positive_div(denominator)?;
            if gain<0.0{stationary=stationary.neg();}
            // An outward stationary interval disjoint from the rectangle cannot
            // contain an interior extremum. Otherwise retain its whole overlap.
            if stationary.hi>=v.lo&&stationary.lo<=v.hi{
                include(evaluate(Interval{lo:stationary.lo.max(v.lo),hi:stationary.hi.min(v.hi)},y))?;
            }
        }
    }
    if v.lo<=0.0&&v.hi>=0.0{include(Interval::point(0.0))?;}
    Ok(result)
}

struct PlasticSettlement{changes:Vec<(usize,f64)>,heat_j:f64,numerical_dissipation_j:f64}
impl Functional64Material{
    fn plastic_return(&self,f:&Frontier,a:&LocalVector,b:&LocalVector,count:&mut WorkCount,admission:Admission)->Result<PlasticSettlement>{
        let send=a.nodes.iter().zip(&b.nodes).map(|(p,q)|Interval::sin_path(p.send,q.send)).collect::<Result<Vec<_>>>()?;
        let receive=a.nodes.iter().zip(&b.nodes).map(|(p,q)|Interval::sin_path(p.receive,q.receive)).collect::<Result<Vec<_>>>()?;
        let vmax=send.iter().map(|r|r.absmax()).fold(0.0f64,f64::max);
        count.scratch(add_bytes(f.scratch_base,checked_bytes(f.edges.len(),8*(std::mem::size_of::<u32>()+std::mem::size_of::<(usize,f64)>()))?)?,admission)?;
        let mut candidates=f.edges.iter().filter(|e|e.contact.plastic).map(|e|e.contact.authentic_slot).collect::<Vec<_>>();let mut failure=None;
        for(i,&node)in f.nodes.iter().enumerate(){
            let umax=receive[i].absmax();let bmax=self.anatomy.geometry.incoming_baseline_max(node);
            let bound=up(vmax*up(umax+up(bmax*vmax)));
            if vmax==0.0||bound<=self.anatomy.geometry.minimum_incoming_yield(node){continue;}
            let result=self.anatomy.geometry.visit_incoming(node,|e|{
                if let Err(error)=count.query(1,admission){failure=Some(error);return Err("yield query admission");}
                if !e.plastic||*self.weights.get(e.authentic_slot as usize)!=0.0{return Ok(());}
                let from=f.index[e.from as usize];if from==usize::MAX{return Ok(());}
                let v=send[from];let stress=match contact_stress_range(v,receive[i],self.anatomy.geometry.baseline(e)){
                    Ok(stress)=>stress,Err(error)=>{failure=Some(error);return Err("yield stress enclosure");}
                };
                if stress.absmax()>e.threshold{
                    let bytes=candidates.len().checked_add(1).and_then(|n|n.checked_mul(8*(std::mem::size_of::<u32>()+std::mem::size_of::<(usize,f64)>()))).and_then(|n|n.checked_add(f.scratch_base));
                    match bytes{Some(n)=>{if let Err(error)=count.scratch(n,admission){failure=Some(error);return Err("yield candidate admission");}},None=>{failure=Some(MaterialError::Capacity("yield candidate bytes"));return Err("yield candidate admission");}}
                    candidates.push(e.authentic_slot);
                }Ok(())
            });
            if result.is_err(){return Err(failure.take().unwrap_or(MaterialError::Invalid("incoming yield geometry")));}
        }
        candidates.sort_unstable();candidates.dedup();let mut changes=Vec::new();let mut heat=0.0;let mut numerical=0.0;
        for slot in candidates{
            count.query(1,admission)?;let e=self.anatomy.contact(slot as usize)?;let w=*self.weights.get(slot as usize);let baseline=self.anatomy.geometry.baseline(e);let effective=finite(baseline+w)?;
            let i=f.index[e.from as usize];let j=f.index[e.to as usize];let p=f.pair(a,self,e.from as usize);let q=f.pair(b,self,e.from as usize);
            let r=f.pair(a,self,e.to as usize);let t=f.pair(b,self,e.to as usize);let(s0,s1,r0,r1)=(p.send,q.send,r.receive,t.receive);
            if s0==s1&&r0==r1{continue;}
            let v=if i==usize::MAX{Interval::point(0.0)}else{send[i]};let u=if j==usize::MAX{Interval::point(0.0)}else{receive[j]};
            let stress=contact_stress_range(v,u,effective)?;if stress.absmax()<=e.threshold{continue;}
            let v1=s1.sin();let u1=r1.sin();let x1=v1*(u1-effective*v1);
            let dv=Interval::cos_path(s0,s1)?.mul(Interval::point(s1-s0));let du=Interval::cos_path(r0,r1)?.mul(Interval::point(r1-r0));
            let derivative=dv.mul(u.sub(v.mul(Interval::point(2.0*effective)))).add(v.mul(du));
            if x1.abs()<=e.threshold||(x1>0.0&&derivative.lo<0.0)||(x1<0.0&&derivative.hi>0.0){return Err(MaterialError::UnresolvedEvent("within-step yield reversal or excursion"));}
            if v1==0.0{return Err(MaterialError::UnresolvedEvent("zero yield endpoint phase"));}
            let uv=Interval::point(u1).mul(Interval::point(v1));let vv=Interval::point(v1).mul(Interval::point(v1));
            let low=uv.sub(Interval::point(e.threshold)).positive_div(vv)?.sub(Interval::point(baseline)).hi;
            let high=uv.add(Interval::point(e.threshold)).positive_div(vv)?.sub(Interval::point(baseline)).lo;
            if low>high{return Err(MaterialError::UnresolvedEvent("no enclosed representable elastic contact"));}
            let next=if x1>0.0{low}else{high};finite(next)?;let dw=next-w;let next_gain=finite(baseline+next)?;
            if dw==0.0||dw.signum()!=x1.signum()||finite(v1*(u1-next_gain*v1))?.abs()>e.threshold{return Err(MaterialError::UnresolvedEvent("yield return resolution"));}
            let old_residual=u1-effective*v1;let next_residual=u1-next_gain*v1;let lambda=self.anatomy.lambda(e);
            let released=0.5*lambda*(old_residual-next_residual)*(old_residual+next_residual);
            let dissipated=lambda*e.threshold*dw.abs();let return_loss=released-dissipated;
            if return_loss<0.0{return Err(MaterialError::UnresolvedEvent("return work enclosure"));}
            nonnegative(released)?;nonnegative(dissipated)?;nonnegative(return_loss)?;
            heat+=dissipated;numerical+=return_loss;changes.push((slot as usize,next));
        }Ok(PlasticSettlement{changes,heat_j:finite(heat)?,numerical_dissipation_j:finite(numerical)?})
    }
}

// Positive constant-aperture circuit operator INSIDE the coupled material trial.
// It has no independent clock, reserve or publication authority.
struct CircuitStep{
    gate:Gate,source_j:f64,resistor_j:f64,exported_j:f64,load_c:f64,
    tail_charge_c:f64,tail_work_j:f64,projection_defect_v:f64,
}
struct PositiveEvolution<const N:usize>{
    integral:[f64;N],endpoint:[f64;N],endpoint_tail:f64,integral_tail:f64,
}
fn circuit_series_limit()->usize{let gmax=aperture(1.0);let nu=2.0*(gmax*(1.0/CM+1.0/CR)).max(G/CR).max(G/CM);(2.0*nu*0.001).ceil()as usize+2*f64::MANTISSA_DIGITS as usize+3}
/// Positive uniformization of the actually reached finite Metzler generator.
/// A priori terms: ceil(2*z)+2*binary64_mantissa_bits+2. After ceil(2*z),
/// successive Poisson terms have ratio<=1/2. Omitted tails remain numerical
/// error; they are never added to source heat or any physical energy store.
fn positive_evolution<const N:usize>(rates:[[f64;N];N],old:[f64;N],h:f64,
    count:&mut WorkCount,admission:Admission)->Result<PositiveEvolution<N>>{
    if h<=0.0||!h.is_finite()||old.iter().any(|v|!v.is_finite()||*v<0.0){return Err(MaterialError::Invalid("positive circuit input"));}
    for j in 0..N{
        if rates[j][j]>0.0||!rates[j][j].is_finite(){return Err(MaterialError::Invalid("nonpassive circuit diagonal"));}
        for i in 0..N{if i!=j&&(rates[i][j]<0.0||!rates[i][j].is_finite()){return Err(MaterialError::Invalid("non-Metzler circuit"));}}
    }
    // Exact structural reachability removes no nonzero state and uses no
    // tolerance. A disconnected zero capacitor cannot make idle work stiff.
    let mut reached=old.map(|x|x!=0.0);let mut changed=true;
    while changed{changed=false;for j in 0..N{if reached[j]{for i in 0..N{if rates[i][j]>0.0&&!reached[i]{reached[i]=true;changed=true;}}}}}
    let mut nu=0.0f64;for j in 0..N{if reached[j]{nu=nu.max(-rates[j][j]);}}
    if nu==0.0{return Ok(PositiveEvolution{endpoint:old,integral:old.map(|x|x*h),endpoint_tail:0.0,integral_tail:0.0});}
    let z=finite(nu*h)?;
    let gmax=aperture(1.0);let numax=2.0*(gmax*(1.0/CM+1.0/CR)).max(G/CR).max(G/CM);
    if z>numax*0.001{return Err(MaterialError::Invalid("circuit interval or material bound"));}
    let limit=(2.0*z).ceil()as usize+2*f64::MANTISSA_DIGITS as usize+2;
    // Preflight the complete series work before allocating or evaluating it.
    let upper_work=(limit+1).checked_mul(N*N+3*N).ok_or(MaterialError::Capacity("circuit operation count"))?;
    count.preflight_force(upper_work,admission)?;
    let mut transition=[[0.0;N];N];
    for i in 0..N{for j in 0..N{if reached[j]{transition[i][j]=rates[i][j]/nu+if i==j{1.0}else{0.0};nonnegative(transition[i][j])?;}}}
    let mut probabilities=Vec::with_capacity(limit+1);probabilities.push((-z).exp());
    if probabilities[0]==0.0{return Err(MaterialError::UnresolvedEvent("circuit series origin underflow"));}
    let mut tail=f64::INFINITY;
    for n in 0..limit{
        let next=probabilities[n]*z/(n+1)as f64;let ratio=z/(n+2)as f64;
        if ratio<1.0{tail=next/(1.0-ratio);if tail<=f64::EPSILON*f64::EPSILON{break;}}
        probabilities.push(next);
    }
    if tail>f64::EPSILON*f64::EPSILON{return Err(MaterialError::UnresolvedEvent("finite circuit exponential tail"));}
    count.force(probabilities.len()*(N*N+3*N),admission)?;
    let terms=probabilities.len();let mut integral_weights=vec![0.0;terms];let mut suffix=0.0;
    for k in(0..terms).rev(){integral_weights[k]=suffix/nu;suffix+=probabilities[k];}
    let mut endpoint=[0.0;N];let mut integral=[0.0;N];let mut vector=old;
    for k in 0..terms{
        for i in 0..N{endpoint[i]+=probabilities[k]*vector[i];integral[i]+=integral_weights[k]*vector[i];}
        if k+1<terms{let mut next=[0.0;N];for i in 0..N{for j in 0..N{next[i]+=transition[i][j]*vector[j];}}vector=next;}
    }
    if endpoint.iter().chain(integral.iter()).any(|x|!x.is_finite()||*x<0.0){return Err(MaterialError::Arithmetic("circuit series overflow"));}
    // Exact-series tail only. Floating arithmetic and moving-aperture error
    // remain the separately reported finite residual/doubling estimate.
    let mass:f64=old.iter().sum();
    Ok(PositiveEvolution{endpoint,integral,endpoint_tail:tail*mass,integral_tail:tail*mass*terms as f64/nu})
}
// The existing Charge lattice stores every bit of an admitted binary64
// operand product when its lowest possible product bit is no lower than
//2^-1074. Check that domain before using product plus its fused residual.
fn equilibrium_charge(capacitance:f64,voltage:f64)->Result<Charge>{
    nonnegative(capacitance)?;nonnegative(voltage)?;
    if capacitance!=0.0&&voltage!=0.0{
        let lattice_exponent=|value:f64|{let e=((value.to_bits()>>52)&2047)as i32;if e==0{-1074}else{e-1075}};
        if lattice_exponent(capacitance)+lattice_exponent(voltage)< -1074{
            return Err(MaterialError::Arithmetic("equilibrium product below exact charge lattice"));
        }
    }
    let product=finite(capacitance*voltage)?;let residual=capacitance.mul_add(voltage,-product);
    Charge::packet(product).and_then(|q|q.add_packet(residual))
        .map_err(|_|MaterialError::Arithmetic("exact equilibrium charge"))
}
// This is a storage/refusal ceiling derived from the admitted geometry,
// never a returned fixed-degree truncation. Actual tails must pass first.
const INPUT_PATH_DEGREE:usize=2*f64::MANTISSA_DIGITS as usize+2;
#[derive(Clone,Copy,Default)]
struct InputPathStep{dq:f64,resistor_heat:f64,cap_reaction:f64,tail_charge_c:f64,tail_work_j:f64}
#[derive(Default)]struct SignedMoment{sum:f64,correction:f64}
impl SignedMoment{
    fn add(&mut self,value:f64)->Result<()>{
        finite(value)?;let next=finite(self.sum+value)?;
        let residue=if self.sum.abs()>=value.abs(){(self.sum-next)+value}else{(value-next)+self.sum};
        self.correction=finite(self.correction+residue)?;self.sum=next;Ok(())
    }
    fn value(&self)->Result<f64>{finite(self.sum+self.correction)}
}
fn input_path_scratch_bytes()->Result<usize>{
    [checked_bytes(3,std::mem::size_of::<SignedMoment>())?,checked_bytes(2,std::mem::size_of::<InputPathStep>())?,
        checked_bytes(6,std::mem::size_of::<Charge>())?,checked_bytes(8,std::mem::size_of::<f64>())?]
        .into_iter().try_fold(checked_bytes(INPUT_PATH_DEGREE+1,std::mem::size_of::<f64>())?,add_bytes)
}
// Preserve the exact affine equilibrium before subtracting a nearby retained
// charge. C0 itself is only the positive denominator projection, not custody.
fn input_affine_equilibrium(y:f64,voltage:f64,count:&mut WorkCount,admission:Admission)->Result<(f64,Charge)>{
    if !y.is_finite()||!(0.0..=1.0).contains(&y){return Err(MaterialError::Invalid("input aperture outside mechanical stops"));}
    nonnegative(voltage)?;
    if y!=0.0{
        let lattice_exponent=|value:f64|{let e=((value.to_bits()>>52)&2047)as i32;if e==0{-1074}else{e-1075}};
        if lattice_exponent(CR)+lattice_exponent(y)< -1074{
            return Err(MaterialError::Arithmetic("affine capacitance product below exact lattice"));
        }
    }
    // One product/FMA decomposition, then three product/FMA charge pairs.
    count.force(8,admission)?;
    let variable=finite(CR*y)?;let residue=finite(CR.mul_add(y,-variable))?;
    let base=equilibrium_charge(CM,voltage)?;
    let variable_charge=equilibrium_charge(variable,voltage)?;
    let mut residual_charge=equilibrium_charge(residue.abs(),voltage)?;
    if residue<0.0{residual_charge=residual_charge.neg();}
    let exact=base.add(variable_charge).and_then(|q|q.add(residual_charge))
        .map_err(|_|MaterialError::Arithmetic("exact affine equilibrium charge"))?;
    Ok((finite(CM+variable)?,exact))
}
fn input_gate_path_step(q0:Charge,y0:f64,y1:f64,voltage:f64,h:f64,count:&mut WorkCount,admission:Admission)->Result<InputPathStep>{
    if !y1.is_finite()||!(0.0..=1.0).contains(&y1){return Err(MaterialError::Invalid("input aperture outside mechanical stops"));}
    let(c0,equilibrium)=input_affine_equilibrium(y0,voltage,count,admission)?;
    let deficit=equilibrium.add(q0.neg()).map_err(|_|MaterialError::Arithmetic("input affine exact headroom"))?;
    // Subtract the actual aperture endpoints before introducing the large CM
    // baseline. This retains the physical CR*dy slope without C1-C0 loss.
    count.force(1,admission)?;let delta_c=finite(CR*(y1-y0))?;
    input_path_series(q0,c0,delta_c,deficit,voltage,h,count,admission)
}
// Arbitrary endpoint capacitances belong only to the pre-existing component
// references. The production path above has one actual affine anatomy owner.
#[cfg(test)]
fn input_path_step(q0:Charge,c0:f64,c1:f64,voltage:f64,h:f64,count:&mut WorkCount,admission:Admission)->Result<InputPathStep>{
    if !c0.is_finite()||!c1.is_finite()||c0<CM||c1<CM||c0>CM+CR||c1>CM+CR{
        return Err(MaterialError::Invalid("input path material domain"));
    }
    nonnegative(voltage)?;
    let deficit=equilibrium_charge(c0,voltage)?.add(q0.neg()).map_err(|_|MaterialError::Arithmetic("input path exact headroom"))?;
    input_path_series(q0,c0,finite(c1-c0)?,deficit,voltage,h,count,admission)
}
fn input_path_series(q0:Charge,c0:f64,delta_c:f64,deficit:Charge,voltage:f64,h:f64,count:&mut WorkCount,admission:Admission)->Result<InputPathStep>{
    if !c0.is_finite()||c0<CM||c0>CM+CR||!delta_c.is_finite()
        ||!h.is_finite()||h<=0.0||h>0.001||q0.negative{
        return Err(MaterialError::Invalid("input path material domain"));
    }
    nonnegative(voltage)?;
    let r0=finite(deficit.projection().map_err(|_|MaterialError::Arithmetic("input path headroom projection"))?/c0)?;
    let v0=nonnegative(q0.projection().map_err(|_|MaterialError::Arithmetic("input path charge projection"))?/c0)?;
    let z=finite(delta_c/c0)?;let a=nonnegative(G*h/c0)?;
    let r1=finite(z*v0-a*r0)?;
    let gap_scale=r0.abs().max(r1.abs());let voltage_scale=v0.abs().max(r1.abs());
    if gap_scale==0.0&&voltage_scale==0.0{return Ok(InputPathStep::default());}
    let eps2=f64::EPSILON*f64::EPSILON;
    let first_budget=if gap_scale==0.0{0.0}else{down(eps2*gap_scale)};
    let gap_budget=if gap_scale==0.0{0.0}else{down(eps2*down(gap_scale*gap_scale))};
    let voltage_budget=if voltage_scale==0.0{0.0}else{down(eps2*down(voltage_scale*voltage_scale))};
    let add_up=|x:f64,y:f64|if x==0.0{y}else if y==0.0{x}else{up(x+y)};
    let mul_up=|x:f64,y:f64|if x==0.0||y==0.0{0.0}else{up(x*y)};
    let div_up=|x:f64,y:f64|if x==0.0{0.0}else{up(x/y)};
    let mut coefficients=[0.0;INPUT_PATH_DEGREE+1];coefficients[0]=r0;coefficients[1]=r1;
    count.force(2,admission)?;
    let mut absolute_gap=add_up(r0.abs(),r1.abs());let mut absolute_voltage=add_up(v0.abs(),r1.abs());
    let mut degree=1usize;let tails;
    loop{
        count.force(1,admission)?;
        let factor=finite(z+a/(degree+1)as f64)?;let next=finite(-factor*coefficients[degree])?;
        if next==0.0&&factor!=0.0&&coefficients[degree]!=0.0{return Err(MaterialError::UnresolvedEvent("input path coefficient underflow"));}
        let rho=add_up(z.abs(),div_up(a,(degree+2)as f64));
        if rho>=1.0{return Err(MaterialError::UnresolvedEvent("input path geometric tail ratio"));}
        let next_bound=if next==0.0{0.0}else{up(next.abs())};
        let t=div_up(next_bound,down(1.0-rho));let first=div_up(t,(degree+2)as f64);
        let square_tail=|absolute:f64|{
            add_up(div_up(mul_up(mul_up(2.0,t),absolute),(degree+2)as f64),
                div_up(mul_up(t,t),(2*degree+3)as f64))
        };
        let gap=square_tail(absolute_gap);let capacitor=square_tail(absolute_voltage);
        if first.is_finite()&&gap.is_finite()&&capacitor.is_finite()
            &&first<=first_budget&&gap<=gap_budget&&capacitor<=voltage_budget{
            tails=(first,gap,capacitor);break;
        }
        if degree==INPUT_PATH_DEGREE{return Err(MaterialError::UnresolvedEvent("input path finite tail budget"));}
        degree+=1;coefficients[degree]=next;
        absolute_gap=add_up(absolute_gap,next.abs());absolute_voltage=add_up(absolute_voltage,next.abs());
    }
    let terms=degree+1;
    let products=terms.checked_mul(terms+1).and_then(|n|n.checked_add(terms)).ok_or(MaterialError::Capacity("input path product count"))?;
    count.preflight_force(products,admission)?;
    let mut first=SignedMoment::default();let mut gap_square=SignedMoment::default();let mut voltage_square=SignedMoment::default();
    for i in 0..terms{
        count.force(1,admission)?;first.add(coefficients[i]/(i+1)as f64)?;
        for j in i..terms{
            count.force(2,admission)?;let factor=if i==j{1.0}else{2.0};let divisor=(i+j+1)as f64;
            gap_square.add((coefficients[i]*coefficients[j])*(factor/divisor))?;
            let vi=if i==0{v0}else{-coefficients[i]};let vj=if j==0{v0}else{-coefficients[j]};
            voltage_square.add((vi*vj)*(factor/divisor))?;
        }
    }
    let integral=first.value()?;let gap=gap_square.value()?;let capacitor=voltage_square.value()?;
    if gap<0.0||capacitor<0.0{return Err(MaterialError::UnresolvedEvent("input path squared integral sign"));}
    let dq=finite(G*h*integral)?;let resistor_heat=nonnegative(G*h*gap)?;let cap_reaction=finite(-0.5*CR*capacitor)?;
    let gh=mul_up(G,h);let tail_charge_c=div_up(mul_up(gh,tails.0),1.0);
    // Includes source, resistor and maximum |dy|<=1 generalized gate work.
    let tail_work_j=add_up(mul_up(gh,add_up(tails.1,mul_up(voltage.abs(),tails.0))),mul_up(0.5*CR,tails.2));
    nonnegative(tail_charge_c)?;nonnegative(tail_work_j)?;
    Ok(InputPathStep{dq,resistor_heat,cap_reaction,tail_charge_c,tail_work_j})
}
// Subtract retained charge before projecting the small source headroom.
// No rounded equilibrium charge or second state variable is stored.
fn source_voltage_headroom(qm:Charge)->Result<f64>{
    let difference=equilibrium_charge(CM,VS)?.add(qm.neg())
        .map_err(|_|MaterialError::Arithmetic("exact source charge headroom"))?;
    finite(difference.projection().map_err(|_|MaterialError::Arithmetic("source headroom projection"))?/CM)
}
fn output_circuit(old:Gate,y:f64,h:f64,powered:bool,count:&mut WorkCount,admission:Admission)->Result<CircuitStep>{
    if !y.is_finite()||!(0.0..=1.0).contains(&y){return Err(MaterialError::Invalid("output aperture outside mechanical stops"));}
    let qm=old.qm.projection().map_err(|_|MaterialError::Arithmetic("output membrane charge"))?;
    let qr=old.qr.projection().map_err(|_|MaterialError::Arithmetic("output receiver charge"))?;
    let vm=qm/CM;let vr=qr/CR;let initial=[vm-vr,vr,source_voltage_headroom(old.qm)?];
    if initial.iter().any(|x|!x.is_finite()||*x<0.0){return Err(MaterialError::UnresolvedEvent("output voltage-order enclosure"));}
    let gg=aperture(y);let gs=if powered{G}else{0.0};let gl=G;
    let rates=[[-gg*(1.0/CM+1.0/CR),gl/CR,gs/CM],[gg/CR,-gl/CR,0.0],[gg/CM,0.0,-gs/CM]];
    let first=positive_evolution(rates,initial,h,count,admission)?;
    let mut quadratic=[[0.0;9];9];let mut products=[0.0;9];
    for i in 0..3{for j in 0..3{
        products[3*i+j]=initial[i]*initial[j];
        for k in 0..3{quadratic[3*i+j][3*k+j]+=rates[i][k];quadratic[3*i+j][3*i+k]+=rates[j][k];}
    }}
    let second=positive_evolution(quadratic,products,h,count,admission)?;
    let source_c=nonnegative(gs*first.integral[2])?;let gate_c=nonnegative(gg*first.integral[0])?;let load_c=nonnegative(gl*first.integral[1])?;
    let next_qm=old.qm.add_packet(source_c).and_then(|q|q.add_packet(-gate_c)).map_err(|_|MaterialError::Arithmetic("exact membrane charge settlement"))?;
    let next_qr=old.qr.add_packet(gate_c).and_then(|q|q.add_packet(-load_c)).map_err(|_|MaterialError::Arithmetic("exact receiving charge settlement"))?;
    if next_qm.negative||next_qr.negative{return Err(MaterialError::UnresolvedEvent("positive capacitor current enclosure"));}
    let mut gate=old;gate.y=y;gate.qm=next_qm;gate.qr=next_qr;
    let next_vm=next_qm.projection().map_err(|_|MaterialError::Arithmetic("next membrane projection"))?/CM;
    let next_vr=next_qr.projection().map_err(|_|MaterialError::Arithmetic("next receiver projection"))?/CR;
    if next_vr>next_vm||next_vm>VS{return Err(MaterialError::UnresolvedEvent("positive circuit endpoint enclosure"));}
    let resistor_j=nonnegative(gs*second.integral[8]+gg*second.integral[0])?;let exported_j=nonnegative(gl*second.integral[4])?;
    let source_j=nonnegative(VS*source_c)?;
    let projection_defect_v=(next_vm-(first.endpoint[0]+first.endpoint[1])).abs()+(next_vr-first.endpoint[1]).abs()+first.endpoint_tail;
    Ok(CircuitStep{gate,source_j,resistor_j,exported_j,load_c,
        tail_charge_c:(gs+gg+gl)*first.integral_tail,tail_work_j:(gs+gg+gl)*second.integral_tail,projection_defect_v})
}

struct SupplyPreparation{successor:Functional64Material,offset:PoweredOffset,thermal_work:Vec<PaidThermalWork>,debited:Work}
impl Functional64Material{
    fn prepare_supply(mut self)->Result<SupplyPreparation>{
        let regulator=Work::output_regulator_interval(G,VS).map_err(MaterialError::Arithmetic)?;
        let mut interval=regulator.mul(TERMINALS as u64).map_err(MaterialError::Arithmetic)?;
        for p in &self.power{if p.packet.origin==PowerOrigin::BodyReserve{
            interval=interval.add(Work::packet_interval(p.packet.admitted_j,1).map_err(MaterialError::Arithmetic)?).map_err(MaterialError::Arithmetic)?;
        }}
        let mut thermal=Vec::with_capacity(self.anatomy.thermal_loads.len());
        for load in self.anatomy.thermal_loads.iter(){let share=Work::thermal_interval(load.microwatts).map_err(MaterialError::Arithmetic)?;
            if !share.low_zero(work_store::CUT_BITS){return Err(MaterialError::Invalid("thermal anatomy has no exact common event grid"));}
            interval=interval.add(share).map_err(MaterialError::Arithmetic)?;thermal.push((load.identity.clone(),share));
        }
        let ticks=self.total_work()?.affordable_ticks(interval).map_err(MaterialError::Arithmetic)?;
        let debited=interval.slice(ticks).map_err(MaterialError::Arithmetic)?;self.debit_work(debited)?;
        let thermal_work=thermal.into_iter().map(|(identity,w)|w.slice(ticks).map(|v|PaidThermalWork{identity,units:v.limbs}).map_err(MaterialError::Arithmetic)).collect::<Result<Vec<_>>>()?;
        Ok(SupplyPreparation{successor:self,offset:PoweredOffset{ticks,fractional_bits:52},thermal_work,debited})
    }
    fn total_work(&self)->Result<Work>{self.work.add(Work::nutrition(self.reserve_ug).map_err(MaterialError::Arithmetic)?).map_err(MaterialError::Arithmetic)}
    fn debit_work(&mut self,amount:Work)->Result<()>{
        if !self.total_work()?.gte(amount){return Err(MaterialError::Arithmetic("unfunded source debit"));}
        if !self.work.gte(amount){let gap=amount.sub(self.work).map_err(MaterialError::Arithmetic)?;let(mut lo,mut hi)=(1,self.reserve_ug);
            while lo<hi{let m=lo+(hi-lo)/2;if Work::nutrition(m).map_err(MaterialError::Arithmetic)?.gte(gap){hi=m}else{lo=m+1;}}
            self.work=self.work.add(Work::nutrition(lo).map_err(MaterialError::Arithmetic)?).map_err(MaterialError::Arithmetic)?;self.reserve_ug-=lo;
        }
        self.work=self.work.sub(amount).map_err(MaterialError::Arithmetic)?;Ok(())
    }
    fn pay_finite_work(&mut self,joules:f64)->Result<bool>{let amount=Work::finite_joules(joules).map_err(MaterialError::Arithmetic)?;if !self.total_work()?.gte(amount){return Ok(false);}self.debit_work(amount)?;Ok(true)}
    fn recover_finite_work(&mut self,joules:f64)->Result<()>{self.work=self.work.add(Work::finite_joules(joules).map_err(MaterialError::Arithmetic)?).map_err(MaterialError::Arithmetic)?;Ok(())}
    pub(crate) fn source_anatomy(&self)->Arc<Anatomy>{self.anatomy.clone()}
    /// Consume only an unpublished successor; no second encoded current reserve.
    pub(crate) fn prepare_assimilation(mut self,available_digestible_ug:u64)->Result<PreparedAssimilation>{
        let headroom=self.anatomy.reserve_capacity_ug.checked_sub(self.reserve_ug).ok_or(MaterialError::Invalid("retained reserve exceeds authenticated capacity"))?;
        let assimilated_ug=headroom.min(available_digestible_ug);self.reserve_ug+=assimilated_ug;
        self.total_work()?;
        Ok(PreparedAssimilation{successor:self,assimilated_ug,remaining_digestible_ug:available_digestible_ug-assimilated_ug})
    }
}

struct MaterialDrive{voltage:Vec<f64>,budget:Vec<Work>,output_budget:Work,reserve_powered:bool}
// Owned only within one adaptive span's identical coarse/first-half start.
// Borrowed operands cannot outlive or silently change the predecessor/drive.
struct CommonStart<'a>{
    predecessor:&'a Functional64Material,drive:&'a MaterialDrive,
    frontier:Frontier,before:LocalVector,
    initial_gradient:Option<Gradient>,initial_energy:Option<(f64,contact_operator::Energy)>,
}
impl<'a> CommonStart<'a>{
    fn new(predecessor:&'a Functional64Material,drive:&'a MaterialDrive,count:&mut WorkCount,admission:Admission)->Result<Self>{
        let frontier=Frontier::new(predecessor,&drive.voltage,count,admission)?;let before=frontier.view(predecessor)?;
        Ok(Self{predecessor,drive,frontier,before,initial_gradient:None,initial_energy:None})
    }
    fn retained_gradient_bytes(f:&Frontier,gates:usize)->Result<usize>{
        [checked_bytes(f.nodes.len(),std::mem::size_of::<PhasePair>())?,
            checked_bytes(f.rings.len(),std::mem::size_of::<[f64;3]>())?,
            checked_bytes(gates,std::mem::size_of::<f64>())?]
            .into_iter().try_fold(std::mem::size_of::<Self>(),add_bytes)
    }
    fn trial(&mut self,ticks:u64,count:&mut WorkCount,admission:Admission)->Result<TrialStep>{
        let predecessor=self.predecessor;
        match predecessor.settle_trial_with_start(self,ticks,true,count,admission)?{
            SettledTrial::Complete(step)=>Ok(step),
            SettledTrial::Comparison(_)=>Err(MaterialError::Invalid("complete trial receipt")),
        }
    }
    fn comparison_trial(&mut self,ticks:u64,count:&mut WorkCount,admission:Admission)->Result<ComparisonStep>{
        let predecessor=self.predecessor;
        match predecessor.settle_trial_with_start(self,ticks,false,count,admission)?{
            SettledTrial::Comparison(step)=>Ok(step),
            SettledTrial::Complete(_)=>Err(MaterialError::Invalid("comparison trial receipt")),
        }
    }
}
struct TrialStep{state:Functional64Material,emitted:[u64;TERMINALS],evidence:WorkEvidence,supplied:Work,transducer_heat:Work}
// A discarded coarse successor has no reported endpoint-energy receipt.
// Its actual transport and four existing comparison observations remain owned.
struct ComparisonStep{state:Functional64Material,emitted:[u64;TERMINALS],caloric:[f64;4],supplied:Work,transducer_heat:Work}
impl ComparisonStep{
    fn from_complete(step:TrialStep)->Self{
        Self{state:step.state,emitted:step.emitted,
            caloric:[step.evidence.supply_j,step.evidence.exported_j,step.evidence.contact_heat_j,step.evidence.plastic_heat_j],
            supplied:step.supplied,transducer_heat:step.transducer_heat}
    }
}
enum SettledTrial{Complete(TrialStep),Comparison(ComparisonStep)}
fn physical_duration(ticks:u64)->Result<f64>{
    if ticks==0||ticks>work_store::FULL_TICKS{return Err(MaterialError::Invalid("material event-grid span"));}
    Ok(ticks as f64/(1000.0*work_store::FULL_TICKS as f64))
}
fn transducer_heat(supplied:Work,electrical_j:f64)->Result<Work>{
    finite(electrical_j)?;let work=Work::finite_joules(electrical_j.abs()).map_err(MaterialError::Arithmetic)?;
    if electrical_j>=0.0{if !supplied.gte(work){return Err(MaterialError::UnresolvedEvent("source transducer work enclosure"));}supplied.sub(work).map_err(MaterialError::Arithmetic)}
    else{supplied.add(work).map_err(MaterialError::Arithmetic)}
}
impl Functional64Material{
    fn local_energy(&self,f:&Frontier,v:&LocalVector,new_contacts:&[(usize,f64)],count:&mut WorkCount,admission:Admission)->Result<(f64,contact_operator::Energy)>{
        let contact=contact_operator::energy(self,f,v,new_contacts,count,admission)?;let mut energy=contact.value;
        for p in &v.nodes{let u=p.receive.sin();let s=p.send.sin();energy+=0.5*LAMBDA*(u-s)*(u-s);}
        for(i,&site)in f.rings.iter().enumerate(){
            let tau=self.facts[site].digit as f64*std::f64::consts::TAU/3.0;
            for(j,k)in[LAMBDA,LAMBDA,LAMBDA/std::f64::consts::SQRT_2].iter().enumerate(){energy+=k*(1.0-(v.rings[i][(j+1)%3]-v.rings[i][j]-tau).cos());}
            energy+=LAMBDA*(1.0-(v.rings[i][0]-v.nodes[f.index[Anatomy::fact_node(site)]].receive).cos());
        }
        for(i,g)in v.gates.iter().enumerate(){
            let node=if i<INPUTS{self.anatomy.input_nodes[i]as usize}else{Anatomy::terminal_node(i-INPUTS)};
            let p=f.pair(v,self,node);let e=g.y-REST-ALPHA*(p.receive.sin()-p.send.sin());energy+=0.5*K*e*e;
            if i<INPUTS{energy+=0.5*g.q*g.q/(CM+CR*g.y);}else{energy+=0.5*(g.qm*g.qm/CM+g.qr*g.qr/CR);}
        }Ok((finite(energy)?,contact))
    }
    fn trial(&self,ticks:u64,drive:&MaterialDrive,count:&mut WorkCount,admission:Admission)->Result<TrialStep>{
        physical_duration(ticks)?;
        CommonStart::new(self,drive,count,admission)?.trial(ticks,count,admission)
    }
    fn settle_trial_with_start(&self,start:&mut CommonStart<'_>,ticks:u64,complete_receipt:bool,count:&mut WorkCount,admission:Admission)->Result<SettledTrial>{
        let h=physical_duration(ticks)?;let drive=start.drive;
        let(mut after,mut evidence,input_paths)=self.solve_elastic(&mut start.frontier,&start.before,&drive.voltage,h,&mut start.initial_gradient,count,admission)?;
        let f=&start.frontier;let before=&start.before;
        let initial_energy=if complete_receipt{Some(match start.initial_energy{
            Some(energy)=>energy,
            None=>{let energy=self.local_energy(f,before,&[],count,admission)?;start.initial_energy=Some(energy);energy}
        })}else{None};
        let plastic=self.plastic_return(&f,&before,&after,count,admission)?;
        let mut next=self.clone();let mut gates=(*self.gates).clone();let mut emitted=[0u64;TERMINALS];
        let mut supplied=Work::ZERO;let mut heat=Work::ZERO;
        for i in 0..INPUTS{
            let dq=input_paths[i].dq;
            let charge=gates[i].q.add_packet(dq).map_err(|_|MaterialError::Arithmetic("input exact current custody"))?;
            if charge.negative{return Err(MaterialError::UnresolvedEvent("input capacitor charge enclosure"));}
            gates[i].y=after.gates[i].y;gates[i].q=charge;after.gates[i]=NumericalGate::project(gates[i])?;
            let source=drive.budget[i].slice(ticks).map_err(MaterialError::Arithmetic)?;
            heat=heat.add(transducer_heat(source,drive.voltage[i]*dq)?).map_err(MaterialError::Arithmetic)?;
            supplied=supplied.add(source).map_err(MaterialError::Arithmetic)?;
        }
        for terminal in 0..TERMINALS{
            let i=INPUTS+terminal;let y=0.5*(before.gates[i].y+after.gates[i].y);
            let mut step=output_circuit(gates[i],y,h,drive.reserve_powered,count,admission)?;step.gate.y=after.gates[i].y;
            let(carriers,remainder)=gates[i].load.prepare(step.load_c,1).map_err(|_|MaterialError::Arithmetic("terminal exact carrier custody"))?;
            if carriers<0{return Err(MaterialError::Arithmetic("load cannot emit opposite terminal"));}
            emitted[terminal]=u64::try_from(carriers).map_err(|_|MaterialError::Arithmetic("terminal output width"))?;
            step.gate.load=remainder;gates[i]=step.gate;after.gates[i]=NumericalGate::project(step.gate)?;
            evidence.supply_j+=step.source_j;evidence.contact_heat_j+=step.resistor_j;evidence.exported_j+=step.exported_j;
            evidence.circuit_tail_charge_c+=step.tail_charge_c;evidence.circuit_tail_work_j+=step.tail_work_j;
            evidence.circuit_projection_defect_v=evidence.circuit_projection_defect_v.max(step.projection_defect_v);
            let source=if drive.reserve_powered{drive.output_budget.slice(ticks).map_err(MaterialError::Arithmetic)?}else{Work::ZERO};
            supplied=supplied.add(source).map_err(MaterialError::Arithmetic)?;
            heat=heat.add(transducer_heat(source,step.source_j)?).map_err(MaterialError::Arithmetic)?;
        }
        for(i,&node)in f.nodes.iter().enumerate(){let p=after.nodes[i];next.phases.set(node,p)?;let reached=Arc::make_mut(&mut next.nonzero_nodes);
            if p.send!=0.0||p.receive!=0.0{reached.insert(node as u16);}else{reached.remove(&(node as u16));}}
        for(i,&site)in f.rings.iter().enumerate(){next.rings.set(site,Ring{phase:after.rings[i]})?;}
        next.gates=Arc::new(gates);next.change_weights(&plastic.changes,count,admission)?;
        evidence.plastic_heat_j=plastic.heat_j;evidence.return_map_dissipation_j=plastic.numerical_dissipation_j;
        if let Some((energy0,contact0))=initial_energy{
            let(energy1,contact1)=next.local_energy(&f,&after,&plastic.changes,count,admission)?;
            evidence.contact_energy_change_j=finite(contact1.value-contact0.value)?;
            evidence.contact_energy_change_lower_j=finite(down(contact1.range.lo-contact0.range.hi))?;
            evidence.contact_energy_change_upper_j=finite(up(contact1.range.hi-contact0.range.lo))?;
            evidence.energy_residual_j=finite(energy1-energy0+evidence.phase_heat_j+evidence.gate_heat_j+
                evidence.stop_dissipation_j+evidence.contact_heat_j+evidence.exported_j+evidence.plastic_heat_j+
                evidence.return_map_dissipation_j-evidence.supply_j)?;
        }
        evidence.source_heat_j=heat.projection_joules().map_err(MaterialError::Arithmetic)?;
        // Remaining means scheduled release, never a second body fuel store.
        // An unfunded BodyReserve slice expires as an offer, not as paid heat.
        for p in &mut next.power{let interval=Work::packet_interval(p.packet.admitted_j,p.release_ms).map_err(MaterialError::Arithmetic)?;
            p.remaining=p.remaining.sub(interval.slice(ticks).map_err(MaterialError::Arithmetic)?).map_err(MaterialError::Arithmetic)?;
        }
        if complete_receipt{Ok(SettledTrial::Complete(TrialStep{state:next,emitted,evidence,supplied,transducer_heat:heat}))}
        else{Ok(SettledTrial::Comparison(ComparisonStep{state:next,emitted,
            caloric:[evidence.supply_j,evidence.exported_j,evidence.contact_heat_j,evidence.plastic_heat_j],supplied,transducer_heat:heat}))}
    }
    fn causal_difference(&self,other:&Self)->Result<AdaptiveComparison>{
        let mut error=0.0f64;
        // nonzero_nodes is derived from these smooth phase coordinates, not an
        // independent event. Keep the accepted fine index exactly; compare its
        // physical coordinates below using the unchanged numerical tolerance.
        let mut causal_mismatch=None;
        self.phases.different_pages(&other.phases,|_,a,b|{error=error.max((a.send-b.send).abs()).max((a.receive-b.receive).abs());});
        self.rings.different_pages(&other.rings,|_,a,b|{for j in 0..3{error=error.max((a.phase[j]-b.phase[j]).abs());}});
        for(a,b)in self.gates.iter().zip(other.gates.iter()){
            error=error.max((a.y-b.y).abs());
            for(q,r)in[(a.q,b.q),(a.qm,b.qm),(a.qr,b.qr)]{
                let delta=q.add(r.neg()).map_err(|_|MaterialError::Arithmetic("adaptive exact charge difference"))?;
                let numerator=delta.projection().map_err(|_|MaterialError::Arithmetic("adaptive charge difference projection"))?.abs();
                let q_proj=q.projection().map_err(|_|MaterialError::Arithmetic("adaptive charge projection"))?.abs();
                let r_proj=r.projection().map_err(|_|MaterialError::Arithmetic("adaptive charge projection"))?.abs();
                let scale=q_proj.max(r_proj).max(material::ELEMENTARY_CHARGE_C);
                error=error.max(numerator/scale);
            }
        }
        let mut invalid_gain=false;
        self.weights.different_pages(&other.weights,|slot,a,b|{
            let scale=1.0f64.max(a.abs()).max(b.abs());error=error.max((a-b).abs()/scale);
            if (*a==0.0)!=(*b==0.0)&&causal_mismatch.is_none(){causal_mismatch=Some("contact support differs");}
            if let Some(edge)=self.anatomy.geometry.contact(slot){
                let baseline=self.anatomy.geometry.baseline(edge);let left=baseline+*a;let right=baseline+*b;
                if !left.is_finite()||!right.is_finite(){invalid_gain=true;}
                if (left==0.0)!=(right==0.0)&&causal_mismatch.is_none(){causal_mismatch=Some("effective contact reachability differs");}
            }
        });
        if invalid_gain{return Err(MaterialError::Arithmetic("adaptive effective contact gain"));}
        self.contact_changes.different_pages(&other.contact_changes,|_,a,b|{
            if a!=b&&causal_mismatch.is_none(){causal_mismatch=Some("contact history event differs");}
        });
        Ok(AdaptiveComparison{state_error:finite(error)?,causal_mismatch})
    }
    // Component access to the continuous estimate; production admission also
    // consumes the discrete result from the same one traversal above.
    #[cfg(test)]
    fn difference(&self,other:&Self)->Result<f64>{Ok(self.causal_difference(other)?.state_error)}
    /// Explicit bounded depth-first span stack. Trials own private successors;
    /// no ancestor or redundant current clone retains a packet-vector copy.
    fn advance(self,ticks:u64,drive:&MaterialDrive,count:&mut WorkCount,admission:Admission)->Result<TrialStep>{
        fn closed_outputs(state:&Functional64Material)->(Charge,bool){
            let outputs=&state.gates[INPUTS..];let qm=outputs[0].qm;
            (qm,outputs.len()==TERMINALS&&outputs.iter().all(|gate|gate.y==REST&&gate.qr==Charge::ZERO&&gate.qm==qm))
        }
        let mut last_rejection=None;
        let mut prepared_left:Option<(u64,usize,TrialStep)>=None;
        let mut spans=Vec::with_capacity(MAX_REFINEMENT+1);spans.push((ticks,0usize));
        let mut total=TrialStep{state:self,emitted:[0;TERMINALS],evidence:WorkEvidence::default(),supplied:Work::ZERO,transducer_heat:Work::ZERO};
        while let Some((span,depth))=spans.pop(){
            if span==1{return Err(MaterialError::UnresolvedEvent("minimum event grid cannot resolve the required error estimate"));}
            let left=span/2;let right=span-left;
            let(coarse,first)={
                let entry=count.force_terms;
                // The common holder dies at this scope's end, BEFORE the
                // second-half trial receives its changed predecessor.
                let mut start=physical_duration(span).and_then(|_|CommonStart::new(&total.state,drive,count,admission))
                    .map_err(|error|error.force_trial_context("coarse",span,depth,entry,last_rejection))?;
                let coarse=match prepared_left.take(){
                    Some((saved_span,saved_depth,step))=>{
                        // Only the immediately rejected parent's first half:
                        // same unchanged total predecessor, drive and duration.
                        if saved_span!=span||saved_depth!=depth{return Err(MaterialError::Invalid("immediate left trial span"));}
                        Ok(ComparisonStep::from_complete(step))
                    }
                    None=>start.comparison_trial(span,count,admission)
                        .map_err(|error|error.force_trial_context("coarse",span,depth,entry,last_rejection)),
                };
                if let Err(error)=&coarse{if !matches!(error,MaterialError::UnresolvedEvent(_)){return Err(error.clone());}}
                let entry=count.force_terms;
                let first=start.trial(left,count,admission)
                    .map_err(|error|error.force_trial_context("first_half",left,depth,entry,last_rejection));
                if let Err(error)=&first{if !matches!(error,MaterialError::UnresolvedEvent(_)){return Err(error.clone());}}
                (coarse,first)
            };
            let fine=match &first{
                Ok(a)=>{
                    let entry=count.force_terms;
                    a.state.trial(right,drive,count,admission)
                        .map_err(|error|error.force_trial_context("second_half",right,depth,entry,last_rejection))
                        .and_then(|mut b|{
                            // Same original scalar accumulation order; retain
                            // a's state only until this span's decision.
                            add_step_totals(&mut b,a.emitted,a.evidence,a.supplied,a.transducer_heat)?;Ok(b)
                        })
                }
                Err(error)=>Err(error.clone()),
            };
            if let Err(error)=&fine{if !matches!(error,MaterialError::UnresolvedEvent(_)){return Err(error.clone());}}
            let mut accepted=None;
            let coarse_unresolved_reason=match &coarse{Err(MaterialError::UnresolvedEvent(reason))=>Some(*reason),_=>None};
            let fine_unresolved_reason=match &fine{Err(MaterialError::UnresolvedEvent(reason))=>Some(*reason),_=>None};
            if let(Ok(a),Ok(mut b))=(coarse,fine){
                let comparison=adaptive_comparison_parts(&a.state,&a.emitted,a.supplied,&b)?;let state_difference=comparison.state_error;let error=state_difference;
                let evidence_pairs=[(a.caloric[0],b.evidence.supply_j),(a.caloric[1],b.evidence.exported_j),
                    (a.caloric[2],b.evidence.contact_heat_j),(a.caloric[3],b.evidence.plastic_heat_j)];
                // Caloric pairs remain visible observations. Acceptance compares
                // the complete causal successor and exact physical transport.
                if comparison.accepted(){b.evidence.error_estimate=error;accepted=Some(b);}
                else{last_rejection=Some(RefinementRejection{span_ticks:span,depth,coarse_unresolved_reason,fine_unresolved_reason,
                    state_difference:Some(state_difference),causal_mismatch:comparison.causal_mismatch,evidence_pairs:Some(evidence_pairs),total_error:Some(error),
                    closed_outputs:Some([closed_outputs(&total.state),closed_outputs(&a.state),closed_outputs(&b.state)])});}
            }else{last_rejection=Some(RefinementRejection{span_ticks:span,depth,coarse_unresolved_reason,fine_unresolved_reason,
                state_difference:None,causal_mismatch:None,evidence_pairs:None,total_error:None,closed_outputs:None});}
            if let Some(step)=accepted{total=combine_steps(total,step)?;}
            else{
                if depth>=MAX_REFINEMENT{return Err(MaterialError::UnresolvedEvent("bounded coupled numerical refinement"));}
                // This one moved successor is consumed at the very next
                // left-child coarse comparison. Nothing is retained for a
                // right sibling or ancestor, and no state is cloned here.
                prepared_left=first.ok().map(|step|(left,depth+1,step));
                spans.push((right,depth+1));spans.push((left,depth+1));
            }
        }Ok(total)
    }
}
// This is the finite functional successor criterion. Caloric receipts are
// observations, not a second dynamical state or a near-zero relative veto.
#[derive(Clone,Copy,Debug)]
struct AdaptiveComparison{state_error:f64,causal_mismatch:Option<&'static str>}
impl AdaptiveComparison{fn accepted(&self)->bool{self.state_error<=RTOL&&self.causal_mismatch.is_none()}}
fn causal_comparison_scratch_bytes()->Result<usize>{
    [checked_bytes(8,std::mem::size_of::<Uint1152>())?,checked_bytes(4,std::mem::size_of::<Charge>())?,
        checked_bytes(8,std::mem::size_of::<f64>())?,
        // Bound both return/match headers without any extra material clone.
        checked_bytes(2,std::mem::size_of::<SettledTrial>())?]
        .into_iter().try_fold(std::mem::size_of::<AdaptiveComparison>(),add_bytes)
}
#[cfg(test)]
fn adaptive_comparison(coarse:&TrialStep,fine:&TrialStep)->Result<AdaptiveComparison>{
    adaptive_comparison_parts(&coarse.state,&coarse.emitted,coarse.supplied,fine)
}
fn adaptive_comparison_parts(a:&Functional64Material,emitted:&[u64;TERMINALS],supplied:Work,fine:&TrialStep)->Result<AdaptiveComparison>{
    if supplied!=fine.supplied{return Err(MaterialError::Arithmetic("adaptive source allocation differs by path"));}
    let b=&fine.state;
    if a.reserve_ug!=b.reserve_ug||a.work!=b.work{return Err(MaterialError::Arithmetic("adaptive reserve custody differs by path"));}
    if a.power.len()!=b.power.len()||a.power.iter().zip(&b.power).any(|(x,y)|x.packet.receiver!=y.packet.receiver||x.remaining!=y.remaining){
        return Err(MaterialError::Arithmetic("adaptive scheduled source custody differs by path"));
    }
    // Trial writes only numerical material, plastic topology/history and exact
    // scheduled remainders. Anatomy/history, clock, facts, delivery, last_power
    // and unavailable_since are unchanged from the common predecessor.
    let mut comparison=a.causal_difference(b)?;
    if *emitted!=fine.emitted&&comparison.causal_mismatch.is_none(){comparison.causal_mismatch=Some("terminal carrier event differs");}
    for(g,h)in a.gates[INPUTS..].iter().zip(&b.gates[INPUTS..]){
        if !g.load.within_one_carrier_error(&h.load,1.0).map_err(|_|MaterialError::Arithmetic("adaptive exact carrier remainder"))?
            &&comparison.causal_mismatch.is_none(){comparison.causal_mismatch=Some("terminal fractional carrier error exceeds budget");}
    }
    Ok(comparison)
}
fn add_step_totals(second:&mut TrialStep,emitted:[u64;TERMINALS],evidence:WorkEvidence,supplied:Work,heat:Work)->Result<()>{
    for i in 0..TERMINALS{second.emitted[i]=emitted[i].checked_add(second.emitted[i]).ok_or(MaterialError::Arithmetic("interval terminal count"))?;}
    second.evidence.add(evidence);second.supplied=supplied.add(second.supplied).map_err(MaterialError::Arithmetic)?;
    second.transducer_heat=heat.add(second.transducer_heat).map_err(MaterialError::Arithmetic)?;Ok(())
}
fn combine_steps(first:TrialStep,mut second:TrialStep)->Result<TrialStep>{
    add_step_totals(&mut second,first.emitted,first.evidence,first.supplied,first.transducer_heat)?;Ok(second)
}
fn continue_steps(first:TrialStep,ticks:u64,drive:&MaterialDrive,count:&mut WorkCount,admission:Admission)->Result<TrialStep>{
    let TrialStep{state,emitted,evidence,supplied,transducer_heat}=first;
    let mut second=state.advance(ticks,drive,count,admission)?;
    add_step_totals(&mut second,emitted,evidence,supplied,transducer_heat)?;Ok(second)
}

impl Functional64Material{
    fn facts_for(field:&SharedJointField,gate:usize)->Result<Arc<[Fact]>>{
        let completed=field.gates().get(gate).ok_or(MaterialError::Source("missing completed structural gate"))?;
        let mut facts=vec![Fact{digit:0,present:false};FACTS];
        for(family,value)in completed.dsf.ordered().iter().enumerate(){
            let rational=float_to_rational_trits(*value).map_err(|_|MaterialError::Source("exact complete field MathLoom"))?;
            for(role,digits)in[&rational.numerator_trits,&rational.denominator_trits].iter().enumerate(){
                if digits.len()>679{return Err(MaterialError::Source("complete binary64 fact exceeds declared ring anatomy"));}
                // MathLoom numerator digits already include their sign.
                for(position,&digit)in digits.iter().enumerate(){let site=(role*679+position)*7+family;facts[site]=Fact{digit,present:true};}
            }
        }Ok(facts.into())
    }
    fn constraint_energy(&self,facts:&[Fact])->Result<f64>{
        let mut energy=0.0;
        for(site,fact)in facts.iter().enumerate(){if fact.present{
            let phase=self.rings.get(site).phase;let tau=fact.digit as f64*std::f64::consts::TAU/3.0;
            for(j,k)in[LAMBDA,LAMBDA,LAMBDA/std::f64::consts::SQRT_2].iter().enumerate(){energy+=k*(1.0-(phase[(j+1)%3]-phase[j]-tau).cos());}
            energy+=LAMBDA*(1.0-(phase[0]-self.phases.get(Anatomy::fact_node(site)).receive).cos());
        }}nonnegative(energy)
    }
    fn install_due(&mut self)->Result<f64>{
        let Some(front)=self.delivery.front()else{return Ok(0.0);};
        if front.installed{return Ok(0.0);}
        let facts=Self::facts_for(&front.field,front.gate)?;let work=self.constraint_energy(&facts)?;
        if !self.pay_finite_work(work)?{
            if self.unavailable_since.is_none(){self.unavailable_since=Some(self.clock);}return Ok(0.0);
        }
        self.facts=facts;self.delivery.front_mut().unwrap().installed=true;self.unavailable_since=None;Ok(work)
    }
    fn complete_field_millisecond(&mut self)->Result<f64>{
        let Some(front)=self.delivery.front_mut()else{return Ok(0.0);};
        if !front.installed{return Ok(0.0);}
        front.remaining_ms=front.remaining_ms.checked_sub(1).ok_or(MaterialError::Invalid("zero installed field duration"))?;
        if front.remaining_ms!=0{return Ok(0.0);}
        let recovered=self.constraint_energy(&self.facts)?;self.recover_finite_work(recovered)?;
        self.facts=vec![Fact{digit:0,present:false};FACTS].into();
        let front=self.delivery.front_mut().unwrap();front.gate+=1;front.installed=false;
        if front.gate==front.field.gates().len(){self.delivery.pop_front();}
        else{front.remaining_ms=validate_field_durations(&front.field)?[front.gate];}
        Ok(recovered)
    }
    fn physical_drives(&self,reserve_powered:bool)->Result<MaterialDrive>{
        let mut voltage=vec![0.0;INPUTS];let mut budget=vec![Work::ZERO;INPUTS];
        for p in &self.power{
            let receiver=p.packet.receiver as usize;
            if p.packet.origin==PowerOrigin::MeasuredEnvironmental||reserve_powered{
                voltage[receiver]=p.source_voltage;
                budget[receiver]=Work::packet_interval(p.packet.admitted_j,p.release_ms).map_err(MaterialError::Arithmetic)?;
            }
        }
        Ok(MaterialDrive{voltage,budget,output_budget:Work::output_regulator_interval(G,VS).map_err(MaterialError::Arithmetic)?,reserve_powered})
    }
    /// Prepare one complete current successor. The predecessor is never
    /// changed, including on numeric/custody/resource refusal. The root pairs
    /// this result with the one staged body/world/source successor.
    pub(crate) fn prepare_boundary(&self,input:MaterialInputs)->Result<PreparedMaterial>{
        if input.start!=self.clock||!one_millisecond(input.start,input.end)?{return Err(MaterialError::Invalid("actual one millisecond predecessor boundary"));}
        if input.actual_reserve_ug!=self.reserve_ug{return Err(MaterialError::Invalid("caller reserve is not exact native predecessor"));}
        let no_original=[None,None];
        let source_bytes=material_source_payload(self,&no_original,&input.power,
            input.field.as_ref().map(|(field,identity,_)|(field,identity)))?;
        if source_bytes>input.admission.max_source_bytes{return Err(MaterialError::Capacity("complete material source payload"));}
        if input.power.len()>INPUTS{return Err(MaterialError::Capacity("source packet roster"));}
        let mut staged=self.clone();
        staged.power.reserve_exact(INPUTS-staged.power.len());staged.delivery.reserve_exact(2-staged.delivery.len());
        if let Some((field,identity,published))=input.field{
            if identity.is_empty()||!time_le(published,input.start)?||!staged.can_accept_field(){return Err(MaterialError::Source("complete finite field register admission"));}
            if staged.delivery.iter().any(|d|d.identity==identity){return Err(MaterialError::Source("duplicate complete field occurrence"));}
            let durations=validate_field_durations(&field)?;
            staged.delivery.push_back(Delivery{field,identity,published,gate:0,remaining_ms:durations[0],installed:false});
        }
        for packet in input.power{
            let release_ms=packet_release_ms(&packet)?;let receiver=packet.receiver as usize;
            if packet.release_start!=input.start||!time_le(input.end,packet.release_end)?{return Err(MaterialError::Source("new source packet must start at its actual release boundary"));}
            if let Some(previous)=staged.last_power[receiver]{if !time_le(previous,packet.release_start)?{return Err(MaterialError::Source("replayed or overlapping physical source packet"));}}
            if staged.power.iter().any(|p|p.packet.receiver==packet.receiver){return Err(MaterialError::Source("duplicate powered receiver"));}
            let source_voltage=packet_source_voltage(&packet,release_ms)?;
            staged.last_power[receiver]=Some(packet.release_end);
            staged.power.push(PendingPower{remaining:Work::finite_joules(packet.admitted_j).map_err(MaterialError::Arithmetic)?,packet,source_voltage,release_ms});
        }
        for p in &staged.power{
            if !time_le(p.packet.release_start,input.start)?||!time_le(input.end,p.packet.release_end)?{return Err(MaterialError::Source("retained packet does not cover actual interval"));}
        }
        let switch_paid=staged.install_due()?;
        let supply=staged.prepare_supply()?;
        let mut count=WorkCount::default();let ticks=supply.offset.ticks;
        let mut result=if ticks==0{
            let drive=supply.successor.physical_drives(false)?;
            supply.successor.advance(work_store::FULL_TICKS,&drive,&mut count,input.admission)?
        }else{
            let drive=supply.successor.physical_drives(true)?;
            let first=supply.successor.advance(ticks,&drive,&mut count,input.admission)?;
            if ticks==work_store::FULL_TICKS{first}else{
                // Only reserve-funded supplies open. Real optical/acoustic
                // sources and already stored charge continue at the same clock.
                let drive=first.state.physical_drives(false)?;
                continue_steps(first,work_store::FULL_TICKS-ticks,&drive,&mut count,input.admission)?
            }
        };
        result.state.clock=input.end;
        let recovered=result.state.complete_field_millisecond()?;
        result.evidence.field_switch_j=switch_paid-recovered;
        let mut pending=Vec::with_capacity(result.state.power.len());
        for packet in result.state.power.drain(..){
            if packet.packet.release_end==input.end{
                if !packet.remaining.is_zero(){return Err(MaterialError::Arithmetic("unreleased finite source work at expiry"));}
            }else{pending.push(packet);}
        }
        result.state.power=pending;
        let mut discharges=Vec::with_capacity(TERMINALS);
        for(terminal,&carriers)in result.emitted.iter().enumerate(){if carriers!=0{discharges.push(TimedDischarge{at:input.end,terminal:terminal as u8,carriers});}}
        let reserve_consumed_ug=self.reserve_ug.checked_sub(result.state.reserve_ug).ok_or(MaterialError::Arithmetic("interval reserve cannot increase before physical assimilation"))?;
        let positive_field_work=Work::finite_joules(switch_paid).map_err(MaterialError::Arithmetic)?;
        let recovered_field_work=Work::finite_joules(recovered).map_err(MaterialError::Arithmetic)?;
        let debited=supply.debited.add(positive_field_work).map_err(MaterialError::Arithmetic)?;
        Ok(PreparedMaterial{successor:result.state,discharges,reserve_consumed_ug,evidence:result.evidence,work:count,
            powered_offset:supply.offset,paid_thermal:supply.thermal_work,debited_work:debited.limbs,
            recovered_field_work:recovered_field_work.limbs,
            supplied_work_units:result.supplied.limbs,transducer_heat_units:result.transducer_heat.limbs})
    }
}

/// Logical allocation preflight only; the mounting owner separately admits
/// allocator/Arc/tree overhead and process RSS. No full material is decoded
/// merely to discover whether its page/index payload fits.
struct DecodeBudget{used:usize,limit:usize}
impl DecodeBudget{
    fn claim(&mut self,n:usize)->Result<()>{let next=add_bytes(self.used,n)?;if next>self.limit{return Err(MaterialError::Capacity("canonical material decode staging"));}self.used=next;Ok(())}
    fn pages_root<T:Clone>(&mut self,len:usize)->Result<()>{self.claim(add_bytes(std::mem::size_of::<Pages<T>>(),checked_bytes((len+PAGE*FAN-1)/(PAGE*FAN),std::mem::size_of::<Option<Branch<T>>>())?)?)}
    fn page_row<T>(&mut self,slot:usize,previous:&mut Option<usize>)->Result<()>{
        let page=slot/PAGE;let branch=page/FAN;
        if previous.map_or(true,|p|p/FAN!=branch){self.claim(add_bytes(std::mem::size_of::<Vec<Option<Leaf<T>>>>(),checked_bytes(FAN,std::mem::size_of::<Option<Leaf<T>>>())?)?)?;}
        if *previous!=Some(page){self.claim(add_bytes(std::mem::size_of::<Vec<T>>(),checked_bytes(PAGE,std::mem::size_of::<T>())?)?)?;}
        *previous=Some(page);Ok(())
    }
}
// Canonical current material bytes. Decode never commissions or repairs state.
struct Writer{bytes:Vec<u8>,limit:usize}
impl Writer{
    fn put(&mut self,b:&[u8])->Result<()>{let n=self.bytes.len().checked_add(b.len()).ok_or(MaterialError::Capacity("codec size"))?;if n>self.limit{return Err(MaterialError::Capacity("canonical material bytes"));}self.bytes.extend_from_slice(b);Ok(())}
    fn u8(&mut self,n:u8)->Result<()>{self.put(&[n])}
    fn u16(&mut self,n:u16)->Result<()>{self.put(&n.to_be_bytes())}
    fn u32(&mut self,n:u32)->Result<()>{self.put(&n.to_be_bytes())}
    fn u64(&mut self,n:u64)->Result<()>{self.put(&n.to_be_bytes())}
    fn f64(&mut self,n:f64)->Result<()>{finite(n)?;self.u64(n.to_bits())}
    fn len(&mut self,n:usize)->Result<()>{self.u64(u64::try_from(n).map_err(|_|MaterialError::Capacity("codec length width"))?)}
    fn blob(&mut self,b:&[u8])->Result<()>{self.len(b.len())?;self.put(b)}
    fn time(&mut self,t:ExactTime)->Result<()>{let(n,d)=t.parts();self.put(&n.to_be_bytes())?;self.u64(d)}
    fn big(&mut self,v:Uint1152)->Result<()>{for limb in v.limbs{self.u64(limb)?;}Ok(())}
    fn work(&mut self,v:Work)->Result<()>{for limb in v.limbs{self.u64(limb)?;}Ok(())}
    fn charge(&mut self,q:Charge)->Result<()>{q.validate().map_err(|_|MaterialError::Invalid("exact charge"))?;self.u8(u8::from(q.negative))?;self.big(q.magnitude)}
    fn remainder(&mut self,r:Remainder)->Result<()>{r.validate().map_err(|_|MaterialError::Invalid("terminal remainder"))?;self.u8(u8::from(r.negative))?;self.big(r.magnitude)}
    fn optional_time(&mut self,t:Option<ExactTime>)->Result<()>{match t{None=>self.u8(0),Some(t)=>{self.u8(1)?;self.time(t)}}}
}
struct Reader<'a>{body:&'a[u8],at:usize,budget:DecodeBudget}
impl<'a> Reader<'a>{
    fn take(&mut self,n:usize)->Result<&'a[u8]>{let end=self.at.checked_add(n).ok_or(MaterialError::Capacity("codec cursor"))?;if end>self.body.len(){return Err(MaterialError::Invalid("truncated material body"));}let b=&self.body[self.at..end];self.at=end;Ok(b)}
    fn u8(&mut self)->Result<u8>{Ok(self.take(1)?[0])}
    fn flag(&mut self)->Result<bool>{match self.u8()?{0=>Ok(false),1=>Ok(true),_=>Err(MaterialError::Invalid("noncanonical Boolean"))}}
    fn u16(&mut self)->Result<u16>{Ok(u16::from_be_bytes(self.take(2)?.try_into().unwrap()))}
    fn u32(&mut self)->Result<u32>{Ok(u32::from_be_bytes(self.take(4)?.try_into().unwrap()))}
    fn u64(&mut self)->Result<u64>{Ok(u64::from_be_bytes(self.take(8)?.try_into().unwrap()))}
    fn f64(&mut self)->Result<f64>{finite(f64::from_bits(self.u64()?))}
    fn len(&mut self,limit:usize,min_bytes:usize)->Result<usize>{let n=usize::try_from(self.u64()?).map_err(|_|MaterialError::Capacity("codec length"))?;if n>limit||n.checked_mul(min_bytes).map_or(true,|b|b>self.body.len()-self.at){return Err(MaterialError::Capacity("encoded material count"));}Ok(n)}
    fn blob_slice(&mut self,limit:usize)->Result<&'a[u8]>{let n=self.len(limit,1)?;self.take(n)}
    fn blob(&mut self,limit:usize)->Result<Arc<[u8]>>{let bytes=self.blob_slice(limit)?;self.budget.claim(bytes.len())?;Ok(bytes.into())}
    fn time(&mut self)->Result<ExactTime>{let n=i64::from_be_bytes(self.take(8)?.try_into().unwrap());let d=self.u64()?;ExactTime::new(n,d).map_err(|_|MaterialError::Invalid("canonical physical time"))}
    fn big(&mut self)->Result<Uint1152>{let mut v=Uint1152::ZERO;for limb in &mut v.limbs{*limb=self.u64()?;}Ok(v)}
    fn work(&mut self)->Result<Work>{let mut v=Work::ZERO;for limb in &mut v.limbs{*limb=self.u64()?;}Ok(v)}
    fn charge(&mut self)->Result<Charge>{let q=Charge{negative:self.flag()?,magnitude:self.big()?};q.validate().map_err(|_|MaterialError::Invalid("canonical charge"))?;Ok(q)}
    fn remainder(&mut self)->Result<Remainder>{let r=Remainder{negative:self.flag()?,magnitude:self.big()?};r.validate().map_err(|_|MaterialError::Invalid("canonical carrier remainder"))?;Ok(r)}
    fn optional_time(&mut self)->Result<Option<ExactTime>>{if self.flag()?{Ok(Some(self.time()?))}else{Ok(None)}}
}
fn constitutional_bits()->[f64;28]{[
    LAMBDA,DRAG,NG,REST,K,ZETA,COUPLING,ALPHA,CM,CR,G,VS,g0(),
    material::R_P0,material::R_A0,material::RECEIVING_RESTING_V,
    material::KT_J,material::ELEMENTARY_CHARGE_C,
    material::GATE_STIFFNESS_K_J,material::GATE_DRAG_ZETA_J_S,
    material::CONTACT_MATERIAL_CONDUCTIVITY_S_PER_M,material::CONTACT_AREA_REF_M2,material::CONTACT_LENGTH_REF_M,
    RTOL,SOLVE_TOL,std::f64::consts::TAU,std::f64::consts::SQRT_2,
    0.5,
]}
impl Anatomy{
    fn encode_anatomy(&self,w:&mut Writer,history:bool)->Result<()>{
        w.put(b"GL64AN01")?;w.blob(CONSTITUTION)?;
        for n in [NODES,FACTS,RAW_SLOTS,INPUTS,TERMINALS,work_store::LIMBS,work_store::CUT_BITS,MAX_ITERATIONS,MAX_REFINEMENT]{w.len(n)?;}
        for x in constitutional_bits(){w.f64(x)?;}
        for &s in self.geometry.severed.iter(){w.u8(u8::from(s))?;}
        for y in self.geometry.yield_intra{w.f64(y)?;}w.f64(self.geometry.yield_inter)?;
        w.len(self.input_nodes.len())?;for &n in self.input_nodes.iter(){w.u16(n)?;}
        w.u64(self.reserve_capacity_ug)?;w.len(self.thermal_loads.len())?;
        for load in self.thermal_loads.iter(){w.blob(&load.identity)?;w.u64(load.microwatts)?;}
        if history{w.blob(&self.complete_authentic_history)?;}Ok(())
    }
    /// Stable physical source evidence excludes authentic historical payload.
    pub(crate) fn source_evidence(&self,limit:usize)->Result<Vec<u8>>{let mut w=Writer{bytes:Vec::new(),limit};self.encode_anatomy(&mut w,false)?;Ok(w.bytes)}
    fn decode_anatomy(r:&mut Reader,limit:usize)->Result<Arc<Self>>{
        if r.take(8)?!=b"GL64AN01"||r.blob_slice(CONSTITUTION.len())?!=CONSTITUTION{return Err(MaterialError::Invalid("anatomy constitution version"));}
        for expected in [NODES,FACTS,RAW_SLOTS,INPUTS,TERMINALS,work_store::LIMBS,work_store::CUT_BITS,MAX_ITERATIONS,MAX_REFINEMENT]{
            if r.u64()?!=expected as u64{return Err(MaterialError::Invalid("different material dimensions or numerical law"));}
        }
        for expected in constitutional_bits(){if r.f64()?.to_bits()!=expected.to_bits(){return Err(MaterialError::Invalid("different material coefficient bits"));}}
        r.budget.claim(2*4096+NODES*(9*std::mem::size_of::<f64>()+std::mem::size_of::<u32>())+INPUTS*std::mem::size_of::<u16>()+std::mem::size_of::<Anatomy>())?;
        let mut severed=Vec::with_capacity(4096);for _ in 0..4096{severed.push(r.flag()?);}
        let mut yields=[0.0;64];for y in &mut yields{*y=r.f64()?;}let inter=r.f64()?;
        if r.len(INPUTS,2)?!=INPUTS{return Err(MaterialError::Invalid("complete608 receptor roster required"));}
        let mut inputs=Vec::with_capacity(INPUTS);for _ in 0..INPUTS{inputs.push(r.u16()?);}
        let capacity=r.u64()?;
        if r.len(1,17)?!=1{return Err(MaterialError::Invalid("authenticated thermal roster required"));}
        let thermal=ThermalLoad{identity:r.blob(limit)?,microwatts:r.u64()?};
        let history=r.blob(limit)?;
        let geometry=Geometry::new(severed.into(),yields,inter).map_err(MaterialError::Invalid)?;
        Ok(Arc::new(Self::declare(geometry,inputs.into(),history,capacity,vec![thermal].into())?))
    }
}
impl Functional64Material{
    pub(crate) fn encode(&self,limit:usize,source_bounds:AdmissionBounds)->Result<Vec<u8>>{
        let mut w=Writer{bytes:Vec::new(),limit};w.put(MAGIC)?;self.anatomy.encode_anatomy(&mut w,true)?;w.time(self.clock)?;
        w.u64(self.reserve_ug)?;w.work(self.work)?;w.optional_time(self.unavailable_since)?;
        // Count and stream existing sparse storage; do not allocate a duplicate
        // vector of every retained contact just to serialize it.
        w.len(self.phases.allocated().filter(|(_,p)|p.send.to_bits()!=0||p.receive.to_bits()!=0).count())?;
        for(i,p)in self.phases.allocated(){if p.send.to_bits()!=0||p.receive.to_bits()!=0{w.u16(i as u16)?;w.f64(p.send)?;w.f64(p.receive)?;}}
        w.len(self.rings.allocated().filter(|(_,p)|p.phase.iter().any(|x|x.to_bits()!=0)).count())?;
        for(i,p)in self.rings.allocated(){if p.phase.iter().any(|x|x.to_bits()!=0){w.u16(i as u16)?;for x in p.phase{w.f64(x)?;}}}
        w.len(self.weights.allocated().filter(|(_,v)|v.to_bits()!=0).count())?;
        for(i,&v)in self.weights.allocated(){if v.to_bits()!=0{w.u32(i as u32)?;w.f64(v)?;}}
        w.len(self.facts.len())?;for fact in self.facts.iter(){w.u8(u8::from(fact.present))?;w.u8((fact.digit+1) as u8)?;}
        w.len(self.gates.len())?;for gate in self.gates.iter(){w.f64(gate.y)?;w.charge(gate.q)?;w.charge(gate.qm)?;w.charge(gate.qr)?;w.remainder(gate.load)?;}
        w.len(self.last_power.len())?;for &t in &self.last_power{w.optional_time(t)?;}
        w.len(self.power.len())?;for p in &self.power{
            let q=&p.packet;w.blob(&q.identity)?;w.u16(q.receiver)?;w.u8(match q.origin{PowerOrigin::MeasuredEnvironmental=>0,PowerOrigin::BodyReserve=>1})?;
            for t in [q.acquired_start,q.acquired_end,q.available,q.release_start,q.release_end]{w.time(t)?;}
            for x in [q.admitted_j,q.lower_j,q.upper_j,p.source_voltage]{w.f64(x)?;}
            w.work(p.remaining)?;w.u8(p.release_ms)?;
        }
        w.len(self.delivery.len())?;for d in &self.delivery{
            let source=encode_joint_source(d.field.source(),source_bounds).map_err(|_|MaterialError::Source("complete source encoding"))?;
            w.blob(&source)?;w.blob(&d.identity)?;w.time(d.published)?;w.len(d.gate)?;w.u16(d.remaining_ms)?;w.u8(u8::from(d.installed))?;
        }
        w.len(self.contact_changes.allocated().filter(|(_,changed)|**changed).count())?;
        for(slot,&changed)in self.contact_changes.allocated(){if changed{w.u32(slot as u32)?;}}
        Ok(w.bytes)
    }
    pub(crate) fn decode(bytes:&[u8],limit:usize,source_bounds:AdmissionBounds)->Result<Self>{
        if bytes.len()>limit{return Err(MaterialError::Capacity("canonical material decode bytes"));}
        let mut r=Reader{body:bytes,at:0,budget:DecodeBudget{used:std::mem::size_of::<Self>(),limit}};if r.take(8)?!=MAGIC{return Err(MaterialError::Invalid("current material schema required"));}
        let anatomy=Anatomy::decode_anatomy(&mut r,limit)?;let clock=r.time()?;let reserve_ug=r.u64()?;let work=r.work()?;let unavailable_since=r.optional_time()?;
        if reserve_ug>anatomy.reserve_capacity_ug{return Err(MaterialError::Invalid("retained reserve exceeds authenticated capacity"));}
        work.add(Work::nutrition(reserve_ug).map_err(MaterialError::Arithmetic)?).map_err(MaterialError::Arithmetic)?;
        if let Some(time)=unavailable_since{if !time_le(time,clock)?{return Err(MaterialError::Invalid("unavailability begins after current clock"));}}
        r.budget.claim(NODES*std::mem::size_of::<u16>())?;
        r.budget.pages_root::<PhasePair>(NODES)?;r.budget.pages_root::<Ring>(FACTS)?;r.budget.pages_root::<f64>(RAW_SLOTS)?;r.budget.pages_root::<bool>(RAW_SLOTS)?;r.budget.pages_root::<Arc<Vec<u32>>>(NODES)?;
        let mut s=Self{anatomy,clock,phases:Pages::new(NODES,PhasePair::default()),rings:Pages::new(FACTS,Ring{phase:[0.0;3]}),weights:Pages::new(RAW_SLOTS,0.0),incident:Pages::new(NODES,Arc::new(Vec::new())),nonzero_nodes:Arc::new(BTreeSet::new()),facts:Arc::new([]),gates:Arc::new(Vec::new()),power:Vec::new(),last_power:Vec::new(),delivery:VecDeque::new(),reserve_ug,work,unavailable_since,contact_changes:Pages::new(RAW_SLOTS,false)};
        let mut prior_page=None;
        let n=r.len(NODES,18)?;let mut previous=None;
        for _ in 0..n{
            let i=r.u16()? as usize;if i>=NODES||previous.map_or(false,|p|p>=i){return Err(MaterialError::Invalid("phase address order"));}previous=Some(i);
            let p=PhasePair{send:r.f64()?,receive:r.f64()?};if p.send.to_bits()==0&&p.receive.to_bits()==0{return Err(MaterialError::Invalid("redundant phase row"));}
            r.budget.page_row::<PhasePair>(i,&mut prior_page)?;
            s.phases.set(i,p)?;if p.send!=0.0||p.receive!=0.0{Arc::make_mut(&mut s.nonzero_nodes).insert(i as u16);}
        }
        let mut prior_page=None;
        let n=r.len(FACTS,26)?;let mut previous=None;
        for _ in 0..n{
            let i=r.u16()? as usize;if i>=FACTS||previous.map_or(false,|p|p>=i){return Err(MaterialError::Invalid("ring address order"));}previous=Some(i);
            r.budget.page_row::<Ring>(i,&mut prior_page)?;
            let p=[r.f64()?,r.f64()?,r.f64()?];if p.iter().all(|x|x.to_bits()==0){return Err(MaterialError::Invalid("redundant ring row"));}s.rings.set(i,Ring{phase:p})?;
        }
        let mut prior_page=None;
        let n=r.len(RAW_SLOTS,12)?;let mut previous=None;
        for _ in 0..n{
            let i=r.u32()? as usize;if i>=RAW_SLOTS||previous.map_or(false,|p|p>=i){return Err(MaterialError::Invalid("contact address order"));}previous=Some(i);
            let value=r.f64()?;if value.to_bits()==0{return Err(MaterialError::Invalid("redundant contact row"));}
            // Preserve signed zero and all finite raw bits, even unmounted slots.
            r.budget.page_row::<f64>(i,&mut prior_page)?;
            s.weights.set(i,value)?;
        }
        let mounted=s.weights.allocated().filter(|(slot,w)|**w!=0.0&&s.anatomy.geometry.contact(*slot).is_some()).count();
        r.budget.claim(add_bytes(checked_bytes(mounted,4*std::mem::size_of::<u32>())?,checked_bytes(NODES,2*std::mem::size_of::<Vec<u32>>()+std::mem::size_of::<Arc<Vec<u32>>>())?)?)?;
        s.rebuild_incident()?;
        if r.len(FACTS,2)?!=FACTS{return Err(MaterialError::Invalid("incomplete typed fact fabric"));}
        r.budget.claim(2*FACTS*std::mem::size_of::<Fact>())?;
        let mut facts=Vec::with_capacity(FACTS);
        for _ in 0..FACTS{let present=r.flag()?;let digit=r.u8()?;if digit>2||(!present&&digit!=1){return Err(MaterialError::Invalid("typed fact digit"));}facts.push(Fact{digit:digit as i8-1,present});}s.facts=facts.into();
        if r.len(INPUTS+TERMINALS,588)?!=INPUTS+TERMINALS{return Err(MaterialError::Invalid("incomplete mounted gate state"));}
        r.budget.claim((INPUTS+TERMINALS)*std::mem::size_of::<Gate>()+INPUTS*std::mem::size_of::<Option<ExactTime>>()+INPUTS*std::mem::size_of::<PendingPower>()+2*std::mem::size_of::<Delivery>())?;
        let mut gates=Vec::with_capacity(INPUTS+TERMINALS);
        for i in 0..INPUTS+TERMINALS{
            let gate=Gate{y:r.f64()?,q:r.charge()?,qm:r.charge()?,qr:r.charge()?,load:r.remainder()?};
            if !(0.0..=1.0).contains(&gate.y)||gate.q.negative||gate.qm.negative||gate.qr.negative
                ||(i<INPUTS&&(gate.qm!=Charge::ZERO||gate.qr!=Charge::ZERO||gate.load!=Remainder::ZERO))||(i>=INPUTS&&gate.q!=Charge::ZERO){return Err(MaterialError::Invalid("gate material invariant"));}
            let projected=NumericalGate::project(gate)?;
            if i>=INPUTS&&(gate.load.negative||projected.qr/CR>projected.qm/CM||projected.qm/CM>VS){return Err(MaterialError::Invalid("retained output circuit ordering"));}
            gates.push(gate);
        }
        s.gates=Arc::new(gates);
        if r.len(INPUTS,1)?!=INPUTS{return Err(MaterialError::Invalid("source arrival custody count"));}
        s.last_power=Vec::with_capacity(INPUTS);
        for _ in 0..INPUTS{s.last_power.push(r.optional_time()?);}
        let n=r.len(INPUTS,277)?;let mut receivers=BTreeSet::new();
        s.power=Vec::with_capacity(n);
        for _ in 0..n{
            let identity=r.blob(source_bounds.max_source_bytes)?;let receiver=r.u16()?;
            let origin=match r.u8()?{0=>PowerOrigin::MeasuredEnvironmental,1=>PowerOrigin::BodyReserve,_=>return Err(MaterialError::Invalid("power origin"))};
            let packet=PowerPacket{identity,receiver,origin,acquired_start:r.time()?,acquired_end:r.time()?,available:r.time()?,release_start:r.time()?,release_end:r.time()?,admitted_j:r.f64()?,lower_j:r.f64()?,upper_j:r.f64()?};
            let source_voltage=r.f64()?;let remaining=r.work()?;let release_ms=r.u8()?;
            let expected_release=packet_release_ms(&packet)?;
            if !receivers.insert(receiver)||source_voltage<0.0||release_ms!=expected_release
                ||!Work::finite_joules(packet.admitted_j).map_err(MaterialError::Arithmetic)?.gte(remaining)
                ||!time_le(packet.release_start,s.clock)?||!time_le(s.clock,packet.release_end)?||s.clock==packet.release_end
                ||s.last_power[receiver as usize]!=Some(packet.release_end){return Err(MaterialError::Invalid("retained power packet invariant"));}
            // Remaining release slots derive from the retained exact clock;
            // no packet or elapsed slice is re-created during ordinary restore.
            let remaining_ms=duration_ms(s.clock,packet.release_end)?;
            if remaining_ms>release_ms as u64{return Err(MaterialError::Invalid("retained power release cursor"));}
            let expected_remaining=Work::packet_interval(packet.admitted_j,release_ms).map_err(MaterialError::Arithmetic)?.mul(remaining_ms).map_err(MaterialError::Arithmetic)?;
            if remaining!=expected_remaining||source_voltage.to_bits()!=packet_source_voltage(&packet,release_ms)?.to_bits(){return Err(MaterialError::Invalid("retained source release or voltage constitution"));}
            s.power.push(PendingPower{packet,source_voltage,remaining,release_ms});
        }
        for(receiver,&last)in s.last_power.iter().enumerate(){if let Some(time)=last{
            if !time_le(time,s.clock)?&&!receivers.contains(&(receiver as u16)){return Err(MaterialError::Invalid("future source release without retained packet"));}
        }}
        let n=r.len(2,44)?;
        s.delivery=VecDeque::with_capacity(n);
        for index in 0..n{
            let body=r.blob_slice(source_bounds.max_payload_bytes)?;
            let actual_payload=crate::joint_uf_vector::source_codec::joint_source_field_payload_bound(body,source_bounds)
                .map_err(|_|MaterialError::Source("actual complete source allocation admission"))?;
            r.budget.claim(actual_payload)?;
            let source=decode_joint_source(body,source_bounds).map_err(|_|MaterialError::Source("complete original source decode"))?;
            // Exactly one unchanged full evaluation per occupied field register.
            let field=evaluate_joint_source(source,source_bounds).map_err(|_|MaterialError::Source("unchanged full joint re-evaluation"))?;
            let durations=validate_field_durations(&field)?;
            let identity=r.blob(source_bounds.max_source_bytes)?;let published=r.time()?;let gate=r.len(25,0)?;let remaining_ms=r.u16()?;let installed=r.flag()?;
            if identity.is_empty()||!time_le(published,s.clock)?||gate>=durations.len(){return Err(MaterialError::Invalid("complete-field cursor"));}
            let full_ms=durations[gate];
            if remaining_ms==0||remaining_ms>full_ms||(!installed&&remaining_ms!=full_ms)
                ||(index!=0&&(installed||gate!=0)){return Err(MaterialError::Invalid("complete-field gate custody"));}
            s.delivery.push_back(Delivery{field,identity,published,gate,remaining_ms,installed});
        }
        let mut prior_page=None;
        let n=r.len(RAW_SLOTS,4)?;let mut previous=None;
        for _ in 0..n{
            let slot=r.u32()?;
            if slot as usize>=RAW_SLOTS||previous.map_or(false,|p|p>=slot)||!s.anatomy.geometry.contact(slot as usize).map_or(false,|e|e.plastic){return Err(MaterialError::Invalid("contact change cursor"));}
            r.budget.page_row::<bool>(slot as usize,&mut prior_page)?;
            previous=Some(slot);s.contact_changes.set(slot as usize,true)?;
        }
        if r.at!=bytes.len(){return Err(MaterialError::Invalid("trailing canonical material bytes"));}
        let expected=match s.delivery.front(){Some(d)if d.installed=>Self::facts_for(&d.field,d.gate)?,_=>vec![Fact{digit:0,present:false};FACTS].into()};
        if s.facts.iter().zip(expected.iter()).any(|(a,b)|a.present!=b.present||a.digit!=b.digit){return Err(MaterialError::Invalid("field/cursor/material constraint mismatch"));}
        if s.delivery.len()==2&&s.delivery[0].identity==s.delivery[1].identity{return Err(MaterialError::Invalid("duplicate retained field identity"));}
        if s.unavailable_since.is_some()&&s.delivery.front().map_or(true,|d|d.installed){return Err(MaterialError::Invalid("brownout cursor without unpaid gate"));}
        Ok(s)
    }
}

// One borrowed current material view and its exact source evidence. This is
// observation, never an additional cognitive owner or a replacement checkpoint.
#[derive(Clone,Copy,Debug)]
pub(crate) struct MaterialContactView{
    pub(crate) authentic_slot:u32,pub(crate) from_node:u16,pub(crate) to_node:u16,
    pub(crate) signed_geometry:f64,pub(crate) yield_threshold:f64,pub(crate) plastic:bool,
}
impl MaterialContactView{pub(crate) fn material_coordinate_endpoints(self)->(usize,usize){(2*self.from_node as usize,2*self.to_node as usize+1)}}
pub(crate) struct MaterialView<'a>{
    pub(crate) time:ExactTime,pub(crate) coordinates:Vec<f64>,pub(crate) contact_rows:Vec<MaterialContactView>,
    pub(crate) anatomy:&'a Anatomy,pub(crate) exact_custody:&'a Functional64Material,
}
pub(crate) struct MaterialWorkState{pub(crate) reserve_ug:u64,pub(crate) work_units:[u64;19]}
pub(crate) struct ContactEvidenceRange{pub(crate) authentic_slot:u32,pub(crate) range:std::ops::Range<usize>}
pub(crate) struct SourceObservationEvidence{
    pub(crate) bytes:Arc<[u8]>,pub(crate) raw_coordinates:std::ops::Range<usize>,
    pub(crate) exact_current:std::ops::Range<usize>,pub(crate) reserve_and_work:std::ops::Range<usize>,
    pub(crate) contacts:Vec<ContactEvidenceRange>,
}
pub(crate) struct DeliveryView<'a>{
    pub(crate) identity:&'a[u8],pub(crate) published:ExactTime,pub(crate) gate_index:usize,
    pub(crate) remaining_ms:u16,pub(crate) installed:bool,
}
impl Functional64Material{
    pub(crate) fn work_state(&self)->MaterialWorkState{MaterialWorkState{reserve_ug:self.reserve_ug,work_units:self.work.limbs}}
    pub(crate) fn source_reserve_micrograms(&self)->u64{self.reserve_ug}
    pub(crate) fn delivery_view(&self)->impl Iterator<Item=DeliveryView<'_>>{
        self.delivery.iter().map(|d|DeliveryView{identity:&d.identity,published:d.published,gate_index:d.gate,remaining_ms:d.remaining_ms,installed:d.installed})
    }
    /// Sparse observation rows include dormant retained contacts and changed
    /// zeros. Both ordered page streams are merged without a second history map.
    fn source_contact_rows(&self)->impl Iterator<Item=MaterialContactView>+'_ {
        let mut weights=self.weights.allocated().filter(|(_,w)|w.to_bits()!=0).map(|(slot,_)|slot).peekable();
        let mut changed=self.contact_changes.allocated().filter(|(_,flag)|**flag).map(|(slot,_)|slot).peekable();
        std::iter::from_fn(move||loop{
            let slot=match(weights.peek().copied(),changed.peek().copied()){
                (None,None)=>return None,(Some(a),None)=>{weights.next();a},(None,Some(b))=>{changed.next();b},
                (Some(a),Some(b))=>{if a<=b{weights.next();}if b<=a{changed.next();}a.min(b)}
            };
            if let Some(e)=self.anatomy.geometry.contact(slot){return Some(MaterialContactView{authentic_slot:slot as u32,from_node:e.from,to_node:e.to,signed_geometry:*self.weights.get(slot),yield_threshold:e.threshold,plastic:e.plastic});}
        })
    }
    pub(crate) fn material_view(&self)->Result<MaterialView<'_>>{
        let mut coordinates=Vec::with_capacity(self.anatomy.raw_coordinate_count());
        for node in 0..NODES{let p=self.phases.get(node);coordinates.push(p.send);coordinates.push(p.receive);}
        for site in 0..FACTS{coordinates.extend_from_slice(&self.rings.get(site).phase);}
        for g in &self.gates[..INPUTS]{coordinates.push(g.y);coordinates.push(g.q.projection().map_err(|_|MaterialError::Arithmetic("raw input charge projection"))?);}
        for g in &self.gates[INPUTS..]{
            coordinates.push(g.y);coordinates.push(g.qm.projection().map_err(|_|MaterialError::Arithmetic("raw membrane charge projection"))?);
            coordinates.push(g.qr.projection().map_err(|_|MaterialError::Arithmetic("raw receiver charge projection"))?);
        }
        // Source incidence is independent of the currently moving frontier.
        // Retain nonzero mounted rows and each explicit changed-to-zero row.
        // Unmounted authentic slots remain exact in ordinary material custody.
        let contact_rows=self.source_contact_rows().collect();
        Ok(MaterialView{time:self.clock,coordinates,contact_rows,anatomy:&self.anatomy,exact_custody:self})
    }
    pub(crate) fn source_observation_evidence(&self,limit:usize)->Result<SourceObservationEvidence>{
        let view=self.material_view()?;self.encode_observation_view(&view,limit)
    }
    /// Reuse the one actual immutable successor view for source F and evidence;
    /// no second material traversal or repeated raw source-evidence payload.
    pub(crate) fn encode_observation_view(&self,view:&MaterialView<'_>,limit:usize)->Result<SourceObservationEvidence>{
        if !std::ptr::eq(view.exact_custody,self)||!std::ptr::eq(view.anatomy,self.anatomy.as_ref())
            ||view.time!=self.clock||view.coordinates.len()!=self.anatomy.raw_coordinate_count(){
            return Err(MaterialError::Invalid("observation is not this complete material successor"));
        }
        let mut w=Writer{bytes:Vec::new(),limit};w.put(b"GL64OB01")?;w.time(self.clock)?;w.len(view.coordinates.len())?;
        let start=w.bytes.len();for &x in &view.coordinates{w.f64(x)?;}let raw_coordinates=start..w.bytes.len();
        let start=w.bytes.len();w.len(self.gates.len())?;
        for(i,g)in self.gates.iter().enumerate(){if i<INPUTS{w.charge(g.q)?;}else{w.charge(g.qm)?;w.charge(g.qr)?;w.remainder(g.load)?;}}
        let exact_current=start..w.bytes.len();
        let start=w.bytes.len();w.u64(self.reserve_ug)?;w.work(self.work)?;let reserve_and_work=start..w.bytes.len();
        w.len(view.contact_rows.len())?;let mut contacts=Vec::with_capacity(view.contact_rows.len());
        for e in &view.contact_rows{
            let start=w.bytes.len();w.u32(e.authentic_slot)?;w.u16(e.from_node)?;w.u16(e.to_node)?;
            w.f64(e.signed_geometry)?;w.f64(e.yield_threshold)?;w.u8(u8::from(e.plastic))?;
            contacts.push(ContactEvidenceRange{authentic_slot:e.authentic_slot,range:start..w.bytes.len()});
        }
        Ok(SourceObservationEvidence{bytes:w.bytes.into(),raw_coordinates,exact_current,reserve_and_work,contacts})
    }
}

/// Logical payload admission, not allocator RSS. Shared material anatomy,
/// authentic history and evaluated source fields are counted once. Page/Vec
/// capacity is included; allocator and BTree node headers belong to the measured
/// process envelope. This read-only report never encodes or mutates the owner.
#[derive(Clone,Copy,Debug)]
pub(crate) struct MaterialLogicalSize {
    /// Current material and anatomy, including distinct packet/thermal identity
    /// bytes; excludes the two separately reported immutable payload classes.
    pub(crate) retained_material_bytes:usize,
    pub(crate) authentic_history_bytes:usize,
    pub(crate) shared_field_payload_bound:usize,
    pub(crate) mounted_contact_source_rows:usize,
    /// Whole material preparation: predecessor/current/three trial states,
    /// currently occupied immutable custody once and numerical scratch.
    pub(crate) preparation_peak_bound:usize,
}
fn material_page_bytes<T:Clone>(pages:&Pages<T>)->Result<usize>{
    let mut bytes=add_bytes(pages.logical_payload()?,std::mem::size_of::<Vec<Option<Branch<T>>>>())?;
    for branch in pages.root.iter().flatten(){
        bytes=add_bytes(bytes,std::mem::size_of::<Vec<Option<Leaf<T>>>>())?;
        for _ in branch.iter().flatten(){bytes=add_bytes(bytes,std::mem::size_of::<Vec<T>>())?;}
    }
    Ok(bytes)
}
/// Additional populated pages permitted by at most `writes` distinct addresses.
/// Existing capacities are already in material_page_bytes. COW coexistence is
/// admitted separately, so this function bounds new page population only.
fn material_page_growth<T:Clone>(pages:&Pages<T>,writes:usize)->Result<usize>{
    let mut branches=0usize;let mut leaves=0usize;
    for b in pages.root.iter().flatten(){branches=add_bytes(branches,1)?;leaves=add_bytes(leaves,b.iter().filter(|x|x.is_some()).count())?;}
    let total_leaves=add_bytes(pages.len,PAGE-1)?/PAGE;
    let new_leaves=writes.min(total_leaves.checked_sub(leaves).ok_or(MaterialError::Invalid("page population"))?);
    let new_branches=writes.min(pages.root.len().checked_sub(branches).ok_or(MaterialError::Invalid("branch population"))?);
    add_bytes(checked_bytes(new_leaves,add_bytes(std::mem::size_of::<Vec<T>>(),checked_bytes(PAGE,std::mem::size_of::<T>())?)?)?,
        checked_bytes(new_branches,add_bytes(std::mem::size_of::<Vec<Option<Leaf<T>>>>(),checked_bytes(FAN,std::mem::size_of::<Option<Leaf<T>>>())?)?)?)
}
fn material_add_identity(bytes:&Arc<[u8]>,seen:&mut[(usize,usize)],count:&mut usize,total:&mut usize)->Result<()>{
    let key=(bytes.as_ptr() as usize,bytes.len());
    if !seen[..*count].contains(&key){
        if *count==seen.len(){return Err(MaterialError::Capacity("retained source identity roster"));}
        seen[*count]=key;*count+=1;*total=add_bytes(*total,bytes.len())?;
    }Ok(())
}
impl Functional64Material{
    pub(crate) fn logical_size(&self,admission:Admission)->Result<MaterialLogicalSize>{
        use std::mem::size_of;
        if self.power.len()>INPUTS||self.delivery.len()>2||self.anatomy.thermal_loads.len()!=1{
            return Err(MaterialError::Invalid("bounded material owner roster"));
        }
        let mut mutable=size_of::<Self>();
        for n in [material_page_bytes(&self.phases)?,material_page_bytes(&self.rings)?,
            material_page_bytes(&self.weights)?,material_page_bytes(&self.incident)?,material_page_bytes(&self.contact_changes)?,
            checked_bytes(self.facts.len(),size_of::<Fact>())?,size_of::<Vec<Gate>>(),checked_bytes(self.gates.capacity(),size_of::<Gate>())?,
            checked_bytes(self.power.capacity(),size_of::<PendingPower>())?,checked_bytes(self.last_power.capacity(),size_of::<Option<ExactTime>>())?,
            checked_bytes(self.delivery.capacity(),size_of::<Delivery>())?,size_of::<BTreeSet<u16>>(),checked_bytes(self.nonzero_nodes.len(),size_of::<u16>())?,
            size_of::<Vec<u32>>()]{mutable=add_bytes(mutable,n)?;}
        // Empty page cells share one empty vector. Every populated node has its
        // own retained incident vector; unchanged trial clones share its Arc.
        for (_,rows) in self.incident.allocated(){
            if !Arc::ptr_eq(rows,&self.incident.zero){
                mutable=add_bytes(mutable,add_bytes(size_of::<Vec<u32>>(),checked_bytes(rows.capacity(),size_of::<u32>())?)?)?;
            }
        }
        let mut anatomy=size_of::<Anatomy>();
        for n in [checked_bytes(4096,size_of::<bool>())?,checked_bytes(NODES,size_of::<u32>())?,checked_bytes(NODES,size_of::<[f64;3]>())?,
            checked_bytes(self.anatomy.input_nodes.len(),size_of::<u16>())?,checked_bytes(self.anatomy.thermal_loads.len(),size_of::<ThermalLoad>())?]{anatomy=add_bytes(anatomy,n)?;}
        let history=self.anatomy.complete_authentic_history.len();
        let mut identities=[(0usize,0usize);INPUTS+3];let mut identity_count=0usize;let mut identity_bytes=0usize;
        for row in &self.power{material_add_identity(&row.packet.identity,&mut identities,&mut identity_count,&mut identity_bytes)?;}
        for row in &self.delivery{material_add_identity(&row.identity,&mut identities,&mut identity_count,&mut identity_bytes)?;}
        for row in self.anatomy.thermal_loads.iter(){material_add_identity(&row.identity,&mut identities,&mut identity_count,&mut identity_bytes)?;}
        // If an identity borrows the whole authentic archive, it is already
        // owned by `history`; an interior/independent copy remains a real copy.
        if identities[..identity_count].contains(&(self.anatomy.complete_authentic_history.as_ptr() as usize,history)){
            identity_bytes=identity_bytes.checked_sub(history).ok_or(MaterialError::Arithmetic("identity ownership"))?;
        }
        let retained=add_bytes(add_bytes(mutable,anatomy)?,identity_bytes)?;
        let mut fields=0usize;let mut field_ptrs=[0usize;2];let mut field_count=0usize;
        for row in &self.delivery{let p=Arc::as_ptr(&row.field) as usize;
            if !field_ptrs[..field_count].contains(&p){field_ptrs[field_count]=p;field_count+=1;fields=add_bytes(fields,row.field.admitted_payload_bound())?;}
        }
        let mut contact_rows=0usize;
        for(slot,w)in self.weights.allocated(){if w.to_bits()!=0&&self.anatomy.geometry.contact(slot).is_some(){contact_rows=add_bytes(contact_rows,1)?;}}
        for(slot,changed)in self.contact_changes.allocated(){if *changed&&self.weights.get(slot).to_bits()==0&&self.anatomy.geometry.contact(slot).is_some(){contact_rows=add_bytes(contact_rows,1)?;}}
        let mut growth=0usize;
        // Fixed phase/ring anatomy is independent of the reached frontier.
        // Actual contact pages and indices are preadmitted at change_weights
        // inside the one aggregate max_staged_bytes envelope below.
        for n in [material_page_growth(&self.phases,NODES)?,material_page_growth(&self.rings,FACTS)?,
            checked_bytes(NODES-self.nonzero_nodes.len(),size_of::<u16>())?]{growth=add_bytes(growth,n)?;}
        // Pending inputs and delivery vectors can be rebuilt at the fixed port
        // capacity. Old capacities are retained in mutable, so adding the full
        // new capacities is conservative even when they replace old storage.
        growth=add_bytes(growth,checked_bytes(INPUTS,size_of::<PendingPower>())?)?;
        growth=add_bytes(growth,checked_bytes(2,size_of::<Delivery>())?)?;
        let immutable=add_bytes(add_bytes(anatomy,identity_bytes)?,add_bytes(history,fields)?)?;
        let mut peak=add_bytes(checked_bytes(add_bytes(mutable,growth)?,5)?,immutable)?;
        // Incoming immutable sources are admitted from actual register
        // payload by the owner; a configured ceiling is not occupied memory.
        peak=add_bytes(peak,admission.max_staged_bytes)?;
        // Inline trial/receipt containers above their included material state,
        // plus one actual millisecond's maximum terminal and thermal receipts.
        peak=add_bytes(peak,checked_bytes(3,size_of::<TrialStep>()-size_of::<Self>())?)?;
        peak=add_bytes(peak,size_of::<PreparedMaterial>()-size_of::<Self>())?;
        peak=add_bytes(peak,checked_bytes(TERMINALS,size_of::<TimedDischarge>())?)?;
        peak=add_bytes(peak,checked_bytes(self.anatomy.thermal_loads.len(),size_of::<PaidThermalWork>())?)?;
        peak=add_bytes(peak,size_of::<MaterialDrive>())?;
        Ok(MaterialLogicalSize{retained_material_bytes:retained,authentic_history_bytes:history,
            shared_field_payload_bound:fields,mounted_contact_source_rows:contact_rows,preparation_peak_bound:peak})
    }
}

#[path="functional64_current_commission.rs"] pub(crate) mod current_commission;
#[cfg(test)] #[path="functional64_material_tests.rs"] mod tests;

/// Only the bounded source registers are visited, never contacts/history.
/// Identity Arcs and complete field Arcs are counted once while the original
/// quarter and its private material successor coexist.
fn material_source_payload(material:&Functional64Material,original:&[Option<Arc<SharedJointField>>;2],
    input_power:&[PowerPacket],input_field:Option<(&Arc<SharedJointField>,&Arc<[u8]>)>)->Result<usize>{
    if material.delivery.len()>2||material.power.len()>INPUTS||input_power.len()>INPUTS{
        return Err(MaterialError::Capacity("source custody roster"));}
    let mut total=0usize;let mut field_ptrs=[0usize;5];let mut field_count=0usize;
    let mut field=|value:&Arc<SharedJointField>|->Result<()>{let key=Arc::as_ptr(value) as usize;
        if !field_ptrs[..field_count].contains(&key){field_ptrs[field_count]=key;field_count+=1;
            total=add_bytes(total,value.admitted_payload_bound())?;}Ok(())};
    for value in original.iter().flatten(){field(value)?;}
    for d in &material.delivery{field(&d.field)?;}
    if let Some((value,_))=input_field{field(value)?;}
    let mut identities=[(0usize,0usize);2*INPUTS+3];let mut count=0usize;
    for d in &material.delivery{material_add_identity(&d.identity,&mut identities,&mut count,&mut total)?;}
    for p in &material.power{material_add_identity(&p.packet.identity,&mut identities,&mut count,&mut total)?;}
    for p in input_power{material_add_identity(&p.identity,&mut identities,&mut count,&mut total)?;}
    if let Some((_,identity))=input_field{material_add_identity(identity,&mut identities,&mut count,&mut total)?;}
    Ok(total)
}

/// Immutable admission basis for ONE unpublished owner quarter. Source roots
/// prevent pointer reuse while deduplicating their complete immutable payload.
/// No contact cache or counter is added to canonical material/cold state.
#[derive(Clone,Debug)]
pub(crate) struct MaterialAllocationBasis{
    pub(crate) initial:MaterialLogicalSize,
    admission:Admission,
    original_fields:[Option<Arc<SharedJointField>>;2],
    fixed_preparation_payload:usize,
}
impl MaterialAllocationBasis{
    /// All five fixed material states and the one numerical/growth envelope;
    /// large immutable sources are charged separately from actual source roots.
    pub(crate) fn next_preparation_payload_bound(&self)->usize{self.fixed_preparation_payload}
    /// Source evaluation precedes numerical settlement. Only contact population
    /// already admitted by earlier intervals coexists at this stage.
    pub(crate) fn source_stage_material_payload(&self,prefix:usize)->Result<usize>{
        add_bytes(self.fixed_preparation_payload.checked_sub(self.admission.max_staged_bytes)
            .ok_or(MaterialError::Arithmetic("material stage envelope"))?,checked_bytes(prefix,5)?)
    }
    pub(crate) fn source_payload_bound(&self,current:&Functional64Material,
        incoming_field_payload:usize,incoming_identity_bytes:usize)->Result<usize>{
        add_bytes(material_source_payload(current,&self.original_fields,&[],None)?,
            add_bytes(incoming_field_payload,incoming_identity_bytes)?)
    }
    /// Earlier actual batches, including discarded trials, consume this same
    /// quarter-local envelope. The owner never serializes this accounting sum.
    pub(crate) fn next_admission(&self,actual_prefix_contact_growth_bytes:usize)->Result<Admission>{
        let mut admission=self.admission;
        admission.max_staged_bytes=admission.max_staged_bytes.checked_sub(checked_bytes(actual_prefix_contact_growth_bytes,5)?)
            .ok_or(MaterialError::Capacity("prepared actual contact allocation prefix"))?;
        Ok(admission)
    }
}
impl Functional64Material{
    pub(crate) fn allocation_basis(&self,admission:Admission)->Result<MaterialAllocationBasis>{
        let initial=self.logical_size(admission)?;
        let fixed_preparation_payload=initial.preparation_peak_bound.checked_sub(initial.shared_field_payload_bound)
            .ok_or(MaterialError::Arithmetic("material immutable source allocation"))?;
        let original_fields=std::array::from_fn(|i|self.delivery.get(i).map(|d|d.field.clone()));
        Ok(MaterialAllocationBasis{initial,admission,original_fields,fixed_preparation_payload})
    }
}

// Append-only observation method. Called explicitly, never by settlement.
impl Functional64Material {
    pub(crate) fn phase_pairs_le(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(2 * NODES * std::mem::size_of::<f64>());
        for node in 0..NODES {
            let p = self.phases.get(node);
            bytes.extend_from_slice(&p.send.to_bits().to_le_bytes());
            bytes.extend_from_slice(&p.receive.to_bits().to_le_bytes());
        }
        bytes
    }
}

// Explicit bounded endpoint observation only; no ordinary-path caller.
impl Functional64Material {
    pub(crate) fn retained_contact_evidence_le(&self, max_bytes: usize) -> Result<Vec<u8>> {
        if max_bytes == 0 {
            return Err(MaterialError::Capacity("contact observation byte admission must be positive"));
        }
        let row_count = self.source_contact_rows().try_fold(0usize, |n, _| {
            n.checked_add(1).ok_or(MaterialError::Capacity("contact observation row count"))
        })?;
        let byte_count = row_count.checked_mul(25)
            .ok_or(MaterialError::Capacity("contact observation byte count"))?;
        if byte_count > max_bytes {
            return Err(MaterialError::Capacity("complete contact observation exceeds byte admission"));
        }
        let mut bytes = Vec::with_capacity(byte_count);
        for row in self.source_contact_rows() {
            bytes.extend_from_slice(&row.authentic_slot.to_le_bytes());
            bytes.extend_from_slice(&row.from_node.to_le_bytes());
            bytes.extend_from_slice(&row.to_node.to_le_bytes());
            bytes.extend_from_slice(&row.signed_geometry.to_bits().to_le_bytes());
            bytes.extend_from_slice(&row.yield_threshold.to_bits().to_le_bytes());
            bytes.push(u8::from(row.plastic));
        }
        Ok(bytes)
    }
}
