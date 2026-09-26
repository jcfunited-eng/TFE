"""AUT-01 storage-law falsifiers, not autonomous feeding or physical-learning proof.

Fixtures below are explicit synthetic record shapes. They test integrity and
capacity only; no world, live endpoint, caretaker or checkpoint is constructed.
"""
from __future__ import annotations

import copy
import json
import unittest

from dsf_ai_service.episodic_binding_engine import (
    bound_waking_moments, consecutive_motor_trials, qualifies_for_retention,
    retained_episode_keys,
)


def motor(tick, *, intake=0, previous=None, target="fixture-target", refusal=None):
    key = f"motor:{tick}"
    return key, {
        "count": 1, "tick": tick + 1, "salience": 0.0,
        "source": "motor", "fed": intake,
        "motor_transition": {
            "key": key, "start_tick": tick, "end_tick": tick + 1,
            "pre": f"cue:{tick}", "post": f"cue:{tick + 1}",
            "action": "bite" if intake else "step", "target": target,
            "observed_subject": target, "intake": intake,
            "refusal": refusal, "previous": previous,
        },
    }


def route(start, length):
    records = {}
    previous = None
    for i in range(length):
        key, entry = motor(start + i, previous=previous, intake=17 if i == length - 1 else 0)
        records[key] = entry
        previous = key
    return records, previous


