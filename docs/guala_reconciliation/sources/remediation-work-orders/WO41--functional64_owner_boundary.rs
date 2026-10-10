//! Typed host orchestration only. No native-to-Python callback is registered.
use std::sync::Arc;
use pyo3::prelude::*;
use pyo3::exceptions::{PyTypeError,PyValueError};
use pyo3::types::{PyBool,PyBytes,PyDict,PyInt,PyTuple};
use crate::functional64_owner::{Functional64Owner,OwnerBounds,OwnerError,PreparedBeat,BeatSummary};
use crate::functional64_material::PaidThermalWork;
use crate::virtual_articulated_body::{ArticulatedBodyState,BODY_AXES};

pub(crate) fn owner_error(error:OwnerError)->PyErr{PyValueError::new_err(format!("{error:?}"))}
fn integer(value:&Bound<'_,PyAny>)->PyResult<()>{
    if !value.is_instance_of::<PyInt>()||value.is_instance_of::<PyBool>(){return Err(PyTypeError::new_err("physical integer requires an integer, not bool or coercion"));}Ok(())
}
pub(crate) fn parse_bounds(value:&Bound<'_,PyTuple>)->PyResult<OwnerBounds>{
    if value.len()!=13{return Err(PyValueError::new_err("complete owner admission has exactly thirteen fields"));}
    let mut fields=[0usize;13];for(i,item)in value.iter().enumerate(){integer(&item)?;fields[i]=item.extract()?;}
    OwnerBounds::from_values(fields).map_err(owner_error)
}
type AxisRow=(u8,String,String,i32,i32,i32,i32);
fn axes(body:&ArticulatedBodyState)->Vec<AxisRow>{BODY_AXES.iter().map(|&axis|{
    let a=body.anatomy(axis);(axis as u8,axis.anatomical_name().to_owned(),a.unit.physical_name().to_owned(),body.axis(axis),a.minimum,a.neutral,a.maximum)
}).collect()}
fn paid_rows<'py>(py:Python<'py>,rows:&[PaidThermalWork])->PyResult<Bound<'py,PyTuple>>{
    let mut values=Vec::with_capacity(rows.len());for row in rows{values.push((PyBytes::new(py,&row.identity),PyTuple::new(py,row.units)?));}PyTuple::new(py,values)
}
fn pcm<'py>(py:Python<'py>,samples:&[i16])->Bound<'py,PyBytes>{
    let mut bytes=Vec::with_capacity(samples.len()*2);for sample in samples{bytes.extend_from_slice(&sample.to_le_bytes());}PyBytes::new(py,&bytes)
}
fn summary<'py>(py:Python<'py>,s:&BeatSummary)->PyResult<Bound<'py,PyDict>>{
    let d=PyDict::new(py);d.set_item("start_millisecond",s.start_ms)?;d.set_item("end_millisecond",s.end_ms)?;
    d.set_item("elapsed_milliseconds",250)?;d.set_item("reserve_before_micrograms",s.reserve_before)?;d.set_item("reserve_after_micrograms",s.reserve_after)?;
    d.set_item("intake_micrograms",s.intake_micrograms)?;d.set_item("assimilated_micrograms",s.assimilated_micrograms)?;
    d.set_item("reserve_debited_micrograms",s.reserve_debited_micrograms)?;
    d.set_item("debited_work_units",PyTuple::new(py,s.debited_work)?)?;d.set_item("supplied_work_units",PyTuple::new(py,s.supplied_work)?)?;
    d.set_item("transducer_heat_units",PyTuple::new(py,s.transducer_heat)?)?;d.set_item("recovered_field_work_units",PyTuple::new(py,s.recovered_field_work)?)?;
    d.set_item("paid_thermal",paid_rows(py,&s.paid_thermal)?)?;d.set_item("fields_delivered",s.fields_delivered)?;
    d.set_item("source_rows_admitted",s.source_rows_admitted)?;d.set_item("source_rows_unacquired",s.source_rows_unacquired)?;
    d.set_item("articulatory_applied_quanta",s.articulatory_applied)?;d.set_item("articulatory_stalled_quanta",s.articulatory_stalled)?;
    d.set_item("numerical_column_names",PyTuple::new(py,["supply_j","field_switch_j","source_heat_j","contact_heat_j","phase_heat_j","gate_heat_j",
        "exported_j","plastic_heat_j","return_map_dissipation_j","stop_dissipation_j","energy_residual_j","nonlinear_bound","error_estimate",
        "circuit_tail_charge_c","circuit_tail_work_j","circuit_projection_defect_v",
        "contact_energy_change_j","contact_energy_change_lower_j","contact_energy_change_upper_j"])?)?;
    let count=s.intervals.iter().map(|row|row.end_discharges.len()).sum();
    let mut discharges=Vec::with_capacity(count);
    for (index,row) in s.intervals.iter().enumerate(){
        for &(terminal,carriers) in row.end_discharges.iter(){
            discharges.push((index+1,terminal,carriers));
        }
    }
    d.set_item("terminal_end_discharges",PyTuple::new(py,discharges)?)?;
    let mut intervals=Vec::with_capacity(s.intervals.len());for row in s.intervals.iter(){
        intervals.push((row.powered_ticks,PyTuple::new(py,row.numerical)?,row.force_terms,row.yield_queries,row.staged_bytes));}
    d.set_item("material_intervals",PyTuple::new(py,intervals)?)?;d.set_item("powered_offset_fractional_bits",52)?;Ok(d)
}

