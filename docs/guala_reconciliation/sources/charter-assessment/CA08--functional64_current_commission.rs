//! Explicit new material commissioning from ONE complete incumbent current.
//! This is never ordinary cold restore and never executes legacy cognition.
//! Authority: collaborative_todo.md current-history preservation boundary.
use super::*;
use crate::cortical_column::current_codec::CurrentView;

#[derive(Clone, Copy, Debug)]
pub(crate) struct CommissionLimits {
    pub(crate) max_custody_bytes: usize,
    pub(crate) max_contact_rows: usize,
    /// Logical payload/scratch bound; allocator metadata and capacity slack are
    /// separately part of the complete owner's measured process envelope.
    pub(crate) max_staged_payload_bytes: usize,
}
fn plus(a:usize,b:usize)->Result<usize>{a.checked_add(b).ok_or(MaterialError::Capacity("commission payload overflow"))}
fn times(a:usize,b:usize)->Result<usize>{a.checked_mul(b).ok_or(MaterialError::Capacity("commission payload overflow"))}
fn admit(bytes:usize,limits:CommissionLimits)->Result<()>{
    if bytes>limits.max_staged_payload_bytes{Err(MaterialError::Capacity("same-current commission payload admission"))}else{Ok(())}
}
fn array_bytes<T>(n:usize)->Result<usize>{times(n,std::mem::size_of::<T>())}
fn arc_vec_payload<T>(n:usize)->Result<usize>{plus(std::mem::size_of::<Vec<T>>(),array_bytes::<T>(n)?)}
fn pages_payload<T:Clone>(len:usize,branches:usize,leaves:usize)->Result<usize>{
    let root=len.div_ceil(PAGE*FAN);
    let root=arc_vec_payload::<Option<Branch<T>>>(root)?;
    let branch=times(branches,arc_vec_payload::<Option<Leaf<T>>>(FAN)?)?;
    let leaf=times(leaves,arc_vec_payload::<T>(PAGE)?)?;
    plus(root,plus(branch,leaf)?)
}
fn geometry_retained_payload()->Result<usize>{
    // Geometry is inline in Anatomy. Its three Arc slices own these arrays.
    plus(array_bytes::<bool>(4096)?,plus(array_bytes::<u32>(NODES)?,array_bytes::<[f64;3]>(NODES)?)?)
}
fn geometry_conversion_scratch()->Result<usize>{
    // Geometry::new's maximum transient above its final arrays occurs while
    // old three-bound zeros + construction Vec coexist with the new Arc slice.
    array_bytes::<[f64;3]>(2*NODES)
}
fn fixed_scratch()->Result<usize>{
    plus(array_bytes::<u32>(NODES)?,plus(array_bytes::<bool>(4096)?,
        plus(array_bytes::<u16>(INPUTS)?,array_bytes::<f64>(64)?)?)?)
}
fn positive_threshold(bits:u32)->Result<f64>{
    let value=f32::from_bits(bits);
    if !value.is_finite()||value<=0.0{return Err(MaterialError::Invalid("retained physical yield threshold"));}
    Ok(value as f64)
}
fn actual_thermal(load:&ThermalLoad)->Result<()>{
    // Root supplies this from the actual world thermal anatomy and source row:
    // magic + original32-byte receipt + exact node index + actual microwatts.
    if load.identity.len()!=56||&load.identity[..8]!=b"GL64TH01"||load.microwatts!=41_500_000{
        return Err(MaterialError::Invalid("same-current thermal source identity or constitution"));
    }
    let declared=u64::from_le_bytes(load.identity[48..56].try_into().unwrap());
    if declared!=load.microwatts{return Err(MaterialError::Invalid("thermal identity disagrees with actual source power"));}
    Ok(())
}
fn input_node(index:usize)->u16{
    let node=if index<480{(index/60)*320+160+index%60}
        else if index<512{let n=index-480;let ear=n/16;let band=n%16;(8+4*ear+band/4)*320+160+band%4}
        else{let t=index-512;(16+t%8)*320+160+t/8};
    node as u16
}

