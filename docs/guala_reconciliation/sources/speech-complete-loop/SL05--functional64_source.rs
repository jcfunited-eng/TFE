//! Actual source assembly inside the single complete organism owner.
//! Authority: collaborative_todo.md active functional64 source contract.
//! No world publication, source acquisition, kernel law or independent brain
//! lives here. Missing physical input is an error, never a manufactured zero.

use std::collections::BTreeMap;
use std::ops::Range;
use std::sync::Arc;
use crate::joint_uf_vector::{AdmissionBounds, ContactSample, CoordinateDeclaration,
    EvidenceRef, ExactRelevance, ExactTime, IntersampleLaw, JointSource,
    SourceCompletion, SourceFrame, UfError};
use crate::functional64_material::{Anatomy, MaterialError, MaterialView, PowerOrigin, PowerPacket};
use crate::virtual_articulated_body::{ArticulatedBodyState, BodyAnatomyProfile,
    BodyAxis, BodyAxisUnit, BODY_AXES};

#[path="source_ratio.rs"]
mod ratio;
use ratio::{Projection, RatioProjector, project_small, require_reduced};
type Result<T> = std::result::Result<T,UfError>;
const SITES:usize=19_335;
const OPTICAL:usize=6*SITES;
const INPUTS:usize=608;
const PHASES:usize=40_960+28_518;
const MATERIAL:usize=PHASES+2*INPUTS+3*97;
const ROWS:usize=46;

fn add(a:usize,b:usize)->Result<usize>{a.checked_add(b).ok_or(UfError::Capacity("source size"))}
fn product(a:usize,b:usize)->Result<usize>{a.checked_mul(b).ok_or(UfError::Capacity("source size"))}
fn finite(x:f64)->Result<f64>{if x.is_finite(){Ok(x)}else{Err(UfError::Arithmetic("source coordinate nonfinite"))}}
fn time(milliseconds:i64)->Result<ExactTime>{
    let mut a=milliseconds.unsigned_abs();let mut b=1000u64;
    while b!=0{let r=a%b;a=b;b=r;}ExactTime::new(milliseconds/(a as i64),1000/a)
}
fn milliseconds(t:ExactTime)->Result<i64>{
    let(n,d)=t.parts();let n=(n as i128).checked_mul(1000).ok_or(UfError::Arithmetic("source clock"))?;
    if n%(d as i128)!=0{return Err(UfError::Invalid("source is not on actual millisecond clock"));}
    i64::try_from(n/(d as i128)).map_err(|_|UfError::Arithmetic("source millisecond range"))
}

/// The byte bound applies before parsing/allocating raw acquisition data.
#[derive(Clone,Copy)]
pub(crate) struct SourceBounds{
    pub(crate) uf:AdmissionBounds,
    pub(crate) max_record_bytes:usize,
    pub(crate) max_integer_bytes:usize,
    pub(crate) max_prepared_bytes:usize,
}
impl SourceBounds{
    fn record(self,n:usize)->Result<()>{
        if n==0||n>self.max_record_bytes||n>self.uf.max_source_bytes{
            Err(UfError::Capacity("source record admission"))
        }else{Ok(())}
    }
}

struct Reader<'a>{bytes:&'a[u8],at:usize}
impl<'a> Reader<'a>{
    fn take(&mut self,n:usize)->Result<&'a[u8]>{let end=add(self.at,n)?;
        if end>self.bytes.len(){return Err(UfError::Invalid("truncated physical source record"));}
        let b=&self.bytes[self.at..end];self.at=end;Ok(b)}
    fn u64(&mut self)->Result<u64>{Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))}
    fn i64(&mut self)->Result<i64>{Ok(i64::from_le_bytes(self.take(8)?.try_into().unwrap()))}
    fn len(&mut self,bound:usize)->Result<usize>{let n=usize::try_from(self.u64()?).map_err(|_|UfError::Capacity("source record length"))?;
        if n>bound{return Err(UfError::Capacity("source record length"));}Ok(n)}
    fn blob(&mut self,bound:usize)->Result<&'a[u8]>{let n=self.len(bound)?;self.take(n)}
    fn ratio(&mut self,bound:usize)->Result<(&'a[u8],&'a[u8])>{
        let n=self.blob(bound)?;let d=self.blob(bound)?;
        for v in [n,d]{if v.is_empty()||(v.len()>1&&v.last()==Some(&0)){return Err(UfError::Invalid("noncanonical physical integer"));}}
        if d==[0]{return Err(UfError::Invalid("zero physical denominator"));}Ok((n,d))
    }
    fn finish(self)->Result<()>{if self.at==self.bytes.len(){Ok(())}else{Err(UfError::Invalid("trailing physical source bytes"))}}
}
struct Writer{bytes:Vec<u8>,limit:usize}
impl Writer{
    fn put(&mut self,b:&[u8])->Result<EvidenceRef>{let start=self.bytes.len();let end=add(start,b.len())?;
        if end>self.limit{return Err(UfError::Capacity("source evidence body"));}
        self.bytes.extend_from_slice(b);Ok(EvidenceRef{start,end})}
    fn u64(&mut self,x:u64)->Result<()>{self.put(&x.to_le_bytes())?;Ok(())}
    fn blob(&mut self,b:&[u8])->Result<EvidenceRef>{self.u64(b.len() as u64)?;self.put(b)}
}

/// Packed exact world readings, acquired once. The derived cohort powers are
/// produced in the same acquisition packer by exact area-weighted summation.
/// It never applies the eyelids, a pupil transform, RGB or eight-bit conversion.
pub(crate) struct OpticalAcquisition{
    bytes:Arc<[u8]>,identity:Range<usize>,values:usize,powers:usize,
    acquired_ms:i64,available_ms:i64,
}
impl OpticalAcquisition{
    pub(crate) fn decode(bytes:Arc<[u8]>,bounds:SourceBounds)->Result<Arc<Self>>{
        bounds.record(bytes.len())?;let mut r=Reader{bytes:&bytes,at:0};
        if r.take(8)?!=b"GL64OP01"{return Err(UfError::Invalid("optical source constitution"));}
        let acquired_ms=r.i64()?;let available_ms=r.i64()?;
        if acquired_ms>available_ms{return Err(UfError::Invalid("optical availability precedes acquisition"));}
        let size=r.len(bounds.max_record_bytes)?;let identity=r.at..add(r.at,size)?;
        if size==0{return Err(UfError::Invalid("optical acquisition identity missing"));}r.take(size)?;
        if r.u64()?!=OPTICAL as u64{return Err(UfError::Invalid("six-band optical roster"));}
        let values=r.at;let mut projection=RatioProjector::new(bounds.max_integer_bytes)?;
        for _ in 0..OPTICAL{let(n,d)=r.ratio(bounds.max_integer_bytes)?;
            require_reduced(n,d,bounds.max_integer_bytes)?;
            let p=projection.project(n,d,1,1)?;
            if p.upper>1.0{return Err(UfError::Invalid("raw optical irradiance outside anatomy"));}
        }
        if r.u64()?!=480{return Err(UfError::Invalid("optical receiver roster"));}
        let powers=r.at;
        for port in 0..480{let(n,d)=r.ratio(bounds.max_integer_bytes)?;
            require_reduced(n,d,bounds.max_integer_bytes)?;let p=projection.project(n,d,1,1)?;
            let disconnected=matches!((port/60,(port%60)/6),(0,3)|(0,6)|(1,3)|(1,6)|(6,3)|(6,6)|(7,3)|(7,6));
            if p.upper>100.0||(disconnected&&n!=[0]){return Err(UfError::Invalid("optical aperture power outside declared anatomy"));}
        }
        r.finish()?;Ok(Arc::new(Self{bytes,identity,values,powers,acquired_ms,available_ms}))
    }
    fn append_coordinates(&self,t:i64,shutter:(u128,u128),out:&mut Vec<f64>,p:&mut RatioProjector,b:SourceBounds)->Result<()>{
        if t<self.available_ms{return Err(UfError::Invalid("unavailable optical acquisition"));}
        let mut r=Reader{bytes:&self.bytes,at:self.values};
        for _ in 0..OPTICAL{let(n,d)=r.ratio(b.max_integer_bytes)?;out.push(p.project(n,d,shutter.0,shutter.1)?.value);}Ok(())
    }
}

