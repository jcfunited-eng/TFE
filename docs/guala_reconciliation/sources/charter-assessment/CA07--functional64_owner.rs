//! One unpublished chronological material/body/source successor.
//! The host transports actual world and continuous cochlear consequences only.
//! No native callback, legacy action chooser, acoustic label or word credit.
use std::sync::Arc;
use crate::functional64_material::{Admission, Functional64Material, MaterialError,
    MaterialInputs, PaidThermalWork, PowerPacket, PreparedMaterial};
use crate::joint_uf_vector::{AdmissionBounds, ExactTime, UfError, evaluate_joint_source};
use crate::joint_uf_vector::physical_source::{SourceAnatomy, SourceAssembly, SourceBounds,
    OpticalAcquisition, CochlearObservation, SurfaceObservation, SourceObservation,
    RootInterval, RootWindow, power_for_next_millisecond, auditory_power_packets};
use crate::virtual_articulated_body::{ArticulatedBodyState, ArticulatedBodyError,
    BodyAnatomyProfile, BodyAxis, BodyEffectorDrive, BodyEffectorTerminal,
    AdmittedBodyEffectorDrives, settle_body_effector_drives};
use crate::virtual_articulatory_body::{ArticulatoryBodyError, settle_native_articulatory_interval};

const MAGIC:&[u8;8]=b"GL64OWN1";
const CONSTITUTION:&[u8]=b"complete64-owner:1ms-end-discharge;axis90-yaw2-x2-y2-resp1;v9;source10ms;self-pcm16-delay4000;beat250ms;work19-q1127";
pub(crate) const BEAT_MILLISECONDS:usize=250;
pub(crate) const PCM_BYTES:usize=8000;
const EAR_BYTES:usize=3156;
const MAX_DIGESTIBLE:u64=i64::MAX as u64;

#[derive(Debug)]
pub(crate) enum OwnerError{
    Invalid(&'static str), Capacity(&'static str), Arithmetic(&'static str),
    Payload{required:usize,limit:usize},
    Material(MaterialError), Source(UfError), Body(ArticulatedBodyError), Pressure(ArticulatoryBodyError),
}
type Result<T>=std::result::Result<T,OwnerError>;
impl From<MaterialError> for OwnerError{fn from(e:MaterialError)->Self{Self::Material(e)}}
impl From<UfError> for OwnerError{fn from(e:UfError)->Self{Self::Source(e)}}
impl From<ArticulatedBodyError> for OwnerError{fn from(e:ArticulatedBodyError)->Self{Self::Body(e)}}
impl From<ArticulatoryBodyError> for OwnerError{fn from(e:ArticulatoryBodyError)->Self{Self::Pressure(e)}}
fn add(a:usize,b:usize)->Result<usize>{a.checked_add(b).ok_or(OwnerError::Capacity("owner byte arithmetic"))}
fn count(a:u64,b:u64)->Result<u64>{a.checked_add(b).ok_or(OwnerError::Arithmetic("owner evidence count"))}
fn time(ms:i64)->Result<ExactTime>{let(mut a,mut b)=(ms.unsigned_abs(),1000u64);while b!=0{let r=a%b;a=b;b=r;}Ok(ExactTime::new(ms/(a as i64),1000/a)?)}
fn milliseconds(t:ExactTime)->Result<i64>{let(n,d)=t.parts();let n=(n as i128)*1000;
    if n%(d as i128)!=0{return Err(OwnerError::Invalid("material clock is not integral milliseconds"));}
    i64::try_from(n/(d as i128)).map_err(|_|OwnerError::Arithmetic("material millisecond clock"))}

#[derive(Clone,Copy)]
pub(crate) struct OwnerBounds{
    pub(crate) max_owner_bytes:usize,pub(crate) material:Admission,pub(crate) source:SourceBounds,
}
impl OwnerBounds{
    pub(crate) fn from_values(v:[usize;13])->Result<Self>{
        if v.contains(&0){return Err(OwnerError::Capacity("all actual resource bounds must be positive"));}
        let uf=AdmissionBounds{max_source_bytes:v[4],max_frames:v[5],max_vertices:v[6],
            max_group_members:v[7],max_contacts:v[8],max_payload_bytes:v[9]};
        Ok(Self{max_owner_bytes:v[0],material:Admission{max_force_terms:u64::try_from(v[1]).map_err(|_|OwnerError::Capacity("force bound"))?,
            max_yield_queries:u64::try_from(v[2]).map_err(|_|OwnerError::Capacity("yield bound"))?,max_staged_bytes:v[3],max_source_bytes:v[0]},
            source:SourceBounds{uf,max_record_bytes:v[10],max_integer_bytes:v[11],max_prepared_bytes:v[12]}})
    }
}

/// Bounds the existing GLCOCH01 mechanics without reimplementing its filter.
/// The actual Python CochlearStream.restore authenticates its existing checksum
/// and coefficient identity before this typed transport is called. Every byte,
/// including that checksum, is retained unchanged. No SHA validation is claimed here.
fn validate_ear(bytes:&[u8],origin:i64,at:i64)->Result<u64>{
    if bytes.len()!=EAR_BYTES||&bytes[..8]!=b"GLCOCH01"{return Err(OwnerError::Invalid("complete current continuous cochlea required"));}
    let sample=u64::from_le_bytes(bytes[40..48].try_into().unwrap());
    let elapsed=at.checked_sub(origin).ok_or(OwnerError::Arithmetic("ear origin clock"))?;
    if elapsed<0||u64::try_from(elapsed).ok().and_then(|n|n.checked_mul(16))!=Some(sample){return Err(OwnerError::Invalid("cochlear sample/current owner clock disagreement"));}
    // First caller observes at actual 10ms completions. A differently phased
    // incumbent requires a correspondingly phased owner, never silent padding.
    if sample%160!=0{return Err(OwnerError::Invalid("owner source cadence requires an actual cochlear completion boundary"));}
    for ear in 0..2{let base=48+ear*1538;let partial=u16::from_le_bytes(bytes[base..base+2].try_into().unwrap());
        if u64::from(partial)!=sample%160{return Err(OwnerError::Invalid("cochlear partial block clock"));}
        for index in 0..192{let start=base+2+8*index;let value=f64::from_bits(u64::from_le_bytes(bytes[start..start+8].try_into().unwrap()));
            if !value.is_finite()||(index>=176&&(value<0.0||(partial==0&&value!=0.0))){return Err(OwnerError::Invalid("cochlear current recurrence or block energy"));}}
    }Ok(sample)
}
fn thermal_identities(material:&Functional64Material)->Result<Vec<Arc<[u8]>>>{
    let loads=material.thermal_loads();
    if loads.len()!=1{return Err(OwnerError::Invalid("actual thermal source roster"));}
    let mut out=Vec::with_capacity(loads.len());
    for load in loads{if load.identity.len()!=56||&load.identity[..8]!=b"GL64TH01"||load.microwatts!=41_500_000
        ||u64::from_le_bytes(load.identity[48..56].try_into().unwrap())!=load.microwatts{return Err(OwnerError::Invalid("same-world thermal identity and actual power"));}
        out.push(load.identity.clone());}Ok(out)
}

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) struct AcquisitionGap{pub(crate) first_ms:i64,pub(crate) last_ms:i64}
#[derive(Clone,Default)]
struct SourceCoverage{admitted:u64,unacquired:u64,open:Option<AcquisitionGap>,last_closed:Option<AcquisitionGap>}
impl SourceCoverage{
    fn miss(&mut self,at:i64)->Result<()>{self.unacquired=count(self.unacquired,1)?;
        self.open=Some(match self.open{None=>AcquisitionGap{first_ms:at,last_ms:at},Some(g)=>{
            if g.last_ms.checked_add(10)!=Some(at){return Err(OwnerError::Invalid("source gap chronology"));}
            AcquisitionGap{first_ms:g.first_ms,last_ms:at}}});Ok(())}
    fn close(&mut self){if let Some(g)=self.open.take(){self.last_closed=Some(g);}}
}

