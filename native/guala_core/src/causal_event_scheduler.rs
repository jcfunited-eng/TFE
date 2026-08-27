//! Exact causal event scheduler foundation (S15, Codex-corrected form).
//!
//! One entry per contact in a preallocated indexed binary heap ordered by
//! `(due_clock, contact_index)`. An entry's due clock is the CARRIER
//! crossing alone: the earliest clock at which carrier phase can reach a
//! whole elementary charge under the standing drive set at its last
//! settlement. Transition work is never scheduled for a sleeper — it is
//! evaluated synchronously when a gradient event wakes an endpoint, and the
//! catch-up below carries the predecessor work phase through unchanged as a
//! structural invariant (Codex-concurred physics: the quiescent branch
//! exports released work as heat and cannot move work phase).
//! MANDATORY WIRING CONDITION (Codex): every nonzero pump or passive-return
//! settlement is a waking endpoint event and must enter the frontier before
//! contact selection — otherwise a sleeper could sleep through the very
//! event that enables its work accumulation.
//! Firing early is lawful (settlement finds no crossing and reschedules
//! exactly); firing late is impossible by construction because the carrier
//! crossing clock is computed from the same exact arithmetic the settlement
//! itself uses.
//!
//! Companion contract (enforced by the integration layer, tested against
//! the settlement oracle below): every contact carries
//! `last_integrated_clock`; whenever a contact is read, settled, sealed, or
//! its endpoints change, its accumulators are first advanced exactly from
//! `last_integrated_clock` to the present clock under the standing drive —
//! so no observation or persistence can ever see stale phase. The schedule
//! is derived state: rebuilt from the organism on restore, never persisted,
//! and holding no cognitive authority.

/// Preallocated indexed min-heap over contacts.
///
/// Storage is three parallel arrays sized once to the contact count:
/// the heap of contact indices ordered by `(due_clock, contact_index)`,
/// each contact's current position in that heap (or NONE), and each
/// contact's due clock. Replacement and removal are O(log n) with no
/// scanning, no allocation after construction, and no stale entries.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CarrierCrossingSchedule {
    heap: Vec<u32>,
    position_by_contact: Vec<u32>,
    due_by_contact: Vec<u64>,
    len: usize,
}

const NO_POSITION: u32 = u32::MAX;

impl CarrierCrossingSchedule {
    pub(crate) fn with_contact_count(contact_count: usize) -> Self {
        assert!(contact_count < NO_POSITION as usize);
        Self {
            heap: vec![0; contact_count],
            position_by_contact: vec![NO_POSITION; contact_count],
            due_by_contact: vec![0; contact_count],
            len: 0,
        }
    }

    pub(crate) fn clear(&mut self) {
        for position in self.position_by_contact.iter_mut() {
            *position = NO_POSITION;
        }
        self.len = 0;
    }