/// One actual continuous-cochlear completion. The sample origin is part of
/// canonical owner custody and cannot be inferred from current batch length.
pub(crate) struct CochlearObservation{
    pub(crate) time_ms:i64,pub(crate) origin_ms:i64,pub(crate) completion_sample:u64,
    pub(crate) rms:[f64;32],pub(crate) phase_turns:[f64;32],
    pub(crate) acquisition_evidence:Arc<[u8]>,
}
impl CochlearObservation{
    fn validate(&self,b:SourceBounds)->Result<()>{
        b.record(self.acquisition_evidence.len())?;
        if self.completion_sample==0||self.completion_sample%160!=0{return Err(UfError::Invalid("not an actual cochlear completion"));}
        let offset=(self.completion_sample as i128)*1000/16000;
        if (self.origin_ms as i128)+offset!=self.time_ms as i128{return Err(UfError::Invalid("cochlear physical clock mismatch"));}
        for &x in &self.rms{if !x.is_finite()||!(0.0..=1.0).contains(&x){return Err(UfError::Invalid("native RMS boundary"));}}
        for &x in &self.phase_turns{finite(x)?;}Ok(())
    }
    fn encode(&self,b:SourceBounds)->Result<Arc<[u8]>>{
        self.validate(b)?;let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64AU01")?;
        w.put(&self.time_ms.to_le_bytes())?;w.put(&self.origin_ms.to_le_bytes())?;w.u64(self.completion_sample)?;
        for i in 0..32{w.put(&self.rms[i].to_bits().to_le_bytes())?;w.put(&self.phase_turns[i].to_bits().to_le_bytes())?;}
        w.blob(&self.acquisition_evidence)?;Ok(w.bytes.into())
    }
}

/// Exact ratios are supplied by the actual event packer: event_area/site_area.
/// The evidence must contain the admitted event IDs and all original phases.
/// This is explicitly body-surface-command event coverage, not skin occupancy.
pub(crate) struct SurfaceObservation{
    pub(crate) start_ms:i64,pub(crate) end_ms:i64,
    pub(crate) received_covered:bool,pub(crate) own_covered:bool,
    pub(crate) ratios:Arc<[u8]>,pub(crate) evidence:Arc<[u8]>,
    pub(crate) skin_millikelvin:Arc<[u8]>,
}

pub(crate) struct SourceAnatomy{
    bytes:Arc<[u8]>,surface_sites:usize,material:Arc<Anatomy>,
    input_qref:f64,output_m_qref:f64,output_r_qref:f64,reserve_capacity:u64,
}
impl SourceAnatomy{
    /// geometry_and_surface is the exact packed acquisition geometry and actual
    /// mounted self-site roster. It is supplied once by the real world owner.
    pub(crate) fn new(geometry_and_surface:Arc<[u8]>,surface_sites:usize,body:&ArticulatedBodyState,
                      material:Arc<Anatomy>,b:SourceBounds)->Result<Arc<Self>>{
        b.record(geometry_and_surface.len())?;
        if surface_sites>32||body.profile()!=BodyAnatomyProfile::V9||material.input_count()!=INPUTS
            ||material.raw_coordinate_count()!=MATERIAL{return Err(UfError::Invalid("functional64 physical source anatomy"));}
        validate_geometry(&geometry_and_surface,surface_sites,b)?;
        let width=OPTICAL+64+45+6+1+2*surface_sites+1+MATERIAL;
        if width>b.uf.max_vertices||width>b.uf.max_group_members{return Err(UfError::Capacity("full source anatomy admission"));}
        let material_evidence:Arc<[u8]>=material.source_evidence(b.max_record_bytes)
            .map_err(material_error)?.into();
        let refs=[material.input_q_reference_c(),material.output_membrane_q_reference_c(),material.output_receiving_q_reference_c()];
        if refs.iter().any(|x|!x.is_finite()||*x<=0.0)||material.reserve_capacity_micrograms()==0{
            return Err(UfError::Invalid("source physical reference"));}
        let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64AN02")?;
        w.u64(surface_sites as u64)?;w.blob(&geometry_and_surface)?;w.blob(&material_evidence)?;
        for axis in BODY_AXES{let a=body.anatomy(axis);w.put(&[axis as u8,match a.unit{BodyAxisUnit::Millidegree=>0,BodyAxisUnit::Micrometre=>1,BodyAxisUnit::SquareMillimetre=>2}])?;
            for x in [a.minimum,a.neutral,a.maximum]{w.put(&x.to_le_bytes())?;}}
        for x in refs{w.put(&x.to_bits().to_le_bytes())?;}w.u64(material.reserve_capacity_micrograms())?;
        let reserve_capacity=material.reserve_capacity_micrograms();
        Ok(Arc::new(Self{bytes:w.bytes.into(),surface_sites,material,
            input_qref:refs[0],output_m_qref:refs[1],output_r_qref:refs[2],reserve_capacity}))
    }
    pub(crate) fn width(&self)->usize{OPTICAL+64+45+6+1+2*self.surface_sites+1+MATERIAL}
    fn material_base(&self)->usize{self.width()-MATERIAL}
}

fn shutter(body:&ArticulatedBodyState)->Result<(u128,u128)>{
    let mut n=0u128;let mut d=0u128;
    for axis in [BodyAxis::LeftEyelidAperture,BodyAxis::RightEyelidAperture]{let a=body.anatomy(axis);let x=body.axis(axis);
        if x<a.minimum||x>a.maximum{return Err(UfError::Invalid("actual eyelid outside body anatomy"));}
        n+=(x as i64-a.minimum as i64) as u128;d+=(a.maximum as i64-a.minimum as i64) as u128;}
    if d==0{return Err(UfError::Invalid("zero optical shutter span"));}Ok((n,d))
}