#[derive(Clone)]
pub(crate) struct Functional64Owner{
    pub(crate) identity:Arc<str>,pub(crate) organism_tick:u64,
    material:Functional64Material,pub(crate) body:ArticulatedBodyState,
    source_anatomy:Arc<SourceAnatomy>,source:SourceAssembly,
    optical:Option<Arc<OpticalAcquisition>>,audio:Option<Arc<CochlearObservation>>,
    auditory_previous:Option<Arc<CochlearObservation>>,
    pending_terminals:[u64;97],roots:Vec<RootInterval>,coverage:SourceCoverage,
    pub(crate) cochlear_origin_ms:i64,pub(crate) cochlear_current:Arc<[u8]>,
    pub(crate) pending_self_pcm_s16le:Arc<[u8]>,pub(crate) unassimilated_digestible_micrograms:u64,
    pub(crate) bounds:OwnerBounds,
}
impl Functional64Owner{
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn commission(identity:Arc<str>,organism_tick:u64,material:Functional64Material,
        body:ArticulatedBodyState,source_anatomy:Arc<SourceAnatomy>,cochlear_origin_ms:i64,
        cochlear_current:Arc<[u8]>,pending_self_pcm_s16le:Arc<[u8]>,pending_terminals:[u64;97],
        unassimilated_digestible_micrograms:u64,bounds:OwnerBounds)->Result<Self>{
        let value=Self{identity,organism_tick,material,body,source:SourceAssembly::new(source_anatomy.clone()),source_anatomy,
            optical:None,audio:None,auditory_previous:None,pending_terminals,roots:Vec::new(),coverage:SourceCoverage::default(),
            cochlear_origin_ms,cochlear_current,pending_self_pcm_s16le,unassimilated_digestible_micrograms,bounds};
        value.validate_current()?;Ok(value)
    }
    pub(crate) fn source_millisecond(&self)->Result<i64>{milliseconds(self.material.clock())}
    pub(crate) fn reserve_micrograms(&self)->u64{self.material.source_reserve_micrograms()}
    pub(crate) fn reserve_capacity_micrograms(&self)->u64{self.material.source_anatomy().reserve_capacity_micrograms()}
    pub(crate) fn thermal_source_identities(&self)->Result<Vec<Arc<[u8]>>>{thermal_identities(&self.material)}
    fn validate_current(&self)->Result<()>{
        let at=self.source_millisecond()?;
        if self.identity.is_empty()||self.identity.len()>self.bounds.max_owner_bytes||self.body.profile()!=BodyAnatomyProfile::V9
            ||self.pending_self_pcm_s16le.len()!=PCM_BYTES||self.unassimilated_digestible_micrograms>MAX_DIGESTIBLE{
            return Err(OwnerError::Invalid("complete owner identity/body/FIFO/gut custody"));}
        validate_ear(&self.cochlear_current,self.cochlear_origin_ms,at)?;thermal_identities(&self.material)?;
        if let Some(optical)=&self.optical{if optical.available_millisecond()>at{return Err(OwnerError::Invalid("cold optical availability after current"));}}
        if let Some(audio)=&self.audio{if audio.time_ms!=at||audio.origin_ms!=self.cochlear_origin_ms{return Err(OwnerError::Invalid("cold latest actual cochlear completion"));}}
        if let Some(previous)=&self.auditory_previous{let current=self.audio.as_ref().ok_or(OwnerError::Invalid("missing pending auditory endpoint"))?;
            auditory_power_packets(previous,current,self.bounds.source)?;}
        if !self.roots.is_empty(){if self.roots.len()!=10{return Err(OwnerError::Invalid("cold complete root window"));}
            for(i,row)in self.roots.iter().enumerate(){if row.start_ms!=at.checked_sub(10-i as i64).ok_or(OwnerError::Arithmetic("root window clock"))?{
                return Err(OwnerError::Invalid("cold root sequence does not end at current"));}}}
        let last=self.source.latest_cochlear(self.bounds.source)?.map(|a|a.time_ms);
        if last.is_some_and(|t|t>at){return Err(OwnerError::Invalid("cold source follows current clock"));}
        if self.coverage.admitted<self.source.observations() as u64{return Err(OwnerError::Invalid("source admitted coverage count"));}
        for gap in [self.coverage.open,self.coverage.last_closed].into_iter().flatten(){
            if gap.first_ms>gap.last_ms||gap.last_ms>at||(gap.last_ms as i128-gap.first_ms as i128)%10!=0
                ||u64::try_from((gap.last_ms as i128-gap.first_ms as i128)/10+1).map_err(|_|OwnerError::Arithmetic("gap count"))?>self.coverage.unacquired{
                return Err(OwnerError::Invalid("cold source unavailable span"));}}
        if let Some(g)=self.coverage.open{if self.source.observations()!=46||g.last_ms!=at||last.is_none_or(|t|t>=g.first_ms){return Err(OwnerError::Invalid("cold saturated source coverage"));}}
        Ok(())
    }
    pub(crate) fn prepare_beat(&self,optical_record:Arc<[u8]>)->Result<PreparedBeat>{
        let fixed=add(std::mem::size_of::<PreparedBeat>(),add(PCM_BYTES,
            BEAT_MILLISECONDS.checked_mul(std::mem::size_of::<IntervalEvidence>()).ok_or(OwnerError::Capacity("fixed prepared interval evidence"))?)?)?;
        if fixed>self.bounds.source.max_prepared_bytes{return Err(OwnerError::Capacity("fixed prepared owner payload"));}
        self.organism_tick.checked_add(1).ok_or(OwnerError::Arithmetic("organism tick"))?;
        let start=self.source_millisecond()?;start.checked_add(BEAT_MILLISECONDS as i64).ok_or(OwnerError::Arithmetic("beat source clock"))?;
        // One actual material allocation scan per private quarter. Subsequent
        //1ms guards use this basis and admitted actual contact batch growth.
        let allocation_basis=self.material.allocation_basis(self.bounds.material)?;
        let source=self.source.logical_size(self.bounds.source,0)?;
        // History and full fields are shared immutable roots, charged once by
        // the basis. The original material shell/source/transport remain live.
        let original_native_payload=add(allocation_basis.initial.retained_material_bytes,
            add(source.retained_source_bytes,self.native_transport_payload()?)?)?;
        if optical_record.len()>self.bounds.source.max_record_bytes{return Err(OwnerError::Capacity("initial optical record admission"));}
        let mut opening=add(original_native_payload,add(source.retained_source_bytes,self.native_transport_payload()?)?)?;
        opening=add(opening,add(allocation_basis.source_stage_material_payload(0)?,allocation_basis.source_payload_bound(&self.material,0,0)?)?)?;
        opening=add(opening,add(self.native_private_workspace()?,optical_record.len())?)?;
        admit_native_payload(opening,self.bounds.max_owner_bytes)?;
        let optical=OpticalAcquisition::decode(optical_record,self.bounds.source)?;
        if optical.acquired_millisecond()!=start||optical.available_millisecond()!=start{return Err(OwnerError::Invalid("initial acquisition must belong to actual predecessor clock"));}
        let mut current=self.clone();current.optical=Some(optical);
        Ok(PreparedBeat{start,current,steps:0,last_source_step:0,pending:None,
            fifo:self.pending_self_pcm_s16le.to_vec(),summary:BeatSummary::new(start,self.reserve_micrograms()),
            intervals:Vec::with_capacity(BEAT_MILLISECONDS),finished:false,allocation_basis,original_native_payload,contact_growth_bytes:0})
    }
}