struct PageCounts{weight_branches:usize,weight_leaves:usize,incident_branches:usize,incident_leaves:usize,
    incident_nodes:usize,incident_rows:usize}
fn material_payload(counts:&PageCounts)->Result<usize>{
    let mut n=plus(std::mem::size_of::<Functional64Material>(),std::mem::size_of::<Anatomy>())?;
    n=plus(n,geometry_retained_payload()?)?;
    n=plus(n,array_bytes::<u16>(INPUTS)?)?;
    n=plus(n,std::mem::size_of::<ThermalLoad>())?;
    n=plus(n,pages_payload::<PhasePair>(NODES,0,0)?)?;
    n=plus(n,pages_payload::<Ring>(FACTS,0,0)?)?;
    n=plus(n,pages_payload::<f64>(RAW_SLOTS,counts.weight_branches,counts.weight_leaves)?)?;
    n=plus(n,pages_payload::<Arc<Vec<u32>>>(NODES,counts.incident_branches,counts.incident_leaves)?)?;
    n=plus(n,std::mem::size_of::<Vec<u32>>())?; // incident's one shared empty Vec
    n=plus(n,times(counts.incident_nodes,std::mem::size_of::<Vec<u32>>())?)?;
    n=plus(n,array_bytes::<u32>(counts.incident_rows)?)?;
    n=plus(n,array_bytes::<Fact>(FACTS)?)?;
    n=plus(n,arc_vec_payload::<Gate>(INPUTS+TERMINALS)?)?;
    n=plus(n,array_bytes::<Option<ExactTime>>(INPUTS)?)?;
    n=plus(n,pages_payload::<bool>(RAW_SLOTS,0,0)?)?; // empty changed-slot flags
    n=plus(n,std::mem::size_of::<BTreeSet<u16>>())?;
    Ok(n)
}
fn commission_scratch(rows:usize,counts:&PageCounts)->Result<usize>{
    let mut n=fixed_scratch()?;
    n=plus(n,arc_vec_payload::<(u32,f64)>(rows)?)?;
    n=plus(n,geometry_conversion_scratch()?)?;
    // rebuild_incident has a bounded temporary map of mounted node/slot rows.
    // Count its logical keys/Vec values and data; node allocator overhead is not
    // falsely claimed by this logical-payload admission.
    n=plus(n,std::mem::size_of::<BTreeMap<u16,Vec<u32>>>())?;
    n=plus(n,array_bytes::<(u16,Vec<u32>)>(counts.incident_nodes)?)?;
    n=plus(n,array_bytes::<u32>(counts.incident_rows)?)?;
    // Initial empty incident directory coexists with its reconstructed one.
    n=plus(n,pages_payload::<Arc<Vec<u32>>>(NODES,0,0)?)?;
    n=plus(n,std::mem::size_of::<Vec<u32>>())?;
    // facts Vec→Arc slice conversion temporarily retains both payloads.
    n=plus(n,array_bytes::<Fact>(FACTS)?)?;
    Ok(n)
}