#[pyclass(name="Functional64Core",frozen)]
pub(crate) struct PyFunctional64Core{pub(crate) current:Arc<Functional64Owner>}
#[pymethods]
impl PyFunctional64Core{
    #[getter]fn identity(&self)->&str{&self.current.identity}
    #[getter]fn organism_tick(&self)->u64{self.current.organism_tick}
    #[getter]fn max_encoded_bytes(&self)->usize{self.current.bounds.max_owner_bytes}
    #[getter]fn source_millisecond(&self)->PyResult<i64>{self.current.source_millisecond().map_err(owner_error)}
    #[getter]fn reserve_micrograms(&self)->u64{self.current.reserve_micrograms()}
    #[getter]fn reserve_capacity_micrograms(&self)->u64{self.current.reserve_capacity_micrograms()}
    #[getter]fn unassimilated_digestible_micrograms(&self)->u64{self.current.unassimilated_digestible_micrograms}
    #[getter]fn cochlear_origin_millisecond(&self)->i64{self.current.cochlear_origin_ms}
    #[getter]fn cochlear_current_bytes<'py>(&self,py:Python<'py>)->Bound<'py,PyBytes>{PyBytes::new(py,&self.current.cochlear_current)}
    #[getter]fn pending_self_pcm_s16le<'py>(&self,py:Python<'py>)->Bound<'py,PyBytes>{PyBytes::new(py,&self.current.pending_self_pcm_s16le)}
    // Explicit bounded observation only; the physical loop never calls these.
    #[getter]fn phase_pairs_le<'py>(&self,py:Python<'py>)->Bound<'py,PyBytes>{
        let bytes=self.current.phase_pairs_le();PyBytes::new(py,&bytes)
    }
    #[getter]fn pending_terminal_carriers<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyTuple>>{
        PyTuple::new(py,self.current.pending_terminal_carriers().iter().copied())
    }
    #[getter]fn field_delivery_evidence<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyTuple>>{
        let mut rows=Vec::with_capacity(2);
        for d in self.current.field_delivery_evidence(){
            rows.push((PyBytes::new(py,d.identity),d.published.parts(),d.gate_index,d.remaining_ms,d.installed));
        }
        PyTuple::new(py,rows)
    }
    fn retained_contact_evidence<'py>(&self,py:Python<'py>,max_bytes:&Bound<'_,PyAny>)->PyResult<(i64,Bound<'py,PyBytes>)>{
        integer(max_bytes)?;
        let (at,bytes)=self.current.retained_contact_evidence(max_bytes.extract()?).map_err(owner_error)?;
        Ok((at,PyBytes::new(py,&bytes)))
    }
    #[getter]fn body_axes<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyTuple>>{PyTuple::new(py,axes(&self.current.body))}
    #[getter]fn thermal_source_identities<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyTuple>>{
        let ids=self.current.thermal_source_identities().map_err(owner_error)?;PyTuple::new(py,ids.iter().map(|b|PyBytes::new(py,b)))
    }
    fn resource_sizing<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyDict>>{
        let rows=self.current.resource_sizing().map_err(owner_error)?;let result=PyDict::new(py);
        for(name,bytes)in rows{result.set_item(name,bytes)?;}Ok(result)
    }
    fn encoded<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyBytes>>{
        let bytes=py.allow_threads(||self.current.encode()).map_err(owner_error)?;
        Ok(PyBytes::new(py,&bytes))
    }
    fn prepare_beat<'py>(&self,py:Python<'py>,optical_record:&Bound<'_,PyBytes>)->PyResult<PyFunctional64PreparedBeat>{
        if optical_record.as_bytes().len()>self.current.bounds.source.max_record_bytes{return Err(PyValueError::new_err("initial optical transport exceeds admitted record bytes"));}
        let optical_bytes:Arc<[u8]>=optical_record.as_bytes().into();
        let prepared=py.allow_threads(||self.current.prepare_beat(optical_bytes)).map_err(owner_error)?;
        Ok(PyFunctional64PreparedBeat{prepared})
    }
    #[staticmethod]
    fn restore<'py>(py:Python<'py>,encoded:&Bound<'_,PyBytes>,geometry_record:&Bound<'_,PyBytes>,surface_sites:&Bound<'_,PyAny>,bounds:&Bound<'_,PyTuple>)->PyResult<Self>{
        let b=parse_bounds(bounds)?;integer(surface_sites)?;let sites:usize=surface_sites.extract()?;
        if geometry_record.as_bytes().len()>b.source.max_record_bytes{return Err(PyValueError::new_err("actual restored source geometry exceeds record admission"));}
        let enc_bytes=encoded.as_bytes();
        let geom_bytes:Arc<[u8]>=geometry_record.as_bytes().into();
        let current=py.allow_threads(||Functional64Owner::decode(enc_bytes,geom_bytes,sites,b)).map_err(owner_error)?;
        Ok(Self{current:Arc::new(current)})
    }
}