#[derive(Clone)]
pub(crate) struct MillisecondTransport{
    pub(crate) start_ms:i64,pub(crate) dx_mm:i32,pub(crate) dy_mm:i32,pub(crate) dyaw_mdeg:i32,
    pub(crate) left_grip_um:i32,pub(crate) right_grip_um:i32,pub(crate) jaw_um:i32,
    pub(crate) paid_thermal:Vec<PaidThermalWork>,pub(crate) own_ear_pcm:[u8;32],pub(crate) pressure_pcm:[u8;32],
}
struct PendingMillisecond{
    material:PreparedMaterial,voice:crate::virtual_articulatory_body::ArticulatoryBodyTransition,
    body_consequences:Vec<crate::virtual_articulated_body::BodyProprioceptiveConsequence>,
    terminals:[u64;97],source:SourceAssembly,coverage:SourceCoverage,
    transport:MillisecondTransport,field_delivered:bool,
}
// Complete replacement of the existing IntervalEvidence declaration/impl.
// Merge into the owner, not as an additional duplicate declaration.
#[derive(Clone)]
pub(crate) struct IntervalEvidence {
    pub(crate) powered_ticks: u64,
    pub(crate) numerical: [f64; 19],
    pub(crate) force_terms: u64,
    pub(crate) yield_queries: u64,
    pub(crate) staged_bytes: usize,
    // Actual END carrier transport for this already retained 1ms receipt.
    // Its timestamp is start_ms + receipt_index + 1, never a new clock.
    pub(crate) end_discharges: Box<[(u8, u64)]>,
}
impl IntervalEvidence {
    fn actual(p: &PreparedMaterial) -> Result<Self> {
        let e = p.evidence;
        let numerical = [e.supply_j,e.field_switch_j,e.source_heat_j,e.contact_heat_j,e.phase_heat_j,e.gate_heat_j,
            e.exported_j,e.plastic_heat_j,e.return_map_dissipation_j,e.stop_dissipation_j,e.energy_residual_j,
            e.nonlinear_bound,e.error_estimate,e.circuit_tail_charge_c,e.circuit_tail_work_j,e.circuit_projection_defect_v,
            e.contact_energy_change_j,e.contact_energy_change_lower_j,e.contact_energy_change_upper_j];
        if numerical.iter().any(|v| !v.is_finite()) || p.powered_offset.fractional_bits != 52
            || p.powered_offset.ticks > 1u64 << 52 || p.discharges.len() > 97 {
            return Err(OwnerError::Invalid("actual material interval evidence"));
        }
        let mut rows = Vec::with_capacity(p.discharges.len());
        let mut prior = None;
        for d in &p.discharges {
            if d.terminal >= 97 || d.carriers == 0 || d.at != p.successor.clock()
                || prior.is_some_and(|x| x >= d.terminal) {
                return Err(OwnerError::Invalid("actual ordered END discharge evidence"));
            }
            rows.push((d.terminal, d.carriers));
            prior = Some(d.terminal);
        }
        Ok(Self {
            powered_ticks: p.powered_offset.ticks, numerical,
            force_terms: p.work.force_terms, yield_queries: p.work.yield_queries,
            staged_bytes: p.work.staged_bytes, end_discharges: rows.into_boxed_slice(),
        })
    }
}

#[derive(Clone)]
pub(crate) struct BeatSummary{
    pub(crate) start_ms:i64,pub(crate) end_ms:i64,pub(crate) reserve_before:u64,pub(crate) reserve_after:u64,
    pub(crate) intake_micrograms:u64,pub(crate) assimilated_micrograms:u64,pub(crate) reserve_debited_micrograms:u64,
    pub(crate) debited_work:[u64;19],pub(crate) supplied_work:[u64;19],pub(crate) transducer_heat:[u64;19],
    pub(crate) recovered_field_work:[u64;19],pub(crate) paid_thermal:Vec<PaidThermalWork>,pub(crate) fields_delivered:u64,
    pub(crate) source_rows_admitted:u64,pub(crate) source_rows_unacquired:u64,
    pub(crate) articulatory_applied:u128,pub(crate) articulatory_stalled:u128,
    pub(crate) intervals:Arc<[IntervalEvidence]>,
}
fn limb_add(a:&mut[u64;19],b:&[u64;19])->Result<()>{let mut carry=0u128;
    for i in 0..19{let sum=a[i] as u128+b[i] as u128+carry;a[i]=sum as u64;carry=sum>>64;}
    if carry!=0{return Err(OwnerError::Arithmetic("exact interval work accumulation"));}Ok(())}