struct ObservedContact{edge_id:u64,from:usize,to:usize,range:Range<usize>}
pub(crate) struct SourceObservation{
    time_ms:i64,optical:Arc<OpticalAcquisition>,values:Arc<[f64]>,evidence:Arc<[u8]>,
    contacts:Vec<ObservedContact>,anatomy:Arc<SourceAnatomy>,
}
impl SourceObservation{
    pub(crate) fn from_actual(anatomy:&Arc<SourceAnatomy>,optical:Arc<OpticalAcquisition>,audio:&CochlearObservation,
        body:&ArticulatedBodyState,root:&RootWindow,surface:&SurfaceObservation,material:&MaterialView<'_>,b:SourceBounds)->Result<Arc<Self>>{
        let t=milliseconds(material.time)?;audio.validate(b)?;root.validate(t,b)?;
        if t!=audio.time_ms||surface.end_ms!=t||surface.start_ms.checked_add(10)!=Some(t)
            ||!surface.received_covered||!surface.own_covered{return Err(UfError::Invalid("source endpoint or body-surface event coverage unavailable"));}
        if body.profile()!=BodyAnatomyProfile::V9||material.coordinates.len()!=MATERIAL||material.anatomy.input_count()!=INPUTS
            ||!std::ptr::eq(material.anatomy,anatomy.material.as_ref()){
            return Err(UfError::Invalid("source anatomy changed within cohort"));}
        if anatomy.surface_sites>0{b.record(surface.ratios.len())?;}else if !surface.ratios.is_empty(){return Err(UfError::Invalid("surface values without mounted sites"));}
        b.record(surface.evidence.len())?;b.record(surface.skin_millikelvin.len())?;
        let width=anatomy.width();
        let estimate=add(add(product(width,8)?,product(3,b.max_record_bytes)?)?,
            add(product(material.contact_rows.len(),128)?,product(3,add(b.max_integer_bytes,160)?)?)?)?;
        if width>b.uf.max_vertices||estimate>b.max_prepared_bytes{return Err(UfError::Capacity("source observation allocation"));}
        let mut p=RatioProjector::new(b.max_integer_bytes)?;let mut values=Vec::with_capacity(width);
        optical.append_coordinates(t,shutter(body)?,&mut values,&mut p,b)?;
        for i in 0..32{values.push(audio.rms[i]);values.push(audio.phase_turns[i]);}
        for axis in BODY_AXES{let a=body.anatomy(axis);let x=body.axis(axis);
            if x<a.minimum||x>a.maximum{return Err(UfError::Invalid("source body position outside profile"));}
            values.push(project_small((x as i64-a.minimum as i64) as u128,(a.maximum as i64-a.minimum as i64) as u128)?.value);}
        values.extend_from_slice(&root.latest().presence());
        let reserve=material.exact_custody.source_reserve_micrograms();
        if reserve>anatomy.reserve_capacity||material.anatomy.reserve_capacity_micrograms()!=anatomy.reserve_capacity{
            return Err(UfError::Invalid("source reserve custody or capacity"));}
        values.push(project_small(reserve as u128,anatomy.reserve_capacity as u128)?.value);
        let mut r=Reader{bytes:&surface.ratios,at:0};
        for _ in 0..2*anatomy.surface_sites{let(n,d)=r.ratio(b.max_integer_bytes)?;require_reduced(n,d,b.max_integer_bytes)?;values.push(p.project(n,d,1,1)?.value);}r.finish()?;
        let mut r=Reader{bytes:&surface.skin_millikelvin,at:0};let(n,d)=r.ratio(b.max_integer_bytes)?;
        require_reduced(n,d,b.max_integer_bytes)?;
        if n==[0]{return Err(UfError::Invalid("actual skin temperature must be positive"));}
        values.push(p.project(n,d,1,300_000)?.value);r.finish()?;
        let tau=2.0*std::f64::consts::PI;
        for &x in &material.coordinates[..PHASES]{values.push(finite(x/tau)?);}
        let input_end=PHASES+2*INPUTS;
        for pair in material.coordinates[PHASES..input_end].chunks_exact(2){
            if !(0.0..=1.0).contains(&pair[0]){return Err(UfError::Invalid("actual material input aperture"));}
            values.push(pair[0]);values.push(finite(pair[1]/anatomy.input_qref)?);}
        for triple in material.coordinates[input_end..].chunks_exact(3){
            if !(0.0..=1.0).contains(&triple[0]){return Err(UfError::Invalid("actual material output aperture"));}
            values.push(triple[0]);values.push(finite(triple[1]/anatomy.output_m_qref)?);values.push(finite(triple[2]/anatomy.output_r_qref)?);}
        if values.len()!=width{return Err(UfError::Invalid("full source width"));}
        let raw=material.exact_custody.encode_observation_view(material,b.max_record_bytes)
            .map_err(material_error)?;
        if raw.contacts.len()!=material.contact_rows.len(){return Err(UfError::Invalid("material contact evidence roster"));}
        let body_bytes=body.encode().map_err(|_|UfError::Invalid("actual body evidence"))?;
        let audio_bytes=audio.encode(b)?;
        let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64OB02")?;w.put(&t.to_le_bytes())?;
        w.blob(&audio_bytes)?;w.blob(&body_bytes)?;w.blob(&root.encoded(t,b)?)?;w.put(&surface.start_ms.to_le_bytes())?;
        w.blob(&surface.ratios)?;w.blob(&surface.evidence)?;w.blob(&surface.skin_millikelvin)?;
        let material_ref=w.blob(&raw.bytes)?;let mut contacts=Vec::with_capacity(raw.contacts.len());let mut previous=None;
        for (edge,receipt) in material.contact_rows.iter().zip(&raw.contacts){
            if edge.authentic_slot!=receipt.authentic_slot||previous.is_some_and(|x|edge.authentic_slot<=x)
                ||receipt.range.start>=receipt.range.end||receipt.range.end>raw.bytes.len(){return Err(UfError::Invalid("authentic source contact range"));}
            let(from,to)=edge.material_coordinate_endpoints();
            if from>=40_960||to>=40_960{return Err(UfError::Invalid("authentic source contact endpoint"));}
            contacts.push(ObservedContact{edge_id:edge.authentic_slot as u64,from:anatomy.material_base()+from,to:anatomy.material_base()+to,
                range:add(material_ref.start,receipt.range.start)?..add(material_ref.start,receipt.range.end)?});previous=Some(edge.authentic_slot);
        }
        Ok(Arc::new(Self{time_ms:t,optical,values:values.into(),evidence:w.bytes.into(),contacts,anatomy:anatomy.clone()}))
    }
}