#[pyclass(name="Functional64PreparedBeat")]
pub(crate) struct PyFunctional64PreparedBeat{prepared:PreparedBeat}
type Millisecond<'py>=(i64,i32,i32,i32,i32,i32,i32,Bound<'py,PyTuple>,Bound<'py,PyBytes>,Bound<'py,PyBytes>);
#[pymethods]
impl PyFunctional64PreparedBeat{
    #[getter]fn source_due(&self)->bool{self.prepared.source_due()}
    #[getter]fn source_millisecond(&self)->PyResult<i64>{self.prepared.source_millisecond().map_err(owner_error)}
    #[getter]fn body_axes<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyTuple>>{PyTuple::new(py,axes(self.prepared.body()))}
    #[getter]fn prepared_body_evidence<'py>(&self,py:Python<'py>)->PyResult<Bound<'py,PyDict>>{
        let(voice,rows)=self.prepared.prepared_body_evidence().map_err(owner_error)?;let d=PyDict::new(py);
        d.set_item("pressure_pcm",pcm(py,&voice.radiated_pressure_pcm))?;
        d.set_item("mechanical_pcm",PyTuple::new(py,voice.body_mechanical_trajectories.iter().map(|r|pcm(py,r)))?)?;
        let consequences=rows.iter().map(|r|(r.axis.anatomical_name().to_owned(),r.unit.physical_name().to_owned(),r.predecessor_position,r.successor_position,
            r.signed_displacement,r.toward_minimum_carriers,r.toward_maximum_carriers,r.opposed_carriers_per_terminal,r.applied_displacement_quanta,r.stalled_carriers));
        d.set_item("proprioceptive_consequences",PyTuple::new(py,consequences)?)?;
        d.set_item("pressure_receipt",(voice.peak_transducer_surface_velocity_pcm,voice.glottal_open_samples_at_apex,
            voice.mouth_area_square_millimetres_at_apex,voice.perioral_area_displacement_square_millimetres,
            voice.applied_motor_quanta,voice.stalled_motor_quanta,voice.relaxation_sample_count))?;
        if let Some(trajectory)=&voice.passive_body_trajectory{
            let mut positions=Vec::new();for frame in 0..trajectory.frame_count(){for axis in 0..trajectory.axes().len(){
                positions.push(trajectory.position(frame,axis).ok_or_else(||PyValueError::new_err("actual passive body sample unavailable"))?);}}
            d.set_item("passive_positions",(PyTuple::new(py,trajectory.axes().iter().map(|a|*a as u8))?,PyTuple::new(py,positions)?,trajectory.frame_count()))?;
        }else{d.set_item("passive_positions",py.None())?;}Ok(d)
    }
    fn prepare_millisecond<'py>(&mut self,py:Python<'py>)->PyResult<Millisecond<'py>>{
        let row=py.allow_threads(||self.prepared.prepare_millisecond()).map_err(owner_error)?;
        Ok((row.start_ms,row.dx_mm,row.dy_mm,row.dyaw_mdeg,row.left_grip_um,row.right_grip_um,row.jaw_um,
            paid_rows(py,&row.paid_thermal)?,PyBytes::new(py,&row.own_ear_pcm),PyBytes::new(py,&row.pressure_pcm)))
    }
    fn accept_world<'py>(&mut self,py:Python<'py>,root_interval_record:&Bound<'_,PyBytes>,intake_micrograms:&Bound<'_,PyAny>)->PyResult<()>{
        integer(intake_micrograms)?;
        let intake:u64=intake_micrograms.extract()?;
        let record=root_interval_record.as_bytes();
        py.allow_threads(||self.prepared.accept_world(record,intake)).map_err(owner_error)
    }
    #[allow(clippy::too_many_arguments)]
    fn accept_source<'py>(&mut self,py:Python<'py>,cochlear_record:&Bound<'_,PyBytes>,optical_record:&Bound<'_,PyBytes>,surface_ratios:&Bound<'_,PyBytes>,
        surface_evidence:&Bound<'_,PyBytes>,skin_ratio:&Bound<'_,PyBytes>,received_covered:&Bound<'_,PyAny>,own_covered:&Bound<'_,PyAny>)->PyResult<()>{
        if !received_covered.is_instance_of::<PyBool>()||!own_covered.is_instance_of::<PyBool>(){
            return Err(PyTypeError::new_err("actual event-stream coverage requires explicit booleans"));}
        let limit=self.prepared.record_byte_limit();
        for bytes in [cochlear_record,optical_record,surface_ratios,surface_evidence,skin_ratio]{
            if bytes.as_bytes().len()>limit{return Err(PyValueError::new_err("actual source transport exceeds admitted record bytes"));}}
        let cochlear=cochlear_record.as_bytes();
        let optical:Arc<[u8]>=optical_record.as_bytes().into();
        let ratios:Arc<[u8]>=surface_ratios.as_bytes().into();
        let evidence:Arc<[u8]>=surface_evidence.as_bytes().into();
        let skin:Arc<[u8]>=skin_ratio.as_bytes().into();
        let rx:bool=received_covered.extract()?;
        let own:bool=own_covered.extract()?;
        py.allow_threads(||self.prepared.accept_source(cochlear,optical,ratios,evidence,skin,rx,own)).map_err(owner_error)
    }
    fn finish<'py>(&mut self,py:Python<'py>,cochlear_current_bytes:&Bound<'_,PyBytes>)->PyResult<(PyFunctional64Core,Bound<'py,PyBytes>,Bound<'py,PyDict>)>{
        if cochlear_current_bytes.as_bytes().len()!=3156{return Err(PyValueError::new_err("actual current cochlear framing is3156 bytes"));}
        let cochlear_bytes:Arc<[u8]>=cochlear_current_bytes.as_bytes().into();
        let(core,pressure,evidence)=py.allow_threads(||self.prepared.finish(cochlear_bytes)).map_err(owner_error)?;
        Ok((PyFunctional64Core{current:Arc::new(core)},PyBytes::new(py,&pressure),summary(py,&evidence)?))
    }
}
pub(crate) fn register(module:&Bound<'_,PyModule>)->PyResult<()>{
    module.add_class::<PyFunctional64Core>()?;module.add_class::<PyFunctional64PreparedBeat>()?;Ok(())
}