impl BeatSummary{
    fn new(start:i64,reserve:u64)->Self{Self{start_ms:start,end_ms:start,reserve_before:reserve,reserve_after:reserve,
        intake_micrograms:0,assimilated_micrograms:0,reserve_debited_micrograms:0,debited_work:[0;19],supplied_work:[0;19],transducer_heat:[0;19],
        recovered_field_work:[0;19],paid_thermal:Vec::new(),fields_delivered:0,source_rows_admitted:0,source_rows_unacquired:0,
        articulatory_applied:0,articulatory_stalled:0,intervals:Arc::from([])}}
    fn paid(&mut self,rows:&[PaidThermalWork])->Result<()>{
        if self.paid_thermal.is_empty(){self.paid_thermal=rows.to_vec();return Ok(());}
        if self.paid_thermal.len()!=rows.len(){return Err(OwnerError::Invalid("thermal source roster changed during beat"));}
        for(a,b)in self.paid_thermal.iter_mut().zip(rows){if a.identity!=b.identity{return Err(OwnerError::Invalid("thermal identity changed during beat"));}limb_add(&mut a.units,&b.units)?;}Ok(())
    }
}
pub(crate) struct PreparedBeat{
    start:i64,current:Functional64Owner,steps:usize,last_source_step:usize,pending:Option<PendingMillisecond>,
    fifo:Vec<u8>,summary:BeatSummary,intervals:Vec<IntervalEvidence>,finished:bool,
    allocation_basis:crate::functional64_material::MaterialAllocationBasis,original_native_payload:usize,
    contact_growth_bytes:usize,
}
impl PreparedBeat{
    pub(crate) fn source_due(&self)->bool{!self.finished&&self.steps>0&&self.steps%10==0&&self.last_source_step!=self.steps}
    pub(crate) fn source_millisecond(&self)->Result<i64>{self.current.source_millisecond()}
    pub(crate) fn body(&self)->&ArticulatedBodyState{&self.current.body}
    fn open(&self)->Result<()>{if self.finished{Err(OwnerError::Invalid("prepared beat already finished"))}else{Ok(())}}
    pub(crate) fn prepare_millisecond(&mut self)->Result<MillisecondTransport>{
        self.open()?;
        if self.pending.is_some()||self.source_due()||self.steps>=BEAT_MILLISECONDS{return Err(OwnerError::Invalid("millisecond/world/source ordering"));}
        self.admit_next_material_interval()?;
        let at=self.current.source_millisecond()?;let end=at.checked_add(1).ok_or(OwnerError::Arithmetic("millisecond successor"))?;
        let optical=self.current.optical.as_ref().ok_or(OwnerError::Invalid("actual optical acquisition unavailable"))?;
        let mut power=power_for_next_millisecond(optical,&self.current.body,self.current.roots.last(),time(at)?,self.current.bounds.source)?;
        if let Some(previous)=&self.current.auditory_previous{let current=self.current.audio.as_ref().ok_or(OwnerError::Invalid("auditory pending current"))?;
            power.extend(auditory_power_packets(previous,current,self.current.bounds.source)?);}
        let mut source=self.current.source.clone();let mut coverage=self.current.coverage.clone();let mut field_delivered=false;
        let field=if source.observations()==46&&self.current.material.can_accept_field(){
            let(complete,overlap)=source.complete(self.current.bounds.source)?;
            let first=milliseconds(complete.frames.first().ok_or(OwnerError::Invalid("complete source empty"))?.time)?;
            let last=milliseconds(complete.frames.last().ok_or(OwnerError::Invalid("complete source empty"))?.time)?;
            let mut identity=Vec::new();identity.extend_from_slice(b"GL64FD01");identity.extend_from_slice(&(self.current.identity.len() as u64).to_le_bytes());
            identity.extend_from_slice(self.current.identity.as_bytes());identity.extend_from_slice(&first.to_le_bytes());identity.extend_from_slice(&last.to_le_bytes());
            let field=evaluate_joint_source(complete,self.current.bounds.source.uf)?;
            source=if coverage.open.is_some(){coverage.close();SourceAssembly::new(self.current.source_anatomy.clone())}else{overlap};
            field_delivered=true;Some((field,Arc::from(identity),time(at)?))
        }else{None};
        let material=self.current.material.prepare_boundary(MaterialInputs{start:time(at)?,end:time(end)?,
            actual_reserve_ug:self.current.reserve_micrograms(),power,field,admission:self.allocation_basis.next_admission(self.contact_growth_bytes)?})?;
        let mut terminals=[0u64;97];for discharge in &material.discharges{
            let index=discharge.terminal as usize;if index>=97||discharge.at!=time(end)?||discharge.carriers==0||terminals[index]!=0{return Err(OwnerError::Invalid("actual terminal END discharge"));}
            terminals[index]=discharge.carriers;}
        let p=&self.current.pending_terminals;let mut drives=Vec::new();
        for(index,&carriers)in p[..90].iter().enumerate(){if carriers!=0{drives.push(BodyEffectorDrive{
            terminal:BodyEffectorTerminal::from_ordinals((index/2) as u8,(index%2) as u8).ok_or(OwnerError::Invalid("body terminal topology"))?,outward_elementary_carriers:carriers as u128});}}
        let drives=AdmittedBodyEffectorDrives::admit(drives)?;
        let motion=settle_body_effector_drives(&self.current.body,&drives,1000)?;
        let voice=settle_native_articulatory_interval(motion.successor,&motion.proprioceptive_consequences,p[96] as u128,16)?;
        if voice.radiated_pressure_pcm.len()!=16{return Err(OwnerError::Invalid("actual 1ms tract pressure sample clock"));}
        let mut pressure=[0;32];for(i,sample)in voice.radiated_pressure_pcm.iter().enumerate(){pressure[2*i..2*i+2].copy_from_slice(&sample.to_le_bytes());}
        let own_ear_pcm=self.fifo[self.steps*32..(self.steps+1)*32].try_into().unwrap();
        let signed=|negative:u64,positive:u64|i32::try_from(positive as i128-negative as i128).map_err(|_|OwnerError::Arithmetic("actual root count exceeds declared world displacement domain"));
        let transport=MillisecondTransport{start_ms:at,dx_mm:signed(p[92],p[93])?,dy_mm:signed(p[94],p[95])?,dyaw_mdeg:signed(p[90],p[91])?,
            left_grip_um:voice.successor_body.axis(BodyAxis::LeftGripAperture),right_grip_um:voice.successor_body.axis(BodyAxis::RightGripAperture),
            jaw_um:voice.successor_body.axis(BodyAxis::JawOpening),paid_thermal:material.paid_thermal.clone(),own_ear_pcm,pressure_pcm:pressure};
        self.pending=Some(PendingMillisecond{material,voice,body_consequences:motion.proprioceptive_consequences,
            terminals,source,coverage,transport:transport.clone(),field_delivered});
        Ok(transport)
    }
    pub(crate) fn accept_world(&mut self,root_record:&[u8],intake:u64)->Result<()>{
        self.open()?;let pending=self.pending.as_ref().ok_or(OwnerError::Invalid("no prepared millisecond to acknowledge"))?;
        let root=RootInterval::decode(root_record,self.current.bounds.source)?;
        if root.start_ms!=pending.transport.start_ms||intake>MAX_DIGESTIBLE{return Err(OwnerError::Invalid("world intake/root successor clock"));}
        let gut=self.current.unassimilated_digestible_micrograms.checked_add(intake).filter(|&n|n<=MAX_DIGESTIBLE).ok_or(OwnerError::Arithmetic("conserved digestive stock"))?;
        // Clone is COW; fallible assimilation/evidence precede adopting scratch.
        let assimilation=pending.material.successor.clone().prepare_assimilation(gut)?;
        let mut summary=self.summary.clone();summary.end_ms=root.start_ms.checked_add(1).ok_or(OwnerError::Arithmetic("world end clock"))?;
        summary.intake_micrograms=count(summary.intake_micrograms,intake)?;summary.assimilated_micrograms=count(summary.assimilated_micrograms,assimilation.assimilated_ug)?;
        summary.reserve_debited_micrograms=count(summary.reserve_debited_micrograms,pending.material.reserve_consumed_ug)?;
        summary.reserve_after=assimilation.successor.source_reserve_micrograms();
        limb_add(&mut summary.debited_work,&pending.material.debited_work)?;limb_add(&mut summary.supplied_work,&pending.material.supplied_work_units)?;
        limb_add(&mut summary.transducer_heat,&pending.material.transducer_heat_units)?;summary.paid(&pending.material.paid_thermal)?;
        limb_add(&mut summary.recovered_field_work,&pending.material.recovered_field_work)?;
        let interval=IntervalEvidence::actual(&pending.material)?;
        if pending.field_delivered{summary.fields_delivered=count(summary.fields_delivered,1)?;}
        summary.articulatory_applied=summary.articulatory_applied.checked_add(pending.voice.applied_motor_quanta).ok_or(OwnerError::Arithmetic("articulatory applied evidence"))?;
        summary.articulatory_stalled=summary.articulatory_stalled.checked_add(pending.voice.stalled_motor_quanta).ok_or(OwnerError::Arithmetic("articulatory stalled evidence"))?;
        let contact_growth_bytes=add(self.contact_growth_bytes,pending.material.work.contact_growth_bytes)?;
        self.allocation_basis.next_admission(contact_growth_bytes)?;
        let pending=self.pending.take().unwrap();
        self.current.material=assimilation.successor;self.current.unassimilated_digestible_micrograms=assimilation.remaining_digestible_ug;
        self.current.body=pending.voice.successor_body;self.current.pending_terminals=pending.terminals;self.current.source=pending.source;self.current.coverage=pending.coverage;
        self.intervals.push(interval);self.contact_growth_bytes=contact_growth_bytes;
        self.current.auditory_previous=None;
        if self.current.roots.len()==10{self.current.roots.remove(0);}self.current.roots.push(root);
        self.fifo[self.steps*32..(self.steps+1)*32].copy_from_slice(&pending.transport.pressure_pcm);
        self.steps+=1;self.summary=summary;Ok(())
    }
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn accept_source(&mut self,audio_record:&[u8],optical_record:Arc<[u8]>,surface_ratios:Arc<[u8]>,
        surface_evidence:Arc<[u8]>,skin_ratio:Arc<[u8]>,received_covered:bool,own_covered:bool)->Result<()>{
        self.open()?;if self.pending.is_some()||!self.source_due(){return Err(OwnerError::Invalid("source completion outside its actual 10ms boundary"));}
        let admitted_contacts=self.admit_actual_source_observation(&[audio_record.len(),optical_record.len(),
            surface_ratios.len(),surface_evidence.len(),skin_ratio.len()])?;
        let at=self.current.source_millisecond()?;let audio=Arc::new(CochlearObservation::decode(audio_record,self.current.bounds.source)?);
        if audio.time_ms!=at||audio.origin_ms!=self.current.cochlear_origin_ms{return Err(OwnerError::Invalid("actual source cochlear current clock"));}
        if let Some(previous)=&self.current.audio{auditory_power_packets(previous,&audio,self.current.bounds.source)?;}
        let optical=OpticalAcquisition::decode(optical_record,self.current.bounds.source)?;
        if optical.acquired_millisecond()!=at||optical.available_millisecond()!=at{return Err(OwnerError::Invalid("endpoint optical acquisition clock"));}
        if !received_covered||!own_covered{return Err(OwnerError::Invalid("actual contact-event coverage unavailable"));}
        for record in [&surface_ratios,&surface_evidence,&skin_ratio]{if record.len()>self.current.bounds.source.max_record_bytes{return Err(OwnerError::Capacity("actual surface return bytes"));}}
        let mut coverage=self.current.coverage.clone();let mut summary=self.summary.clone();
        let source=if self.current.source.observations()==46{
            coverage.miss(at)?;summary.source_rows_unacquired=count(summary.source_rows_unacquired,1)?;self.current.source.clone()
        }else{
            let intervals:[RootInterval;10]=self.current.roots.clone().try_into().map_err(|_|OwnerError::Invalid("actual ten-millisecond root window unavailable"))?;
            let root=RootWindow{intervals};let surface=SurfaceObservation{start_ms:at.checked_sub(10).ok_or(OwnerError::Arithmetic("surface clock"))?,end_ms:at,
                received_covered,own_covered,ratios:surface_ratios,evidence:surface_evidence,skin_millikelvin:skin_ratio};
            let view=self.current.material.material_view()?;
            if admitted_contacts!=Some(view.contact_rows.len()){return Err(OwnerError::Invalid("actual source roster changed after admission"));}
            let row=SourceObservation::from_actual(&self.current.source_anatomy,optical.clone(),&audio,&self.current.body,&root,&surface,&view,self.current.bounds.source)?;
            let source=self.current.source.prepare_append(row,self.current.bounds.source)?;
            coverage.admitted=count(coverage.admitted,1)?;summary.source_rows_admitted=count(summary.source_rows_admitted,1)?;source
        };
        self.current.auditory_previous=self.current.audio.clone();self.current.audio=Some(audio);self.current.optical=Some(optical);
        self.current.source=source;self.current.coverage=coverage;self.summary=summary;self.last_source_step=self.steps;Ok(())
    }
    pub(crate) fn finish(&mut self,ear:Arc<[u8]>)->Result<(Functional64Owner,Arc<[u8]>,BeatSummary)>{
        self.open()?;if self.steps!=BEAT_MILLISECONDS||self.pending.is_some()||self.source_due(){return Err(OwnerError::Invalid("incomplete chronological quarter"));}
        let at=self.current.source_millisecond()?;
        if self.start.checked_add(BEAT_MILLISECONDS as i64)!=Some(at){return Err(OwnerError::Invalid("beat clock changed"));}
        validate_ear(&ear,self.current.cochlear_origin_ms,at)?;
        let mut next=self.current.clone();next.organism_tick=next.organism_tick.checked_add(1).ok_or(OwnerError::Arithmetic("organism tick"))?;
        next.cochlear_current=ear;next.pending_self_pcm_s16le=self.fifo.clone().into();next.validate_current()?;
        let mut summary=self.summary.clone();summary.intervals=self.intervals.clone().into();
        self.finished=true;Ok((next.clone(),next.pending_self_pcm_s16le.clone(),summary))
    }
}