/// Prepared source custody only. A clone shares immutable actual observations.
/// The caller commits this together with the same body/material/world successor.
#[derive(Clone)]
pub(crate) struct SourceAssembly{anatomy:Arc<SourceAnatomy>,rows:Vec<Arc<SourceObservation>>}
impl SourceAssembly{
    pub(crate) fn new(anatomy:Arc<SourceAnatomy>)->Self{Self{anatomy,rows:Vec::new()}}
    pub(crate) fn observations(&self)->usize{self.rows.len()}
    pub(crate) fn prepare_append(&self,row:Arc<SourceObservation>,b:SourceBounds)->Result<Self>{
        if self.rows.len()>=ROWS||self.rows.len()>=b.uf.max_frames{return Err(UfError::Capacity("source support register full"));}
        if !Arc::ptr_eq(&row.anatomy,&self.anatomy)||row.values.len()!=self.anatomy.width()||self.rows.last().is_some_and(|last|last.time_ms.checked_add(10)!=Some(row.time_ms)){
            return Err(UfError::Invalid("actual source gap or changed cohort"));}
        let mut bytes=self.anatomy.bytes.len();let mut acquired=BTreeMap::new();
        for old in self.rows.iter().chain(std::iter::once(&row)){
            bytes=add(bytes,add(product(old.values.len(),8)?,old.evidence.len())?)?;
            let key=Arc::as_ptr(&old.optical) as usize;
            if acquired.insert(key,()).is_none(){bytes=add(bytes,old.optical.bytes.len())?;}
        }
        if bytes>b.max_prepared_bytes{return Err(UfError::Capacity("source continuation payload"));}
        let mut next=self.clone();next.rows.push(row);Ok(next)
    }
    pub(crate) fn complete(&self,b:SourceBounds)->Result<(Arc<JointSource>,Self)>{
        if self.rows.len()!=ROWS{return Err(UfError::Invalid("46 actual source support rows unavailable"));}
        let source=self.snapshot(true,b)?;
        let next=Self{anatomy:self.anatomy.clone(),rows:self.rows[25..].to_vec()};Ok((source,next))
    }
    /// Partial snapshots explicitly have no completion. Their finite support is
    /// custody, never a claim that the planned250ms occurrence is complete.
    pub(crate) fn snapshot(&self,complete:bool,b:SourceBounds)->Result<Arc<JointSource>>{
        if self.rows.is_empty()||(complete&&self.rows.len()!=ROWS){return Err(UfError::Invalid("source snapshot support"));}
        let width=self.anatomy.width();let count=self.rows.len();
        let layout=self.actual_snapshot_size(complete,b)?;
        let mut w=Writer{bytes:Vec::with_capacity(layout.body_bytes),limit:b.uf.max_source_bytes};w.put(b"GL64SC01")?;
        let anatomy_ref=w.blob(&self.anatomy.bytes)?;
        let mut acquisitions:Vec<&Arc<OpticalAcquisition>>=Vec::with_capacity(count);let mut indices=Vec::with_capacity(count);
        for row in &self.rows{
            let found=acquisitions.iter().position(|a|Arc::ptr_eq(a,&row.optical));
            let index=match found{Some(i)=>i,None=>{let i=acquisitions.len();acquisitions.push(&row.optical);i}};indices.push(index);
        }
        w.u64(acquisitions.len() as u64)?;for a in acquisitions{w.blob(&a.bytes)?;}
        w.u64(count as u64)?;let mut observation_refs=Vec::with_capacity(count);let mut contacts=Vec::with_capacity(layout.contacts);
        for (source_index,(row,index)) in self.rows.iter().zip(indices).enumerate(){
            w.u64(index as u64)?;let record=w.blob(&row.evidence)?;observation_refs.push(record);
            for contact in &row.contacts{
                if contacts.len()>=b.uf.max_contacts{return Err(UfError::Capacity("source contact register"));}
                contacts.push(ContactSample{source_index,edge_id:contact.edge_id,from_vertex:contact.from,to_vertex:contact.to,
                    state:EvidenceRef{start:add(record.start,contact.range.start)?,end:add(record.start,contact.range.end)?}});
            }
        }
        let occurrence=w.put(SNAPSHOT_OCCURRENCE)?;
        let clock_law=w.put(SNAPSHOT_CLOCK)?;
        let clock_unit=w.put(SNAPSHOT_UNIT)?;
        let relevance=w.put(SNAPSHOT_RELEVANCE)?;
        let interpolation=w.put(SNAPSHOT_INTERPOLATION)?;
        let evidence=EvidenceRef{start:anatomy_ref.end,end:observation_refs[count-1].end};
        let mut coordinates=Vec::with_capacity(width);let mut groups=Vec::with_capacity(layout.groups);
        let mut declare=|quantity:&[u8],unit:&[u8],law:&[u8],members:usize,number:usize,w:&mut Writer|->Result<()>{
            let q=w.put(quantity)?;let u=w.put(unit)?;let map=w.put(law)?;
            for physical in 0..number{
                let location=w.put(&(physical as u64).to_le_bytes())?;let first=coordinates.len();
                for _ in 0..members{coordinates.push(CoordinateDeclaration{physical_quantity:q,physical_unit:u,physical_location:location,
                    source_lineage:anatomy_ref,coordinate_law:map,physical_evidence:evidence});}
                groups.push((first..coordinates.len()).collect::<Vec<_>>().into_boxed_slice());
            }Ok(())
        };
        for(q,u,law,members,number)in snapshot_declarations(self.anatomy.surface_sites){declare(q,u,law,members,number,&mut w)?;}
        if coordinates.len()!=width{return Err(UfError::Invalid("source coordinate declarations"));}
        let completion_ref=if complete{Some(w.put(SNAPSHOT_COMPLETION)?)}else{None};
        if w.bytes.len()!=layout.body_bytes{return Err(UfError::Invalid("snapshot allocation/writer disagreement"));}
        let mut frames=Vec::with_capacity(count);for row in &self.rows{frames.push(SourceFrame{time:time(row.time_ms)?,coordinates:row.values.to_vec().into_boxed_slice(),joint_relevance:ExactRelevance::new(1,1)?});}
        let first=19.min(count-1);let last=44.min(count-1);
        let source=Arc::new(JointSource{body:w.bytes.into(),occurrence,clock_coordinate_law:clock_law,clock_unit,joint_relevance_law:relevance,
            coordinates:coordinates.into_boxed_slice(),groups:groups.into_boxed_slice(),contacts:contacts.into_boxed_slice(),
            frames:frames.into_boxed_slice(),
            first_evaluation_index:first,last_evaluation_index:last,intersample_law:IntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear{evidence:interpolation},
            completion:completion_ref.map(|evidence|SourceCompletion{final_source_index:44,evidence})});
        // Child-module access reuses the unchanged producer validator without
        // constructing and discarding a second whole-source encoded blob.
        super::validate_source(&source,b.uf)?;
        Ok(source)
    }
}

fn packet(identity:Arc<[u8]>,receiver:usize,origin:PowerOrigin,acquired_start:i64,acquired_end:i64,
          available:i64,start:i64,end:i64,work:Projection)->Result<PowerPacket>{
    Ok(PowerPacket{identity,receiver:u16::try_from(receiver).map_err(|_|UfError::Capacity("receiver slot"))?,origin,
        acquired_start:time(acquired_start)?,acquired_end:time(acquired_end)?,available:time(available)?,
        release_start:time(start)?,release_end:time(end)?,admitted_j:work.value,lower_j:work.lower,upper_j:work.upper})
}

/// Actual current body shutters and proprioception power the following1ms.
/// Offers never debit reserve here; the single material owner pays BodyReserve.
pub(crate) fn power_for_next_millisecond(optical:&OpticalAcquisition,body:&ArticulatedBodyState,
    root:Option<&RootInterval>,at:ExactTime,b:SourceBounds)->Result<Vec<PowerPacket>>{
    let start=milliseconds(at)?;let end=start.checked_add(1).ok_or(UfError::Arithmetic("source release clock"))?;
    if start<optical.available_ms||body.profile()!=BodyAnatomyProfile::V9{return Err(UfError::Invalid("power source unavailable"));}
    let(shutter_n,shutter_d)=shutter(body)?;
    let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64PW01")?;w.blob(&optical.bytes[optical.identity.clone()])?;
    w.put(&start.to_le_bytes())?;w.put(&end.to_le_bytes())?;
    for axis in [BodyAxis::LeftEyelidAperture,BodyAxis::RightEyelidAperture]{w.put(&body.axis(axis).to_le_bytes())?;}
    let optical_identity:Arc<[u8]>=w.bytes.into();
    let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64SM01")?;w.put(&start.to_le_bytes())?;
    w.blob(&body.encode().map_err(|_|UfError::Invalid("somatic source body"))?)?;let somatic_identity:Arc<[u8]>=w.bytes.into();
    let mut packets=Vec::with_capacity(480+90+6);let mut p=RatioProjector::new(b.max_integer_bytes)?;
    let mut r=Reader{bytes:&optical.bytes,at:optical.powers};
    const MILLISECOND_ZJ_TO_J_DENOMINATOR:u128=1_000_000_000_000_000_000_000_000;
    let denominator=shutter_d.checked_mul(MILLISECOND_ZJ_TO_J_DENOMINATOR).ok_or(UfError::Arithmetic("optical work unit"))?;
    for port in 0..480{let(n,d)=r.ratio(b.max_integer_bytes)?;let work=p.project(n,d,shutter_n,denominator)?;
        packets.push(packet(optical_identity.clone(),port,PowerOrigin::MeasuredEnvironmental,optical.acquired_ms,optical.acquired_ms,optical.available_ms,start,end,work)?);}
    for axis in BODY_AXES{let a=body.anatomy(axis);let x=body.axis(axis);if x<a.minimum||x>a.maximum{return Err(UfError::Invalid("somatic source position"));}
        let span=(a.maximum as i64-a.minimum as i64) as u128;
        let positions=[(x as i64-a.minimum as i64) as u128,(a.maximum as i64-x as i64) as u128];
        for (direction,n) in positions.into_iter().enumerate(){
            let numerator=n.checked_mul(n).and_then(|v|v.checked_mul(100)).ok_or(UfError::Arithmetic("squared somatic work"))?;
            let denominator=span.checked_mul(span).and_then(|v|v.checked_mul(MILLISECOND_ZJ_TO_J_DENOMINATOR)).ok_or(UfError::Arithmetic("squared somatic unit"))?;
            let work=project_small(numerator,denominator)?;
            packets.push(packet(somatic_identity.clone(),512+2*axis.index()+direction,PowerOrigin::BodyReserve,start,start,start,start,end,work)?);}
    }
    if let Some(actual)=root{packets.extend(actual.power_after_completion(start,b)?);}
    Ok(packets)
}