    /// Read-only walk of every scheduled contact and its absolute due clock.
    /// Order is contact-index order, not due order; use `drain_due_at` for
    /// causal ordering. Used by the census probe and the restore report.
    pub(crate) fn scheduled_dues(&self) -> impl Iterator<Item = (usize, u64)> + '_ {
        self.heap[..self.len as usize].iter().map(move |contact| {
            (*contact as usize, self.due_by_contact[*contact as usize])
        })
    }

    pub(crate) fn scheduled_len(&self) -> usize {
        self.len
    }

    fn less(&self, left: u32, right: u32) -> bool {
        let left_due = self.due_by_contact[left as usize];
        let right_due = self.due_by_contact[right as usize];
        (left_due, left) < (right_due, right)
    }

    fn swap_heap(&mut self, a: usize, b: usize) {
        self.heap.swap(a, b);
        self.position_by_contact[self.heap[a] as usize] = a as u32;
        self.position_by_contact[self.heap[b] as usize] = b as u32;
    }

    fn sift_up(&mut self, mut index: usize) {
        while index > 0 {
            let parent = (index - 1) / 2;
            if self.less(self.heap[index], self.heap[parent]) {
                self.swap_heap(index, parent);
                index = parent;
            } else {
                break;
            }
        }
    }

    fn sift_down(&mut self, mut index: usize) {
        loop {
            let left = index * 2 + 1;
            if left >= self.len {
                break;
            }
            let right = left + 1;
            let smaller = if right < self.len && self.less(self.heap[right], self.heap[left])
            {
                right
            } else {
                left
            };
            if self.less(self.heap[smaller], self.heap[index]) {
                self.swap_heap(index, smaller);
                index = smaller;
            } else {
                break;
            }
        }
    }

    /// Set, replace, or remove a contact's due clock in O(log n).
    pub(crate) fn reschedule(&mut self, contact_index: usize, due_clock: Option<u64>) {
        let contact = contact_index as u32;
        let position = self.position_by_contact[contact_index];
        match (position, due_clock) {
            (NO_POSITION, None) => {}
            (NO_POSITION, Some(clock)) => {
                self.due_by_contact[contact_index] = clock;
                let index = self.len;
                self.heap[index] = contact;
                self.position_by_contact[contact_index] = index as u32;
                self.len += 1;
                self.sift_up(index);
            }
            (position, None) => {
                let index = position as usize;
                self.len -= 1;
                if index != self.len {
                    self.swap_heap(index, self.len);
                    self.position_by_contact[contact_index] = NO_POSITION;
                    self.sift_down(index);
                    self.sift_up(index);
                } else {
                    self.position_by_contact[contact_index] = NO_POSITION;
                }
            }
            (position, Some(clock)) => {
                self.due_by_contact[contact_index] = clock;
                let index = position as usize;
                self.sift_up(index);
                self.sift_down(self.position_by_contact[contact_index] as usize);
            }
        }
    }

    /// Pop every contact due at or before `clock`, in exact
    /// `(due_clock, contact_index)` order, into `due`. No allocation when
    /// `due` retains its capacity across clocks.
    pub(crate) fn drain_due_at(&mut self, clock: u64, due: &mut Vec<usize>) {
        due.clear();
        while self.len > 0 {
            let top = self.heap[0] as usize;
            if self.due_by_contact[top] > clock {
                break;
            }
            due.push(top);
            self.reschedule(top, None);
        }
    }
}


/// One full-contact schedule primitive: the retained integration clock and
/// the exact sleeping-span catch-up for BOTH accumulators plus heat.
///
/// Physics basis, from the settlement law's own branches: while a contact
/// sleeps (no endpoint event), its gradient direction is necessarily
/// Quiescent — a layer-10 gradient settlement is a pump event on an
/// endpoint, which wakes the contact. Under Quiescent direction the law
/// converts released work to exported heat each clock and leaves
/// transition_work_phase untouched. Therefore a sleeping span integrates:
/// carrier phase by the widened exact law, heat by work-per-clock times the
/// span, and work phase unchanged — and work-quantum crossings can occur
/// only on awake contacts, so the schedule's due clock is the carrier
/// crossing alone. This invariant is asserted at wiring: an active
/// gradient direction forces frontier membership.
///
/// WIDTH/READ HAZARD (Codex): the widened transition reports the BASE
/// interval in its `interval_microseconds` field, never the elapsed total;
/// downstream accounting must use phase/charges/heat only.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ContactIntegrationClock {
    pub(crate) last_integrated_clock: u64,
}

impl ContactIntegrationClock {
    /// Commit a prepared catch-up: the schedule advances only after the
    /// caller has accepted the physics, never before.
    pub(crate) fn commit(&mut self, prepared: PreparedIntegrationClock) {
        self.last_integrated_clock = prepared.successor_clock;
    }
}

/// The successor clock a catch-up prepares; applied only via `commit`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PreparedIntegrationClock {
    pub(crate) successor_clock: u64,
}

pub(crate) struct SleepingSpanCatchUp {
    pub(crate) prepared_clock: PreparedIntegrationClock,
    pub(crate) successor_phase: crate::elementary_charge_transfer::ChargeCarrierPhase,
    /// Carried through byte-identical from the predecessor: a sleeping span
    /// cannot move work phase, and the type enforces that invariance.
    pub(crate) transition_work_phase: crate::exact_rational::ExactRational,
    pub(crate) outward_elementary_charges: i128,
    pub(crate) exported_heat_zeptojoules: num_rational::BigRational,
}