class WakingRetention(unittest.TestCase):
    def test_intake_qualifies_without_count_or_salience_inflation(self):
        key, entry = motor(4, intake=1)
        before = copy.deepcopy(entry)
        self.assertTrue(qualifies_for_retention(entry))
        self.assertEqual(retained_episode_keys({key: entry}, key), (key,))
        self.assertEqual(entry, before)
        self.assertFalse(qualifies_for_retention(motor(4)[1]))
        self.assertFalse(qualifies_for_retention(motor(4, intake=1, refusal="refused")[1]))

    def test_waypoint_changes_do_not_invent_a_time_or_sensory_gap(self):
        _, a = motor(1, target="fixture-door")
        _, b = motor(2, target="fixture-subject")
        self.assertTrue(consecutive_motor_trials(a["motor_transition"], b["motor_transition"]))
        for field, value in (("start_tick", 7), ("pre", "different"), ("refusal", "refused")):
            changed = dict(b["motor_transition"], **{field: value})
            self.assertFalse(consecutive_motor_trials(a["motor_transition"], changed))

    def test_refusal_and_previous_relief_end_successful_route_support(self):
        _, b = motor(2)
        for a in (motor(1, refusal="collision")[1], motor(1, intake=17)[1]):
            self.assertFalse(consecutive_motor_trials(a["motor_transition"], b["motor_transition"]))

    def test_real_edge_shape_survives_changed_targets(self):
        records, root = route(10, 3)
        records["motor:10"]["motor_transition"]["target"] = "fixture-door"
        self.assertEqual(retained_episode_keys(records, root), ("motor:12", "motor:11", "motor:10"))
        records["motor:10"]["motor_transition"]["refusal"] = "collision"
        self.assertEqual(retained_episode_keys(records, root), ("motor:12", "motor:11"))

    def test_capacity_pressure_keeps_qualified_route_whole(self):
        records, root = route(1, 3)
        retained = copy.deepcopy(records)
        for tick in range(20, 200):
            key, entry = motor(tick)
            candidate = dict(records, **{key: entry})
            before = copy.deepcopy(candidate)
            records = bound_waking_moments(candidate, 8, {key})
            self.assertLessEqual(len(records), 8)
            self.assertEqual(candidate, before)
            self.assertIn(key, records)
            self.assertEqual({k: records[k] for k in retained}, retained)
            self.assertEqual(len(retained_episode_keys(records, root)), 3)

    def test_full_qualified_storage_evicts_a_whole_old_episode(self):
        older, _ = route(1, 2)
        newer, _ = route(10, 2)
        key, entry = motor(20)
        records = dict(older, **newer, **{key: entry})
        result = bound_waking_moments(records, 4, {key})
        self.assertTrue(set(older).isdisjoint(result))
        self.assertTrue(set(newer).issubset(result))
        self.assertIn(key, result)

    def test_oversized_episode_does_not_erase_smaller_episode_or_freeze_admission(self):
        small, _ = route(1, 2)
        big, big_root = route(20, 6)
        result = bound_waking_moments(dict(small, **big), 4, {big_root})
        self.assertEqual(result, small)
        key, entry = motor(30)
        result = bound_waking_moments(dict(result, **{key: entry}), 4, {key})
        self.assertIn(key, result)
        self.assertTrue(set(big).isdisjoint(result))

    def test_missing_history_is_not_reconstructed(self):
        records, root = route(1, 3)
        del records["motor:2"]
        self.assertEqual(retained_episode_keys(records, root), (root,))

    def test_consecutive_intakes_remain_separate_relief_episodes(self):
        key1, a = motor(1, intake=5)
        key2, b = motor(2, intake=9, previous=key1)
        self.assertEqual(retained_episode_keys({key1: a, key2: b}, key2), (key2,))

    def test_json_roundtrip_does_not_change_retention_result(self):
        records, root = route(1, 3)
        copied = json.loads(json.dumps(records, sort_keys=True))
        self.assertEqual(retained_episode_keys(copied, root), retained_episode_keys(records, root))
        self.assertEqual(bound_waking_moments(copied, 8, set()), records)

    def test_recurring_old_root_cannot_starve_new_motor_admission(self):
        for capacity in (4, 128):
            records, tail = route(1, capacity - 1)
            records["fixture-sensory"] = {
                "count": 2, "tick": 1, "salience": 0.0, "episode_tail": tail,
            }
            for tick in range(1000, 1004):
                key, entry = motor(tick)
                candidate = dict(records, **{key: entry})
                if "fixture-sensory" in candidate:
                    candidate["fixture-sensory"] = dict(candidate["fixture-sensory"], tick=tick + 1, count=3)
                result = bound_waking_moments(candidate, capacity, {key})
                self.assertIn(key, result)
                self.assertLessEqual(len(result), capacity)
                if tick == 1000:
                    self.assertTrue(set(records).isdisjoint(result))
                records = result

    def test_moment_producer_distinguishes_creation_from_refresh(self):
        from types import SimpleNamespace
        from dsf_ai_service.guala_functional_organism import FunctionalOrganism
        org = FunctionalOrganism({
            "asleep": False, "moments": {}, "sight_figure": "fixture-figure",
            "room_now": "fixture-room",
        })
        org._ear_closed, org._own_closed = ["fixture-event"], []
        measures = {"hunger": 1.0, "taste_residue": 0.0, "skin_contact": 0.0}
        body = SimpleNamespace(held_object_id=None)
        created = org._form_moments(body, measures, 1)
        self.assertEqual(len(created), 1)
        self.assertEqual(created, set(org._state["moments"]))
        refreshed = org._form_moments(body, measures, 2)
        self.assertEqual(refreshed, set())
        self.assertEqual(org._state["moments"][next(iter(created))]["count"], 2)

    def test_sleep_moves_qualified_root_with_route_before_raw_tail(self):
        # This calls the real retention method on explicit record fixtures.
        # It does not demonstrate natural sleep onset or physical experience.
        from dsf_ai_service.guala_functional_organism import FunctionalOrganism
        records, root = route(1, 3)
        raw_key, raw_entry = motor(30)
        org = FunctionalOrganism({"moments": dict(records, **{raw_key: raw_entry}), "meanings": {}})
        org._dream_moment(40)
        self.assertEqual(org._state["meanings"], records)
        self.assertEqual(org._state["moments"], {raw_key: raw_entry})
        self.assertEqual(org._state["meanings"][root]["count"], 1)
        self.assertEqual(org._state["meanings"][root]["salience"], 0.0)


if __name__ == "__main__":
    unittest.main()