fn outward_product(a:Projection,b:Projection)->Result<Projection>{
    fn down(x:f64)->f64{if x==0.0{0.0}else{f64::from_bits(x.to_bits()-1)}}
    fn up(x:f64)->Result<f64>{finite(f64::from_bits(x.to_bits()+1))}
    let value=finite(a.value*b.value)?;
    let lower=if a.lower==0.0||b.lower==0.0{0.0}else{down(finite(a.lower*b.lower)?)};
    let upper=if a.upper==0.0||b.upper==0.0{0.0}else{up(finite(a.upper*b.upper)?)?};
    Ok(Projection{value,lower,upper})
}
fn outward_sum(a:Projection,b:Projection)->Result<Projection>{
    let value=finite(a.value+b.value)?;let lo=finite(a.lower+b.lower)?;let hi=finite(a.upper+b.upper)?;
    let lower=if lo==0.0{0.0}else{f64::from_bits(lo.to_bits()-1)};
    let upper=if hi==0.0{0.0}else{finite(f64::from_bits(hi.to_bits()+1))?};
    Ok(Projection{value,lower,upper})
}

/// One finite work packet per receiver from REAL adjacent completions. The
/// material owner retains/debits any unconsumed remainder; calling this routine
/// again cannot authorize replay of the same receiver release interval.
pub(crate) fn auditory_power_packets(previous:&CochlearObservation,current:&CochlearObservation,
                                     b:SourceBounds)->Result<Vec<PowerPacket>>{
    previous.validate(b)?;current.validate(b)?;
    if previous.origin_ms!=current.origin_ms||previous.time_ms.checked_add(10)!=Some(current.time_ms)
        ||previous.completion_sample.checked_add(160)!=Some(current.completion_sample){
        return Err(UfError::Invalid("auditory power lacks real adjacent source completions"));}
    let end=current.time_ms.checked_add(10).ok_or(UfError::Arithmetic("auditory release clock"))?;
    let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64AW01")?;
    w.put(&previous.origin_ms.to_le_bytes())?;w.u64(previous.completion_sample)?;w.u64(current.completion_sample)?;
    for channel in 0..32{w.put(&previous.rms[channel].to_bits().to_le_bytes())?;w.put(&current.rms[channel].to_bits().to_le_bytes())?;}
    let identity:Arc<[u8]>=w.bytes.into();
    // 2*50*(p0²+p1²)/2 * (10/1000 seconds) *10^-21 J/zJ.
    // The reduced dimensional factor is exactly1/(2*10^21). Squaring and
    // addition use this fixed binary64 order with outward enclosure; only the
    // admitted finite result bits, not exact real transduction, enter custody.
    let factor=project_small(1,2_000_000_000_000_000_000_000)?;
    let mut packets=Vec::with_capacity(32);
    for channel in 0..32{
        let p=previous.rms[channel];let q=current.rms[channel];
        let p=Projection{value:p,lower:p,upper:p};let q=Projection{value:q,lower:q,upper:q};
        let work=outward_product(outward_sum(outward_product(p,p)?,outward_product(q,q)?)?,factor)?;
        packets.push(packet(identity.clone(),480+channel,PowerOrigin::MeasuredEnvironmental,
            previous.time_ms,current.time_ms,current.time_ms,current.time_ms,end,work)?);
    }
    Ok(packets)
}

impl OpticalAcquisition{
    pub(crate) fn encoded(&self)->&Arc<[u8]>{&self.bytes}
}

impl CochlearObservation{
    pub(crate) fn decode(bytes:&[u8],b:SourceBounds)->Result<Self>{
        b.record(bytes.len())?;let mut r=Reader{bytes,at:0};
        if r.take(8)?!=b"GL64AU01"{return Err(UfError::Invalid("cochlear observation constitution"));}
        let time_ms=r.i64()?;let origin_ms=r.i64()?;let completion_sample=r.u64()?;
        let mut rms=[0.0;32];let mut phase_turns=[0.0;32];
        for channel in 0..32{rms[channel]=f64::from_bits(r.u64()?);phase_turns[channel]=f64::from_bits(r.u64()?);}
        let acquisition_evidence:Arc<[u8]>=r.blob(b.max_record_bytes)?.into();r.finish()?;
        let value=Self{time_ms,origin_ms,completion_sample,rms,phase_turns,acquisition_evidence};value.validate(b)?;Ok(value)
    }
    pub(crate) fn encoded(&self,b:SourceBounds)->Result<Arc<[u8]>>{self.encode(b)}
}