/// Advance a sleeping contact exactly from its retained clock to `now`.
/// The runtime-resident derived event state of the causal scheduler: the
/// carrier-crossing schedule and last-integrated clock per contact, and
/// the membrane-recovery schedule per neuron. Derived, never encoded,
/// rebuilt at cold restore and on any topology change; owning it in the
/// runtime keeps every retained predecessor state value-consistent.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CausalEventResidency {
    pub(crate) contact_schedule: CarrierCrossingSchedule,
    pub(crate) contact_last_integrated: Vec<u64>,
    /// Per-neuron schedule of the PASSIVE MEMBRANE RETURN — the true
    /// rest transition, separate from the active gradient pump. The
    /// return path's sub-carrier phase lives here as derived state: a
    /// cold restore restarts each neuron's return progress at zero,
    /// forfeiting strictly less than one elementary charge per neuron.
    pub(crate) recovery_schedule: CarrierCrossingSchedule,
    pub(crate) recovery_phase: Vec<crate::elementary_charge_transfer::ChargeCarrierPhase>,
    pub(crate) recovery_last_integrated: Vec<u64>,
    pub(crate) contact_count: usize,
    pub(crate) neuron_count: usize,
    pub(crate) organism_clock: u64,
}

impl CausalEventResidency {
    pub(crate) fn matches_shape(&self, neuron_count: usize, contact_count: usize) -> bool {
        self.neuron_count == neuron_count && self.contact_count == contact_count
    }
}