struct Writer{bytes:Vec<u8>,limit:usize}
impl Writer{
    fn put(&mut self,b:&[u8])->Result<()>{if add(self.bytes.len(),b.len())?>self.limit{return Err(OwnerError::Capacity("complete owner encoding"));}self.bytes.extend_from_slice(b);Ok(())}
    fn u64(&mut self,n:u64)->Result<()>{self.put(&n.to_le_bytes())}
    fn i64(&mut self,n:i64)->Result<()>{self.put(&n.to_le_bytes())}
    fn blob(&mut self,b:&[u8])->Result<()>{self.u64(b.len() as u64)?;self.put(b)}
    fn gap(&mut self,g:Option<AcquisitionGap>)->Result<()>{self.put(&[u8::from(g.is_some())])?;if let Some(g)=g{self.i64(g.first_ms)?;self.i64(g.last_ms)?;}Ok(())}
}
struct Reader<'a>{bytes:&'a[u8],at:usize}
impl<'a> Reader<'a>{
    fn take(&mut self,n:usize)->Result<&'a[u8]>{let end=add(self.at,n)?;if end>self.bytes.len(){return Err(OwnerError::Invalid("truncated complete owner"));}let b=&self.bytes[self.at..end];self.at=end;Ok(b)}
    fn u64(&mut self)->Result<u64>{Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))}
    fn i64(&mut self)->Result<i64>{Ok(i64::from_le_bytes(self.take(8)?.try_into().unwrap()))}
    fn blob(&mut self,limit:usize)->Result<&'a[u8]>{let n=usize::try_from(self.u64()?).map_err(|_|OwnerError::Capacity("owner blob width"))?;if n>limit{return Err(OwnerError::Capacity("owner blob admission"));}self.take(n)}
    fn flag(&mut self)->Result<bool>{match self.take(1)?[0]{0=>Ok(false),1=>Ok(true),_=>Err(OwnerError::Invalid("noncanonical custody flag"))}}
    fn gap(&mut self)->Result<Option<AcquisitionGap>>{Ok(if self.flag()?{Some(AcquisitionGap{first_ms:self.i64()?,last_ms:self.i64()?})}else{None})}
}
impl Functional64Owner{
    pub(crate) fn encode(&self)->Result<Vec<u8>>{
        self.validate_current()?;
        let b=self.bounds;let mut w=Writer{bytes:Vec::new(),limit:b.max_owner_bytes};
        w.put(MAGIC)?;w.blob(CONSTITUTION)?;w.blob(self.identity.as_bytes())?;w.u64(self.organism_tick)?;
        w.blob(&self.material.encode(b.max_owner_bytes,b.source.uf)?)?;w.blob(&self.body.encode()?)?;
        w.blob(&self.source.encode_custody(b.source)?)?;
        let shared=self.source.latest_optical();
        match &self.optical{None=>w.put(&[0])?,Some(value)=>{
            if shared.as_ref().is_some_and(|s|s.encoded().as_ref()==value.encoded().as_ref()){w.put(&[1])?;}
            else{w.put(&[2])?;w.blob(value.encoded())?;}}}
        let shared_audio=self.source.latest_cochlear(b.source)?.map(|a|a.encoded(b.source)).transpose()?;
        match &self.audio{None=>w.put(&[0])?,Some(value)=>{let raw=value.encoded(b.source)?;
            if shared_audio.as_ref().is_some_and(|s|s.as_ref()==raw.as_ref()){w.put(&[1])?;}
            else{w.put(&[2])?;w.blob(&raw)?;}}}
        w.put(&[u8::from(self.auditory_previous.is_some())])?;if let Some(a)=&self.auditory_previous{w.blob(&a.encoded(b.source)?)?;}
        for value in self.pending_terminals{w.u64(value)?;}w.u64(self.roots.len() as u64)?;for row in &self.roots{w.blob(&row.encoded(b.source)?)?;}
        w.u64(self.coverage.admitted)?;w.u64(self.coverage.unacquired)?;w.gap(self.coverage.open)?;w.gap(self.coverage.last_closed)?;
        w.i64(self.cochlear_origin_ms)?;w.blob(&self.cochlear_current)?;w.blob(&self.pending_self_pcm_s16le)?;w.u64(self.unassimilated_digestible_micrograms)?;Ok(w.bytes)
    }
    pub(crate) fn decode(bytes:&[u8],geometry:Arc<[u8]>,surface_sites:usize,b:OwnerBounds)->Result<Self>{
        if bytes.len()>b.max_owner_bytes{return Err(OwnerError::Capacity("complete owner decode admission"));}
        let mut r=Reader{bytes,at:0};if r.take(8)?!=MAGIC||r.blob(b.max_owner_bytes)?!=CONSTITUTION{return Err(OwnerError::Invalid("complete owner constitution"));}
        let identity:Arc<str>=std::str::from_utf8(r.blob(b.max_owner_bytes)?).map_err(|_|OwnerError::Invalid("owner identity UTF8"))?.into();let organism_tick=r.u64()?;
        let material=Functional64Material::decode(r.blob(b.max_owner_bytes)?,b.max_owner_bytes,b.source.uf)?;
        let body=ArticulatedBodyState::decode(r.blob(b.max_owner_bytes)?)?;
        let source_anatomy=SourceAnatomy::new(geometry,surface_sites,&body,material.source_anatomy(),b.source)?;
        let source=SourceAssembly::decode_custody(r.blob(b.source.uf.max_source_bytes)?,source_anatomy.clone(),b.source)?;
        let optical=match r.take(1)?[0]{0=>None,1=>Some(source.latest_optical().ok_or(OwnerError::Invalid("cold optical reference missing"))?),
            2=>Some(OpticalAcquisition::decode(r.blob(b.source.max_record_bytes)?.into(),b.source)?),_=>return Err(OwnerError::Invalid("cold optical reference tag"))};
        let audio=match r.take(1)?[0]{0=>None,1=>Some(Arc::new(source.latest_cochlear(b.source)?.ok_or(OwnerError::Invalid("cold cochlear reference missing"))?)),
            2=>Some(Arc::new(CochlearObservation::decode(r.blob(b.source.max_record_bytes)?,b.source)?)),_=>return Err(OwnerError::Invalid("cold cochlear reference tag"))};
        let auditory_previous=if r.flag()?{Some(Arc::new(CochlearObservation::decode(r.blob(b.source.max_record_bytes)?,b.source)?))}else{None};
        let mut pending_terminals=[0;97];for value in &mut pending_terminals{*value=r.u64()?;}
        let n=usize::try_from(r.u64()?).map_err(|_|OwnerError::Capacity("root count"))?;if n!=0&&n!=10{return Err(OwnerError::Invalid("retained root window count"));}
        let mut roots=Vec::with_capacity(n);for _ in 0..n{roots.push(RootInterval::decode(r.blob(b.source.max_record_bytes)?,b.source)?);}
        let coverage=SourceCoverage{admitted:r.u64()?,unacquired:r.u64()?,open:r.gap()?,last_closed:r.gap()?};
        let cochlear_origin_ms=r.i64()?;let cochlear_current=r.blob(EAR_BYTES)?.into();let pending_self_pcm_s16le=r.blob(PCM_BYTES)?.into();let unassimilated_digestible_micrograms=r.u64()?;
        if r.at!=bytes.len(){return Err(OwnerError::Invalid("trailing complete owner bytes"));}
        let value=Self{identity,organism_tick,material,body,source_anatomy,source,optical,audio,auditory_previous,pending_terminals,roots,coverage,
            cochlear_origin_ms,cochlear_current,pending_self_pcm_s16le,unassimilated_digestible_micrograms,bounds:b};
        value.validate_current()?;
        // Ordinary decoding validates canonical reference choice; it never
        // regenerates a material/source/body history by commissioning.
        if value.encode()?.as_slice()!=bytes{return Err(OwnerError::Invalid("noncanonical complete owner custody"));}Ok(value)
    }
}