impl SourceAssembly{
    pub(crate) fn latest_optical(&self)->Option<Arc<OpticalAcquisition>>{self.rows.last().map(|r|r.optical.clone())}
    pub(crate) fn latest_cochlear(&self,b:SourceBounds)->Result<Option<CochlearObservation>>{
        let Some(row)=self.rows.last()else{return Ok(None)};
        let mut r=Reader{bytes:&row.evidence,at:16};
        Ok(Some(CochlearObservation::decode(r.blob(b.max_record_bytes)?,b)?))
    }
    /// Empty warm-up has no manufactured source frame. A nonempty snapshot uses
    /// the accepted complete-source codec with explicit completion=None.
    pub(crate) fn encode_custody(&self,b:SourceBounds)->Result<Vec<u8>>{
        if self.rows.is_empty(){
            let mut w=Writer{bytes:Vec::new(),limit:b.uf.max_source_bytes};w.put(b"GL64SZ01")?;w.blob(&self.anatomy.bytes)?;return Ok(w.bytes);
        }
        let source=self.snapshot(false,b)?;
        crate::joint_uf_vector::source_codec::encode_joint_source(&source,b.uf)
    }
    pub(crate) fn decode_custody(bytes:&[u8],anatomy:Arc<SourceAnatomy>,b:SourceBounds)->Result<Self>{
        if bytes.starts_with(b"GL64SZ01"){
            let mut r=Reader{bytes,at:8};if r.blob(b.uf.max_source_bytes)?!=anatomy.bytes.as_ref(){return Err(UfError::Invalid("cold source anatomy changed"));}
            r.finish()?;return Ok(Self::new(anatomy));
        }
        let source=crate::joint_uf_vector::source_codec::decode_joint_source(bytes,b.uf)?;
        if source.completion.is_some()||source.frames.len()>ROWS||source.coordinates.len()!=anatomy.width(){return Err(UfError::Invalid("cold partial source role or roster"));}
        let mut r=Reader{bytes:&source.body,at:0};
        if r.take(8)?!=b"GL64SC01"||r.blob(b.max_record_bytes)?!=anatomy.bytes.as_ref(){return Err(UfError::Invalid("cold source physical constitution"));}
        let count=r.len(ROWS)?;let mut acquisitions=Vec::with_capacity(count);
        for _ in 0..count{acquisitions.push(OpticalAcquisition::decode(r.blob(b.max_record_bytes)?.into(),b)?);}
        let rows=r.len(ROWS)?;
        if rows!=source.frames.len()||rows==0{return Err(UfError::Invalid("cold source frame roster"));}
        let mut result=Self::new(anatomy);
        let mut contact_cursor=0usize;
        for index in 0..rows{
            let acquisition=r.len(count.saturating_sub(1))?;
            let optical=acquisitions.get(acquisition).ok_or(UfError::Invalid("cold source acquisition reference"))?.clone();
            let len=r.len(b.max_record_bytes)?;let offset=r.at;let raw=r.take(len)?;
            let mut record=Reader{bytes:raw,at:0};
            if record.take(8)?!=b"GL64OB02"{return Err(UfError::Invalid("cold actual observation constitution"));}
            let time_ms=record.i64()?;
            if milliseconds(source.frames[index].time)?!=time_ms||source.frames[index].joint_relevance.parts()!=(1,1)
                ||time_ms<optical.available_ms{return Err(UfError::Invalid("cold source clock or availability"));}
            let audio=CochlearObservation::decode(record.blob(b.max_record_bytes)?,b)?;
            if audio.time_ms!=time_ms{return Err(UfError::Invalid("cold source cochlear clock"));}
            let body=record.blob(b.max_record_bytes)?;
            let decoded_body=ArticulatedBodyState::decode(body).map_err(|_|UfError::Invalid("cold source actual body evidence"))?;
            if body.len()!=680||decoded_body.profile()!=BodyAnatomyProfile::V9{return Err(UfError::Invalid("cold source V9 body evidence"));}
            RootWindow::decode(record.blob(b.max_record_bytes)?,time_ms,b)?;
            if record.i64()?.checked_add(10)!=Some(time_ms){return Err(UfError::Invalid("cold surface interval"));}
            let ratios=record.blob(b.max_record_bytes)?;let mut ratios=Reader{bytes:ratios,at:0};
            for _ in 0..2*result.anatomy.surface_sites{let(n,d)=ratios.ratio(b.max_integer_bytes)?;require_reduced(n,d,b.max_integer_bytes)?;}ratios.finish()?;
            if record.blob(b.max_record_bytes)?.is_empty(){return Err(UfError::Invalid("cold event coverage evidence"));}
            let thermal=record.blob(b.max_record_bytes)?;let mut thermal=Reader{bytes:thermal,at:0};let(n,d)=thermal.ratio(b.max_integer_bytes)?;require_reduced(n,d,b.max_integer_bytes)?;thermal.finish()?;
            let material=record.blob(b.max_record_bytes)?;
            if !material.starts_with(b"GL64OB01"){return Err(UfError::Invalid("cold material observation evidence"));}record.finish()?;
            let mut contacts=Vec::new();
            while let Some(contact)=source.contacts.get(contact_cursor){
                if contact.source_index!=index{break;}
                let start=contact.state.start.checked_sub(offset).ok_or(UfError::Invalid("cold contact observation range"))?;
                let end=contact.state.end.checked_sub(offset).ok_or(UfError::Invalid("cold contact observation range"))?;
                if start>=end||end>len{return Err(UfError::Invalid("cold contact evidence left its actual observation"));}
                contacts.push(ObservedContact{edge_id:contact.edge_id,from:contact.from_vertex,to:contact.to_vertex,range:start..end});contact_cursor+=1;
            }
            let row=Arc::new(SourceObservation{time_ms,optical,values:source.frames[index].coordinates.to_vec().into(),evidence:raw.into(),contacts,anatomy:result.anatomy.clone()});
            result=result.prepare_append(row,b)?;
        }
        if contact_cursor!=source.contacts.len(){return Err(UfError::Invalid("cold source contact row loss"));}
        // Remaining bytes are immutable declaration records referenced by the
        // already validated JointSource, not a second unparsed physical record.
        // Rebuilding must reproduce those declarations, provenance and order.
        let rebuilt=result.snapshot(false,b)?;
        let refs=|c:&CoordinateDeclaration|[c.physical_quantity,c.physical_unit,c.physical_location,c.source_lineage,c.coordinate_law,c.physical_evidence];
        if rebuilt.body.as_ref()!=source.body.as_ref()
            ||rebuilt.first_evaluation_index!=source.first_evaluation_index
            ||rebuilt.last_evaluation_index!=source.last_evaluation_index
            ||rebuilt.occurrence!=source.occurrence||rebuilt.clock_coordinate_law!=source.clock_coordinate_law
            ||rebuilt.clock_unit!=source.clock_unit||rebuilt.joint_relevance_law!=source.joint_relevance_law
            ||rebuilt.intersample_law!=source.intersample_law||rebuilt.groups!=source.groups||rebuilt.contacts!=source.contacts
            ||rebuilt.coordinates.iter().zip(source.coordinates.iter()).any(|(a,b)|refs(a)!=refs(b)){
            return Err(UfError::Invalid("noncanonical cold source assembly"));}
        Ok(result)
    }
}

fn validate_geometry(bytes:&[u8],surface_sites:usize,b:SourceBounds)->Result<()>{
    let mut r=Reader{bytes,at:0};
    if r.take(8)?!=b"GL64SG01"||r.u64()?!=SITES as u64{return Err(UfError::Invalid("actual optical geometry roster"));}
    for site in 0..SITES{
        if r.u64()?!=site as u64{return Err(UfError::Invalid("actual optical geometry order"));}
        let expected=if site<135{
            let (offset,rows,columns)=if site<27{(site,3i32,9i32)}else{(site-27,6i32,18i32)};
            let row=offset as i32/columns;let column=offset as i32%columns;
            let hh=180_000/(2*columns);let vh=90_000/(2*rows);
            [2*(-90_000+column*(180_000/columns)+hh),2*(45_000-row*(90_000/rows)-vh),2*hh,2*vh]
        }else{
            let offset=(site-135) as i32;let row=offset/160;let column=offset%160;
            [-60_000+(2*column+1)*375,45_000-(2*row+1)*375,375,375]
        };
        for value in expected{
            if i32::from_le_bytes(r.take(4)?.try_into().unwrap())!=value{return Err(UfError::Invalid("changed exact retinal geometry requires new source cohort"));}
        }
    }
    if r.u64()?!=surface_sites as u64{return Err(UfError::Invalid("actual surface roster count"));}
    for _ in 0..surface_sites{if r.blob(b.max_record_bytes)?.is_empty(){return Err(UfError::Invalid("missing mounted surface evidence"));}}
    r.finish()
}