/// Commission the explicitly new functional material using one actual archive.
/// The complete owner supplies reserve/thermal/clock from that SAME paired
/// predecessor. Ordinary new-material decoding must never call this function.
pub(crate) fn commission_from_current(current:&CurrentView,clock:ExactTime,
    capacity_ug:u64,reserve_ug:u64,thermal:&ThermalLoad,limits:CommissionLimits)->Result<Functional64Material>{
    if capacity_ug!=500_000||reserve_ug>capacity_ug{
        return Err(MaterialError::Invalid("actual retained body capacity or reserve"));
    }
    actual_thermal(thermal)?;
    let custody=plus(current.bytes().len(),thermal.identity.len())?;
    if custody>limits.max_custody_bytes{return Err(MaterialError::Capacity("original current custody admission"));}
    let count=current.contacts().len();
    if count>limits.max_contact_rows{return Err(MaterialError::Capacity("original current contact admission"));}
    let borrowed=plus(custody,std::mem::size_of::<CurrentView>())?;
    let fixed=plus(fixed_scratch()?,plus(std::mem::size_of::<Geometry>(),
        plus(geometry_retained_payload()?,geometry_conversion_scratch()?)?)?)?;
    admit(plus(borrowed,fixed)?,limits)?;
    let mut yields=[0.0;64];
    for (index,value)in yields.iter_mut().enumerate(){
        let column=current.column(index).ok_or(MaterialError::Invalid("complete current column missing"))?;
        if column.metadata().column_id!=index as u64{return Err(MaterialError::Invalid("retained column identity differs from declared topology"));}
        *value=positive_threshold(column.parameters().yield_threshold)?;
    }
    let global=positive_threshold(current.global_threshold_bits())?;
    for row in current.contacts(){
        if !f32::from_bits(row.bits).is_finite(){return Err(MaterialError::Invalid("nonfinite retained physical contact"));}
    }
    let mut severed=[false;4096];
    for (index,value)in severed.iter_mut().enumerate(){
        *value=current.severed(index/64,index%64).ok_or(MaterialError::Invalid("complete current severing missing"))?;
    }
    let geometry=Geometry::new(Arc::from(&severed[..]),yields,global).map_err(MaterialError::Invalid)?;
    let mut endpoints=[0u32;NODES];
    let mut counts=PageCounts{weight_branches:0,weight_leaves:0,incident_branches:0,incident_leaves:0,incident_nodes:0,incident_rows:0};
    let mut previous_leaf=None;let mut previous_branch=None;
    for row in current.contacts(){
        let slot=row.raw_slot as usize;let leaf=slot/PAGE;let branch=leaf/FAN;
        if previous_leaf!=Some(leaf){counts.weight_leaves+=1;previous_leaf=Some(leaf);}
        if previous_branch!=Some(branch){counts.weight_branches+=1;previous_branch=Some(branch);}
        let weight=f32::from_bits(row.bits);
        // Negativezero retains a weight page/row but has no physical current
        // incidence; this is exactly the material's rebuild_incident law.
        if weight!=0.0{if let Some(contact)=geometry.contact(slot){
            endpoints[contact.from as usize]=endpoints[contact.from as usize].checked_add(1).ok_or(MaterialError::Capacity("incident count"))?;
            if contact.to!=contact.from{endpoints[contact.to as usize]=endpoints[contact.to as usize].checked_add(1).ok_or(MaterialError::Capacity("incident count"))?;}
        }}
    }
    previous_leaf=None;previous_branch=None;
    for (node,&n)in endpoints.iter().enumerate(){if n!=0{
        counts.incident_nodes+=1;counts.incident_rows=plus(counts.incident_rows,n as usize)?;
        let leaf=node/PAGE;let branch=leaf/FAN;
        if previous_leaf!=Some(leaf){counts.incident_leaves+=1;previous_leaf=Some(leaf);}
        if previous_branch!=Some(branch){counts.incident_branches+=1;previous_branch=Some(branch);}
    }}
    let payload=plus(borrowed,plus(material_payload(&counts)?,commission_scratch(count,&counts)?)?)?;
    admit(payload,limits)?;
    let mut weights=Vec::new();
    weights.try_reserve_exact(count).map_err(|_|MaterialError::Capacity("widened current allocation"))?;
    for row in current.contacts(){weights.push((row.raw_slot,f32::from_bits(row.bits)as f64));}
    let input_nodes:[u16;INPUTS]=std::array::from_fn(input_node);
    let anatomy=Arc::new(Anatomy::declare(geometry,Arc::from(&input_nodes[..]),current.bytes().clone(),capacity_ug,
        Arc::from(std::slice::from_ref(thermal)))?);
    Functional64Material::commission(anatomy,clock,&weights,reserve_ug)
}

#[cfg(test)]
#[path="functional64_current_commission_tests.rs"]
mod tests;