pub(crate) fn catch_up_sleeping_contact(
    clock: ContactIntegrationClock,
    now: u64,
    predecessor_phase: crate::elementary_charge_transfer::ChargeCarrierPhase,
    predecessor_transition_work_phase: crate::exact_rational::ExactRational,
    standing_current_picoamperes: crate::exact_rational::ExactRational,
    standing_potential_difference_millivolts: crate::exact_rational::ExactRational,
    interval_microseconds: u32,
) -> Result<SleepingSpanCatchUp, crate::elementary_charge_transfer::ChargeTransferError> {
    use num_bigint::BigInt;
    use num_rational::BigRational;
    let zero = crate::exact_rational::ExactRational::integer(0);
    let one = crate::exact_rational::ExactRational::integer(1);
    let lawful_work_phase = matches!(
        predecessor_transition_work_phase.checked_cmp(zero),
        Ok(core::cmp::Ordering::Greater | core::cmp::Ordering::Equal)
    ) && matches!(
        predecessor_transition_work_phase.checked_cmp(one),
        Ok(core::cmp::Ordering::Less)
    );
    if !lawful_work_phase {
        return Err(crate::elementary_charge_transfer::ChargeTransferError::InvalidPhase);
    }
    let elapsed = now
        .checked_sub(clock.last_integrated_clock)
        .ok_or(crate::elementary_charge_transfer::ChargeTransferError::InvalidDuration)?;
    if elapsed == 0 {
        return Ok(SleepingSpanCatchUp {
            prepared_clock: PreparedIntegrationClock { successor_clock: now },
            successor_phase: predecessor_phase,
            transition_work_phase: predecessor_transition_work_phase,
            outward_elementary_charges: 0,
            exported_heat_zeptojoules: BigRational::from_integer(BigInt::from(0_u8)),
        });
    }
    let transition = crate::elementary_charge_transfer::settle_elementary_charge_transfer_clocks(
        predecessor_phase,
        standing_current_picoamperes,
        interval_microseconds,
        elapsed,
    )?;
    let (current_numerator, current_denominator) = standing_current_picoamperes.parts();
    let (difference_numerator, difference_denominator) =
        standing_potential_difference_millivolts.parts();
    // Released work each clock is |I x dV| x dt; Quiescent direction exports
    // it entirely as heat, so the span's heat is that rate times elapsed.
    let heat_numerator = BigInt::from(current_numerator.unsigned_abs())
        * BigInt::from(difference_numerator.unsigned_abs())
        * BigInt::from(interval_microseconds)
        * BigInt::from(elapsed);
    let heat_denominator =
        BigInt::from(current_denominator) * BigInt::from(difference_denominator);
    Ok(SleepingSpanCatchUp {
        prepared_clock: PreparedIntegrationClock { successor_clock: now },
        successor_phase: transition.successor_phase,
        transition_work_phase: predecessor_transition_work_phase,
        outward_elementary_charges: transition.outward_elementary_charges,
        exported_heat_zeptojoules: BigRational::new(heat_numerator, heat_denominator),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::elementary_charge_transfer::{
        settle_elementary_charge_transfer, ChargeCarrierPhase,
    };
    use crate::exact_rational::ExactRational;

    /// The scheduler's soundness claim against the settlement oracle: for a
    /// contact under constant standing drive, integrating clock-by-clock
    /// through the exact settlement law and integrating once with a catch-up
    /// over the same span produce identical phase and identical cumulative
    /// whole-carrier transfers — so a scheduled contact that sleeps between
    /// crossings loses nothing the swept contact would have had.
    #[test]
    fn catch_up_matches_clock_by_clock_settlement_oracle() {
        let drive = ExactRational::integer(3)
            .checked_div(ExactRational::integer(7))
            .unwrap();
        let interval: u32 = 250_000;
        let spans: [u32; 4] = [1, 2, 5, 9];
        for span in spans {
            let mut stepped_phase = ChargeCarrierPhase::zero();
            let mut stepped_whole: i128 = 0;
            for _ in 0..span {
                let transition =
                    settle_elementary_charge_transfer(stepped_phase, drive, interval)
                        .unwrap();
                stepped_phase = transition.successor_phase;
                stepped_whole += transition.outward_elementary_charges;
            }
            let caught_up = settle_elementary_charge_transfer(
                ChargeCarrierPhase::zero(),
                drive,
                interval * span,
            )
            .unwrap();
            assert_eq!(caught_up.successor_phase, stepped_phase, "span {span}");
            assert_eq!(
                caught_up.outward_elementary_charges, stepped_whole,
                "span {span}"
            );
        }
    }

    /// The computed crossing is exact: settling for exactly the computed
    /// clock count transfers at least one whole carrier; one clock fewer
    /// transfers none. Computed — never discovered by repeated settlement.
    #[test]
    fn computed_crossing_clock_is_exact_under_constant_drive() {
        use crate::elementary_charge_transfer::{
            next_whole_carrier_crossing_clocks, settle_elementary_charge_transfer_clocks,
        };
        let interval: u32 = 250_000;
        for (numerator, denominator) in
            [(1_i128, 10_000_000_i128), (3, 70_000_000), (-1, 12_345_678)]
        {
            let drive = ExactRational::integer(numerator)
                .checked_div(ExactRational::integer(denominator))
                .unwrap();
            let clocks = next_whole_carrier_crossing_clocks(
                ChargeCarrierPhase::zero(),
                drive,
                interval,
            )
            .unwrap()
            .expect("nonzero drive must cross");
            assert!(clocks > 1, "fixture must be multi-clock");
            let exact = settle_elementary_charge_transfer_clocks(
                ChargeCarrierPhase::zero(),
                drive,
                interval,
                clocks,
            )
            .unwrap();
            assert!(exact.outward_elementary_charges.unsigned_abs() >= 1);
            let early = settle_elementary_charge_transfer_clocks(
                ChargeCarrierPhase::zero(),
                drive,
                interval,
                clocks - 1,
            )
            .unwrap();
            assert_eq!(early.outward_elementary_charges, 0);
        }
    }

    /// Wide catch-up composes: integrating a-then-b clocks equals
    /// integrating a+b clocks in one step, across spans far beyond u32
    /// duration width — the exact property sealing and reads rely on.
    #[test]
    fn wide_catch_up_composes_across_spans() {
        use crate::elementary_charge_transfer::settle_elementary_charge_transfer_clocks;
        let interval: u32 = 250_000;
        let drive = ExactRational::integer(7)
            .checked_div(ExactRational::integer(90_000_019))
            .unwrap();
        for (first, second) in [(1_u64, 1_u64), (3, 8), (100_000, 4_294_967_295)] {
            let step_one = settle_elementary_charge_transfer_clocks(
                ChargeCarrierPhase::zero(),
                drive,
                interval,
                first,
            )
            .unwrap();
            let step_two = settle_elementary_charge_transfer_clocks(
                step_one.successor_phase,
                drive,
                interval,
                second,
            )
            .unwrap();
            let joined = settle_elementary_charge_transfer_clocks(
                ChargeCarrierPhase::zero(),
                drive,
                interval,
                first + second,
            )
            .unwrap();
            assert_eq!(joined.successor_phase, step_two.successor_phase);
            assert_eq!(
                joined.outward_elementary_charges,
                step_one.outward_elementary_charges + step_two.outward_elementary_charges,
            );
        }
    }


    /// Sol's falsifiers: nonzero and boundary starting phases, both signs.
    #[test]
    fn catch_up_from_nonzero_and_boundary_phases_matches_oracle() {
        use crate::elementary_charge_transfer::settle_elementary_charge_transfer;
        let interval: u32 = 250_000;
        for (phase_n, phase_d) in
            [(1_i128, 3_u128), (-2, 5), (999_999, 1_000_000), (-999_999, 1_000_000)]
        {
            for (drive_n, drive_d) in [(7_i128, 90_000_019_i128), (-3, 40_000_001)] {
                let start = ChargeCarrierPhase::new(phase_n, phase_d).unwrap();
                let drive = ExactRational::integer(drive_n)
                    .checked_div(ExactRational::integer(drive_d))
                    .unwrap();
                let span = 11_u64;
                let mut stepped = start;
                let mut whole = 0_i128;
                for _ in 0..span {
                    let t = settle_elementary_charge_transfer(stepped, drive, interval)
                        .unwrap();
                    stepped = t.successor_phase;
                    whole += t.outward_elementary_charges;
                }
                let mut clock = ContactIntegrationClock { last_integrated_clock: 100 };
                let caught = catch_up_sleeping_contact(
                    clock,
                    100 + span,
                    start,
                    ExactRational::integer(0),
                    drive,
                    ExactRational::integer(2),
                    interval,
                )
                .unwrap();
                assert_eq!(caught.successor_phase, stepped);
                assert_eq!(caught.outward_elementary_charges, whole);
                assert_eq!(clock.last_integrated_clock, 100);
                clock.commit(caught.prepared_clock);
                assert_eq!(clock.last_integrated_clock, 100 + span);
            }
        }
    }

    /// Heat over a sleeping span is exactly rate times elapsed; zero span
    /// is identity.
    #[test]
    fn sleeping_heat_is_rate_times_span_and_zero_span_is_identity() {
        use num_bigint::BigInt;
        use num_rational::BigRational;
        let drive = ExactRational::integer(3)
            .checked_div(ExactRational::integer(2))
            .unwrap();
        let difference = ExactRational::integer(-5)
            .checked_div(ExactRational::integer(4))
            .unwrap();
        let mut clock = ContactIntegrationClock { last_integrated_clock: 40 };
        let lawful_work = ExactRational::integer(7)
            .checked_div(ExactRational::integer(10))
            .unwrap();
        let caught = catch_up_sleeping_contact(
            clock,
            48,
            ChargeCarrierPhase::zero(),
            lawful_work,
            drive,
            difference,
            250_000,
        )
        .unwrap();
        assert_eq!(
            caught.exported_heat_zeptojoules,
            BigRational::from_integer(BigInt::from(3_750_000_u64)),
        );
        clock.commit(caught.prepared_clock);
        let same = catch_up_sleeping_contact(
            clock,
            48,
            caught.successor_phase,
            caught.transition_work_phase,
            drive,
            difference,
            250_000,
        )
        .unwrap();
        assert_eq!(caught.transition_work_phase, lawful_work);
        assert!(catch_up_sleeping_contact(
            clock,
            50,
            ChargeCarrierPhase::zero(),
            ExactRational::integer(7),
            drive,
            difference,
            250_000,
        )
        .is_err());
        assert_eq!(same.successor_phase, caught.successor_phase);
        assert_eq!(same.transition_work_phase, caught.transition_work_phase);
        assert_eq!(same.outward_elementary_charges, 0);
        assert!(same.exported_heat_zeptojoules
            == BigRational::from_integer(BigInt::from(0_u8)));
    }

    #[test]
    fn indexed_heap_replaces_and_drains_in_exact_order_without_stale_entries() {
        let mut schedule = CarrierCrossingSchedule::with_contact_count(8);
        schedule.reschedule(7, Some(10));
        schedule.reschedule(3, Some(10));
        schedule.reschedule(5, Some(4));
        schedule.reschedule(7, Some(12));
        schedule.reschedule(5, None);
        let mut due = Vec::new();
        schedule.drain_due_at(11, &mut due);
        assert_eq!(due, vec![3]);
        schedule.drain_due_at(12, &mut due);
        assert_eq!(due, vec![7]);
        assert_eq!(schedule.scheduled_len(), 0);
        schedule.reschedule(2, Some(6));
        schedule.reschedule(2, Some(5));
        schedule.drain_due_at(5, &mut due);
        assert_eq!(due, vec![2]);
    }
}