/// Actual compound-world consequence for one completed1ms. These are measured
/// mm/mdeg displacements, never a requested motor command or inferred GPS.
#[derive(Clone)]
pub(crate) struct RootInterval{
    pub(crate) start_ms:i64,pub(crate) actual_x_mm:i64,pub(crate) actual_y_mm:i64,
    pub(crate) actual_yaw_millidegrees:i64,pub(crate) evidence:Arc<[u8]>,
}
impl RootInterval{
    fn validate(&self,b:SourceBounds)->Result<()>{
        b.record(self.evidence.len())?;self.start_ms.checked_add(1).ok_or(UfError::Arithmetic("actual root clock"))?;
        for value in [self.actual_x_mm,self.actual_y_mm,self.actual_yaw_millidegrees]{
            if !(-(1i64<<32)..(1i64<<32)).contains(&value){return Err(UfError::Invalid("actual root displacement boundary"));}}
        Ok(())
    }
    pub(crate) fn presence(&self)->[f64;6]{
        let sign=|x:i64|[f64::from(u8::from(x<0)),f64::from(u8::from(x>0))];
        let yaw=sign(self.actual_yaw_millidegrees);let x=sign(self.actual_x_mm);let y=sign(self.actual_y_mm);
        [yaw[0],yaw[1],x[0],x[1],y[0],y[1]]
    }
    pub(crate) fn encoded(&self,b:SourceBounds)->Result<Arc<[u8]>>{
        self.validate(b)?;let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64RI01")?;
        for value in [self.start_ms,self.actual_x_mm,self.actual_y_mm,self.actual_yaw_millidegrees]{w.put(&value.to_le_bytes())?;}
        w.blob(&self.evidence)?;Ok(w.bytes.into())
    }
    pub(crate) fn decode(bytes:&[u8],b:SourceBounds)->Result<Self>{
        b.record(bytes.len())?;let mut r=Reader{bytes,at:0};if r.take(8)?!=b"GL64RI01"{return Err(UfError::Invalid("root return constitution"));}
        let result=Self{start_ms:r.i64()?,actual_x_mm:r.i64()?,actual_y_mm:r.i64()?,actual_yaw_millidegrees:r.i64()?,evidence:r.blob(b.max_record_bytes)?.into()};
        r.finish()?;result.validate(b)?;Ok(result)
    }
    fn power_after_completion(&self,at:i64,b:SourceBounds)->Result<Vec<PowerPacket>>{
        self.validate(b)?;
        if self.start_ms.checked_add(1)!=Some(at){return Err(UfError::Invalid("root event unavailable or already passed"));}
        let end=at.checked_add(1).ok_or(UfError::Arithmetic("root pulse clock"))?;let identity=self.encoded(b)?;
        let mut result=Vec::with_capacity(6);
        for (port,present) in self.presence().into_iter().enumerate(){
            // The historical event ending starts at0 for this real interval,
            // then ends at the actual direction-presence bit. Integrating the
            // squared endpoint values gives N/1000 zJ, not harvested motor work.
            let work=project_small(if present==0.0{0}else{50},1_000_000_000_000_000_000_000_000)?;
            result.push(packet(identity.clone(),602+port,PowerOrigin::BodyReserve,self.start_ms,at,at,at,end,work)?);
        }
        Ok(result)
    }
}

pub(crate) struct RootWindow{pub(crate) intervals:[RootInterval;10]}
impl RootWindow{
    pub(crate) fn latest(&self)->&RootInterval{&self.intervals[9]}
    fn validate(&self,at:i64,b:SourceBounds)->Result<()>{
        for (index,interval) in self.intervals.iter().enumerate(){
            interval.validate(b)?;
            let expected=at.checked_sub(10-index as i64).ok_or(UfError::Arithmetic("root window clock"))?;
            if interval.start_ms!=expected{return Err(UfError::Invalid("root window lacks ten actual consecutive intervals"));}
        }Ok(())
    }
    pub(crate) fn encoded(&self,at:i64,b:SourceBounds)->Result<Arc<[u8]>>{
        self.validate(at,b)?;let mut w=Writer{bytes:Vec::new(),limit:b.max_record_bytes};w.put(b"GL64RW01")?;w.put(&at.to_le_bytes())?;
        for interval in &self.intervals{w.blob(&interval.encoded(b)?)?;}Ok(w.bytes.into())
    }
    pub(crate) fn decode(bytes:&[u8],at:i64,b:SourceBounds)->Result<Self>{
        b.record(bytes.len())?;let mut r=Reader{bytes,at:0};
        if r.take(8)?!=b"GL64RW01"||r.i64()?!=at{return Err(UfError::Invalid("root window constitution or clock"));}
        let mut rows=Vec::with_capacity(10);for _ in 0..10{rows.push(RootInterval::decode(r.blob(b.max_record_bytes)?,b)?);}r.finish()?;
        let result=Self{intervals:rows.try_into().map_err(|_|UfError::Invalid("root window cardinality"))?};result.validate(at,b)?;Ok(result)
    }
}

fn material_error(error:MaterialError)->UfError{
    match error{
        MaterialError::Invalid(reason)|MaterialError::Source(reason)|MaterialError::UnresolvedEvent(reason)=>UfError::Invalid(reason),
        MaterialError::Capacity(reason)=>UfError::Capacity(reason),
        MaterialError::ForceCapacity{reason,..}=>UfError::Capacity(reason),
        MaterialError::Arithmetic(reason)=>UfError::Arithmetic(reason),
    }
}

#[cfg(test)]
#[path="functional64_source_tests.rs"]
mod tests;

// Separate append-only source API amendment for the combined owner mount.
// Original frozen functional64_source.rs candidate remains untouched.
impl OpticalAcquisition {
    pub(crate) fn acquired_millisecond(&self) -> i64 { self.acquired_ms }
    pub(crate) fn available_millisecond(&self) -> i64 { self.available_ms }
}