impl PreparedBeat{
    pub(crate) fn record_byte_limit(&self)->usize{self.current.bounds.source.max_record_bytes}
    pub(crate) fn prepared_body_evidence(&self)->Result<(&crate::virtual_articulatory_body::ArticulatoryBodyTransition,
        &[crate::virtual_articulated_body::BodyProprioceptiveConsequence])>{
        self.open()?;let pending=self.pending.as_ref().ok_or(OwnerError::Invalid("no prepared body interval"))?;
        Ok((&pending.voice,&pending.body_consequences))
    }
}
impl Functional64Owner{
    /// Logical payload and declared work bounds. This does not claim allocator
    /// overhead, RSS, or proof that the host's available memory admits this plan.
    pub(crate) fn resource_sizing(&self)->Result<Vec<(&'static str,usize)>>{
        let material=self.material.logical_size(self.bounds.material)?;
        let source=self.source.logical_size(self.bounds.source,material.mounted_contact_source_rows)?;
        let mul=|a:usize,b:usize|a.checked_mul(b).ok_or(OwnerError::Capacity("owner resource multiplication"));
        let fixed=add(std::mem::size_of::<Self>(),add(self.identity.len(),add(EAR_BYTES,PCM_BYTES)? )?)?;
        let root_bytes=self.roots.iter().try_fold(0usize,|n,r|add(n,add(std::mem::size_of::<RootInterval>(),r.evidence.len())?))?;
        let current_optical=self.optical.as_ref().map_or(0,|o|o.encoded().len());
        let current_audio=[self.audio.as_ref(),self.auditory_previous.as_ref()].into_iter().flatten().try_fold(0usize,|n,a|
            add(n,add(std::mem::size_of::<CochlearObservation>(),a.acquisition_evidence.len())?))?;
        let fixed=add(fixed,add(root_bytes,add(current_optical,current_audio)?)?)?;
        let interval_evidence=add(mul(2*BEAT_MILLISECONDS,std::mem::size_of::<IntervalEvidence>())?,mul(2*BEAT_MILLISECONDS*97,std::mem::size_of::<(u8,u64)>())?)?;
        let body_scratch=add(mul(3,std::mem::size_of::<ArticulatedBodyState>())?,
            add(mul(45,std::mem::size_of::<crate::virtual_articulated_body::BodyProprioceptiveConsequence>())?,mul(5*16,2)?)?)?;
        // Current occupied source only. Future acquisitions are admitted when
        // present, not charged as two maximum-capacity imaginary fields.
        let material_stage=add(material.preparation_peak_bound,source.retained_source_bytes)?;
        let source_stage=add(owner_material_resident(&material)?,source.preparation_peak_bound)?;
        let peak=add(material_stage.max(source_stage),add(mul(2,fixed)?,add(PCM_BYTES,add(interval_evidence,body_scratch)?)?)?)?;
        Ok(vec![("retained_material_bytes",material.retained_material_bytes),("authentic_history_bytes",material.authentic_history_bytes),
            ("shared_field_payload_bound",material.shared_field_payload_bound),("mounted_contact_source_rows",material.mounted_contact_source_rows),
            ("material_preparation_peak_bound",material.preparation_peak_bound),("retained_source_bytes",source.retained_source_bytes),
            ("next_observation_payload_bound",source.next_observation_payload_bound),("complete_source_snapshot_payload_bound",source.complete_source_snapshot_payload_bound),
            ("complete_field_payload_bound",source.complete_field_payload_bound),("source_preparation_peak_bound",source.preparation_peak_bound),
            ("owner_transport_payload_bound",fixed),("owner_preparation_payload_bound",peak)])
    }
}