/// Serialized declarations are shared by writing and size admission. Their
/// bytes/order are the existing source constitution, not a new coordinate law.
type SnapshotDeclaration=(&'static[u8],&'static[u8],&'static[u8],usize,usize);
fn snapshot_declarations(surface_sites:usize)->[SnapshotDeclaration;11]{[
    (b"six original optical bands",b"fraction of reference irradiance",b"F=rawL*actual two-lid transmission; exact ratio to nearest-even",6,SITES),
    (b"cochlear RMS then reported reset-capable phase",b"normalized amplitude,turn",b"preserve original binary64 bits in channel tuple order",2,32),
    (b"actual V9 axis",b"profile axis unit",b"F=(x-minimum)/(maximum-minimum); exact ratio to nearest-even",1,45),
    (b"actual root yaw,x,y negative/positive event endings",b"dimensionless motion presence",b"F=actual final1ms direction presence; all ten mm/mdeg deltas retained; magnitude is not this sensor quantity",2,3),
    (b"actual native reserve",b"microgram",b"F=post-assimilation native reserve/anatomical capacity",1,1),
    (b"received,own body-surface-command event area",b"square micrometre",b"F=distinct newly completed event area/site area in covered interval",2,surface_sites),
    (b"actual prefix skin temperature",b"millikelvin",b"F=raw Fraction/300000; exact ratio to nearest-even",1,1),
    (b"node send,receive unwrapped phase",b"radian",b"F=raw/(2*IEEE PI), fixed binary64 division",2,20_480),
    (b"complete typed-ring phase",b"radian",b"F=raw/(2*IEEE PI), fixed binary64 division",3,9_506),
    (b"input aperture,independent charge",b"aperture fraction,coulomb",b"F=(y,Q/fixed input Qref)",2,INPUTS),
    (b"output aperture,membrane charge,receiving charge",b"aperture fraction,coulomb,coulomb",b"F=(y,Qm/fixed Qmref,Qr/fixed Qrref)",3,97),
]}
const SNAPSHOT_OCCURRENCE:&[u8]=b"finite actual support for planned250ms episode; evaluation19..44; completion requires46realrows";
const SNAPSHOT_CLOCK:&[u8]=b"actual retained complete-owner millisecond clock divided by1000; no world-clock inference";
const SNAPSHOT_UNIT:&[u8]=b"second";
const SNAPSHOT_RELEVANCE:&[u8]=b"r=1 for the declared complete continuously present acquired-register roster; availability only";
const SNAPSHOT_INTERPOLATION:&[u8]=b"sampled joint structural volume q and declared r piecewise-linear on actual source intervals";
const SNAPSHOT_COMPLETION:&[u8]=b"caller completed actual source episode at evaluation index44; real successor45 retained";

#[derive(Clone,Copy,Debug)]
pub(crate) struct SnapshotLogicalSize{
    pub(crate) body_bytes:usize,pub(crate) groups:usize,pub(crate) contacts:usize,
    pub(crate) retained_snapshot_payload:usize,pub(crate) field_payload:usize,
    /// Maximum of constructor (including Vec-to-Arc copy) and evaluator stages.
    pub(crate) preparation_payload:usize,
}
impl SourceAssembly{
    /// No source arrays, field or serialization buffer are allocated here.
    pub(crate) fn actual_snapshot_size(&self,complete:bool,b:SourceBounds)->Result<SnapshotLogicalSize>{
        use std::mem::size_of;
        let count=self.rows.len();let width=self.anatomy.width();
        if count==0||count>ROWS||(complete&&count!=ROWS)||count>b.uf.max_frames||width>b.uf.max_vertices||width>b.uf.max_group_members{
            return Err(UfError::Capacity("actual snapshot support dimensions"));}
        let mut body=add(8,add(8,self.anatomy.bytes.len())?)?;
        let mut optical_ptrs=[0usize;ROWS];let mut optical_count=0usize;let mut contacts=0usize;
        body=add(body,16)?; // acquisition and observation counts
        for row in &self.rows{
            if row.values.len()!=width||!Arc::ptr_eq(&row.anatomy,&self.anatomy){return Err(UfError::Invalid("actual snapshot anatomy"));}
            contacts=add(contacts,row.contacts.len())?;
            body=add(body,add(16,row.evidence.len())?)?; // acquisition index, blob length, evidence
            let key=Arc::as_ptr(&row.optical) as usize;
            if !optical_ptrs[..optical_count].contains(&key){optical_ptrs[optical_count]=key;optical_count+=1;
                body=add(body,add(8,row.optical.bytes.len())?)?;}
        }
        if contacts>b.uf.max_contacts{return Err(UfError::Capacity("actual snapshot contact register"));}
        for text in [SNAPSHOT_OCCURRENCE,SNAPSHOT_CLOCK,SNAPSHOT_UNIT,SNAPSHOT_RELEVANCE,SNAPSHOT_INTERPOLATION]{body=add(body,text.len())?;}
        let mut groups=0usize;let mut members=0usize;
        for(q,u,law,n,number)in snapshot_declarations(self.anatomy.surface_sites){
            for bytes in [q.len(),u.len(),law.len(),product(8,number)?]{body=add(body,bytes)?;}
            groups=add(groups,number)?;members=add(members,product(n,number)?)?;
        }
        if members!=width{return Err(UfError::Invalid("actual snapshot declared width"));}
        if complete{body=add(body,SNAPSHOT_COMPLETION.len())?;}
        if body>b.uf.max_source_bytes{return Err(UfError::Capacity("actual source body admission"));}
        let field=super::source_codec::source_layout_field_payload_bound(body,width,groups,members,contacts,count,b.uf)?;
        let mut retained=body;
        for bytes in [size_of::<JointSource>(),product(width,size_of::<CoordinateDeclaration>())?,
            product(groups,size_of::<Box<[usize]>>())?,product(members,size_of::<usize>())?,
            product(contacts,size_of::<ContactSample>())?,product(count,size_of::<SourceFrame>())?,
            product(product(count,width)?,size_of::<f64>())?]{retained=add(retained,bytes)?;}
        // Fixed exact-capacity vectors below retain their backing data when
        // boxed. Body conversion may coexist with its original Vec. Group
        // construction owns one Vec header per group while it becomes boxed.
        let metadata=product(count,add(add(size_of::<&Arc<OpticalAcquisition>>(),size_of::<usize>())?,size_of::<EvidenceRef>())?)?;
        let constructor=add(retained,add(body,add(metadata,size_of::<SnapshotLogicalSize>())?)?)?;
        let preparation=constructor.max(field);
        if preparation>b.max_prepared_bytes{return Err(UfError::Capacity("actual source snapshot preparation"));}
        Ok(SnapshotLogicalSize{body_bytes:body,groups,contacts,retained_snapshot_payload:retained,
            field_payload:field,preparation_payload:preparation})
    }
}

/// Actual occupied source custody. Complete fields are reported only when
/// 46 real rows exist; capacity ceilings are not imaginary resident bytes.
#[derive(Clone,Copy,Debug)]
pub(crate) struct SourceLogicalSize{
    pub(crate) retained_source_bytes:usize,
    pub(crate) next_observation_payload_bound:usize,
    pub(crate) next_observation_preparation_bound:usize,
    pub(crate) complete_source_snapshot_payload_bound:usize,
    pub(crate) complete_field_payload_bound:usize,
    pub(crate) preparation_peak_bound:usize,
}
impl SourceAssembly{
    pub(crate) fn logical_size(&self,b:SourceBounds,next_contact_rows:usize)->Result<SourceLogicalSize>{
        use std::mem::size_of;
        let width=self.anatomy.width();
        if self.rows.len()>ROWS||ROWS>b.uf.max_frames||width>b.uf.max_vertices||width>b.uf.max_group_members
            ||next_contact_rows>b.uf.max_contacts{return Err(UfError::Capacity("complete source sizing roster"));}
        let mut retained=add(size_of::<Self>(),add(size_of::<SourceAnatomy>(),self.anatomy.bytes.len())?)?;
        retained=add(retained,product(self.rows.capacity(),size_of::<Arc<SourceObservation>>())?)?;
        let mut optical_ptrs=[0usize;ROWS];let mut optical_count=0usize;let mut contacts=0usize;
        for row in &self.rows{
            if row.values.len()!=width||!Arc::ptr_eq(&row.anatomy,&self.anatomy){return Err(UfError::Invalid("retained source sizing anatomy"));}
            contacts=add(contacts,row.contacts.len())?;
            for n in [size_of::<SourceObservation>(),product(row.values.len(),size_of::<f64>())?,row.evidence.len(),
                product(row.contacts.capacity(),size_of::<ObservedContact>())?]{retained=add(retained,n)?;}
            let key=Arc::as_ptr(&row.optical) as usize;
            if !optical_ptrs[..optical_count].contains(&key){optical_ptrs[optical_count]=key;optical_count+=1;
                retained=add(retained,add(size_of::<OpticalAcquisition>(),row.optical.bytes.len())?)?;}
        }
        if contacts>b.uf.max_contacts||(self.rows.len()<ROWS&&add(contacts,next_contact_rows)?>b.uf.max_contacts){
            return Err(UfError::Capacity("actual source contact admission"));}
        let mut next=0usize;let mut raw_scratch=0usize;
        if self.rows.len()<ROWS{
            next=size_of::<SourceObservation>();
            for n in [size_of::<Arc<SourceObservation>>(),product(width,size_of::<f64>())?,b.max_record_bytes,
                product(next_contact_rows,size_of::<ObservedContact>())?,size_of::<OpticalAcquisition>(),b.max_record_bytes]{next=add(next,n)?;}
            raw_scratch=add(add(product(width,8)?,product(3,b.max_record_bytes)?)?,
                add(product(next_contact_rows,128)?,product(3,add(b.max_integer_bytes,160)?)?)?)?;
            if raw_scratch>b.max_prepared_bytes{return Err(UfError::Capacity("source observation preparation admission"));}
        }
        let complete=if self.rows.len()==ROWS{Some(self.actual_snapshot_size(true,b)?)}else{None};
        let (snapshot,field,preparation)=complete.map_or((0,0,0),|s|(s.retained_snapshot_payload,s.field_payload,s.preparation_payload));
        let predecessor_shell=add(size_of::<Self>(),product(self.rows.capacity(),size_of::<Arc<SourceObservation>>())?)?;
        let peak=add(add(retained,predecessor_shell)?,preparation.max(add(next,raw_scratch)?))?;
        Ok(SourceLogicalSize{retained_source_bytes:retained,next_observation_payload_bound:next,
            next_observation_preparation_bound:raw_scratch,complete_source_snapshot_payload_bound:snapshot,
            complete_field_payload_bound:field,preparation_peak_bound:peak})
    }
}