// Native logical admission only. Python/world/cgroup/allocator budgets remain
// separate. All arithmetic is before creation of the unpublished next state.
fn owner_product(a:usize,b:usize)->Result<usize>{a.checked_mul(b).ok_or(OwnerError::Capacity("owner admission product"))}
fn owner_material_resident(m:&crate::functional64_material::MaterialLogicalSize)->Result<usize>{
    add(m.retained_material_bytes,add(m.authentic_history_bytes,m.shared_field_payload_bound)?)
}
fn admit_native_payload(bytes:usize,limit:usize)->Result<()>{
    if bytes>limit{Err(OwnerError::Payload{required:bytes,limit})}else{Ok(())}
}
impl Functional64Owner{
    fn native_transport_payload(&self)->Result<usize>{
        let mut n=add(std::mem::size_of::<Self>(),add(self.identity.len(),add(self.cochlear_current.len(),self.pending_self_pcm_s16le.len())?)?)?;
        n=add(n,owner_product(self.roots.capacity(),std::mem::size_of::<RootInterval>())?)?;
        for r in &self.roots{n=add(n,r.evidence.len())?;}
        if let Some(o)=&self.optical{n=add(n,add(std::mem::size_of::<OpticalAcquisition>(),o.encoded().len())?)?;}
        for a in [self.audio.as_ref(),self.auditory_previous.as_ref()].into_iter().flatten(){n=add(n,add(std::mem::size_of::<CochlearObservation>(),a.acquisition_evidence.len())?)?;}
        Ok(n)
    }
    fn native_private_workspace(&self)->Result<usize>{
        let mut n=add(std::mem::size_of::<PreparedBeat>(),PCM_BYTES)?;
        // Private interval Vec and final Arc receipt can coexist at finish.
        n=add(n,owner_product(2*BEAT_MILLISECONDS,std::mem::size_of::<IntervalEvidence>())?)?;
        // Original receipt Vec and finish clone/Arc own two copies of
        // each sparse END payload. No prior receipt is cloned per1ms.
        n=add(n,owner_product(2*BEAT_MILLISECONDS*97,std::mem::size_of::<(u8,u64)>())?)?;
        n=add(n,owner_product(3,std::mem::size_of::<ArticulatedBodyState>())?)?;
        n=add(n,owner_product(2*90,std::mem::size_of::<BodyEffectorDrive>())?)?;
        n=add(n,owner_product(2*45,std::mem::size_of::<crate::virtual_articulated_body::BodyProprioceptiveConsequence>())?)?;
        n=add(n,5*16*2)?;
        // Actual fixed receptor/output roster, with Vec growth capacity.
        n=add(n,owner_product(2*608,std::mem::size_of::<PowerPacket>())?)?;
        n=add(n,owner_product(4,self.bounds.source.max_record_bytes)?)?;
        n=add(n,owner_product(4,std::mem::size_of::<PaidThermalWork>())?)?;
        n=add(n,owner_product(2,std::mem::size_of::<BeatSummary>())?)?;
        Ok(n)
    }
}
impl PreparedBeat{
    fn admit_next_material_interval(&self)->Result<()>{
        self.allocation_basis.next_admission(self.contact_growth_bytes)?;
        let b=self.current.bounds;
        // Only bounded source/packet metadata is visited at1ms. No material
        // contact/history scan and no hypothetical allowed-query population.
        let source=self.current.source.logical_size(b.source,0)?;
        let mut common=add(self.original_native_payload,add(source.retained_source_bytes,self.current.native_transport_payload()?)?)?;
        common=add(common,self.current.native_private_workspace()?)?;
        let occupied=self.allocation_basis.source_payload_bound(&self.current.material,0,0)?;
        let mut numerical=add(self.allocation_basis.next_preparation_payload_bound(),occupied)?;
        let mut source_stage=0usize;
        if self.current.source.observations()==46&&self.current.material.can_accept_field(){
            let snapshot=self.current.source.actual_snapshot_size(true,b.source)?;
            let identity=add(32,self.current.identity.len())?;
            numerical=add(numerical,add(snapshot.field_payload,identity)?)?;
            source_stage=add(self.allocation_basis.source_stage_material_payload(self.contact_growth_bytes)?,
                add(occupied,add(snapshot.preparation_payload,identity)?)?)?;
        }
        admit_native_payload(add(common,numerical.max(source_stage))?,b.max_owner_bytes)
    }
    fn admit_actual_source_observation(&self,records:&[usize])->Result<Option<usize>>{
        for &n in records{if n>self.current.bounds.source.max_record_bytes{return Err(OwnerError::Capacity("actual source record admission"));}}
        // This one scan occurs at the actual10ms source boundary, where the
        // complete retained contact roster is itself a required observation.
        let material=self.current.material.logical_size(self.current.bounds.material)?;
        let append=self.current.source.observations()<46;
        let contacts=if append{material.mounted_contact_source_rows}else{0};
        let source=self.current.source.logical_size(self.current.bounds.source,contacts)?;
        let occupied=self.allocation_basis.source_payload_bound(&self.current.material,0,0)?;
        let actual_material=add(material.retained_material_bytes,add(material.authentic_history_bytes,occupied)?)?;
        let mut peak=add(self.original_native_payload,add(actual_material,add(source.retained_source_bytes,self.current.native_transport_payload()?)?)?)?;
        peak=add(peak,self.current.native_private_workspace()?)?;
        for &n in records{peak=add(peak,n)?;}
        if append{
            peak=add(peak,add(source.next_observation_payload_bound,source.next_observation_preparation_bound)?)?;
            let raw=self.current.material.source_anatomy().raw_coordinate_count();
            peak=add(peak,owner_product(raw,std::mem::size_of::<f64>())?)?;
            peak=add(peak,owner_product(owner_product(2,contacts)?,std::mem::size_of::<crate::functional64_material::MaterialContactView>())?)?;
        }
        admit_native_payload(peak,self.current.bounds.max_owner_bytes)?;
        Ok(if append{Some(contacts)}else{None})
    }
}

#[cfg(test)]
#[path="functional64_owner_tests.rs"]
mod tests;

// Append-only explicit observation. No checkpoint, phase/contact mutation or
// history scan. The immutable PyCore pins one owner across all three getters.
impl Functional64Owner {
    pub(crate) fn phase_pairs_le(&self) -> Vec<u8> {
        self.material.phase_pairs_le()
    }
    pub(crate) fn pending_terminal_carriers(&self) -> &[u64; 97] {
        &self.pending_terminals
    }
    pub(crate) fn field_delivery_evidence(&self)
        -> impl Iterator<Item = crate::functional64_material::DeliveryView<'_>> {
        self.material.delivery_view()
    }
}

// Explicit bounded endpoint observation; no current mutation or hot caller.
impl Functional64Owner {
    pub(crate) fn retained_contact_evidence(&self, max_bytes: usize) -> Result<(i64, Vec<u8>)> {
        if max_bytes == 0 || max_bytes > self.bounds.source.max_record_bytes {
            return Err(OwnerError::Capacity("contact observation exceeds admitted source record limit"));
        }
        let at = self.source_millisecond()?;
        let bytes = self.material.retained_contact_evidence_le(max_bytes)?;
        Ok((at, bytes))
    }
}
