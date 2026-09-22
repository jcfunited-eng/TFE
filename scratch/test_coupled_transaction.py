"""scratch/test_coupled_transaction.py — Verify coupled world-thermal transaction mechanics,
including complete rollback of None fields and cold restart into fresh authority instances."""

from dsf_ai_service.guala_home_world import (
    home_world_authority,
    switch_tv_channel,
    nocturnal_house_tidying,
    expand_library_books,
    expand_garden_fauna_and_flora,
    expand_exterior_walkway,
    _world_thermal_transaction,
)
from dsf_ai_service.guala_caretaker_hand import present_food

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"

def test_full_coupled_continuity():
    auth = home_world_authority(identity=IDENTITY)
    
    # Baseline
    t_obs0 = auth.thermal_observation()
    assert t_obs0.world_revision == auth._state.world.revision
    print("Baseline OK: revision =", t_obs0.world_revision)
    
    # 1. TV switch
    switch_tv_channel(auth)
    t_obs1 = auth.thermal_observation()
    assert t_obs1.world_revision == auth._state.world.revision
    print("TV switch OK: revision =", t_obs1.world_revision)
    
    # 2. Nocturnal tidying
    nocturnal_house_tidying(auth)
    t_obs2 = auth.thermal_observation()
    assert t_obs2.world_revision == auth._state.world.revision
    print("Nocturnal tidying OK: revision =", t_obs2.world_revision)
    
    # 3. Library books expansion
    expand_library_books(auth)
    t_obs3 = auth.thermal_observation()
    assert t_obs3.world_revision == auth._state.world.revision
    print("Library expansion OK: revision =", t_obs3.world_revision)
    
    # 4. Garden fauna expansion
    expand_garden_fauna_and_flora(auth)
    t_obs4 = auth.thermal_observation()
    assert t_obs4.world_revision == auth._state.world.revision
    print("Garden expansion OK: revision =", t_obs4.world_revision)
    
    # 5. Exterior walkway expansion (with thermal anatomy integration)
    expand_exterior_walkway(auth)
    t_obs5 = auth.thermal_observation()
    assert t_obs5.world_revision == auth._state.world.revision
    assert "air:walkway" in auth._thermal_anatomy.node_ids
    assert len(auth._thermal_anatomy.conductive_edges("walkway")) > 0
    print("Walkway expansion OK: revision =", t_obs5.world_revision, "walkway air node present")
    
    # 6. Contact action execution after all expansions:
    res = present_food(auth, "touch-lap")
    assert res is not None
    assert res.get("touched") == "lap_hold"
    t_obs6 = auth.thermal_observation()
    assert t_obs6.world_revision == auth._state.world.revision
    print("Post-expansion contact OK: revision =", t_obs6.world_revision)

    print("--- PART 1: COUPLED EXPANSION & ACTION CONTINUITY PASSED CLEANLY! ---")


def test_lived_action_mutation_restart_lifecycle():
    """Verify exact sequence across both existing and fresh authority instances:
    1. Lived thermal action leaves transition receipt at revision R.
    2. World mutation advances to R+1, retiring the prior transition tail.
    3. Save / restore succeeds into existing authority AND into a completely fresh authority.
    4. Continued physical action executes on the restored authority instances."""
    auth = home_world_authority(identity=IDENTITY)

    mutations = [
        ("switch_tv_channel", lambda a: switch_tv_channel(a)),
        ("nocturnal_house_tidying", lambda a: nocturnal_house_tidying(a)),
        ("expand_library_books", lambda a: expand_library_books(a)),
        ("expand_garden_fauna_and_flora", lambda a: expand_garden_fauna_and_flora(a)),
        ("expand_exterior_walkway", lambda a: expand_exterior_walkway(a)),
    ]

    for name, mutate in mutations:
        # Step 1: Lived thermal action leaves a transition receipt at revision R
        res_before = present_food(auth, "touch-lap")
        assert res_before.get("touched") == "lap_hold"
        assert auth._latest_thermal_transition is not None
        r_action = auth._state.world.revision
        assert auth._latest_thermal_transition.world_revision_after == r_action
        
        # Step 2: Mutation advances world revision to R+1 and retires prior transition tail
        mutate(auth)
        assert auth._latest_thermal_transition is None
        r_mut = auth._state.world.revision
        assert r_mut > r_action
        assert auth._thermal_world_revision == r_mut
        
        # Step 3A: Save and restore into existing authority instance
        enc = auth.encoded_snapshot()
        auth.restore_encoded(enc)
        assert auth._state.world.revision == r_mut
        assert auth._thermal_world_revision == r_mut
        assert auth._latest_thermal_transition is None
        
        # Step 3B: Cold restart into a completely fresh authority instance
        has_walkway = "walkway" in {r.region_id for r in auth._state.world.regions}
        fresh_auth = home_world_authority(identity=IDENTITY, encoded_world=enc, expand_walkway=has_walkway)
        assert fresh_auth._state.world.revision == r_mut
        assert fresh_auth._thermal_world_revision == r_mut
        assert fresh_auth._latest_thermal_transition is None

        # Step 4: Continued physical action executes cleanly on both
        res_after = present_food(auth, "touch-lap")
        assert res_after.get("touched") == "lap_hold"
        assert auth._latest_thermal_transition is not None
        assert auth._latest_thermal_transition.world_revision_after == auth._state.world.revision

        res_fresh = present_food(fresh_auth, "touch-lap")
        assert res_fresh.get("touched") == "lap_hold"
        assert fresh_auth._latest_thermal_transition is not None
        assert fresh_auth._latest_thermal_transition.world_revision_after == fresh_auth._state.world.revision

        print(f"Cold restart lifecycle for {name}: PASSED! (rev {r_action} -> {r_mut} -> {auth._state.world.revision})")

    print("--- PART 2: ALL 5 RESTART LIFECYCLES (EXISTING & FRESH) PASSED CLEANLY! ---")


def test_exact_none_rollback():
    """Verify complete rollback: fields that were originally None strictly return to None on exception."""
    auth = home_world_authority(identity=IDENTITY)
    auth._latest_thermal_transition = None
    auth._pending_thermal = None
    auth._committed_thermal_tail = None

    try:
        with _world_thermal_transaction(auth):
            auth._latest_thermal_transition = "dirty_transition"
            auth._pending_thermal = "dirty_pending"
            auth._committed_thermal_tail = "dirty_tail"
            raise RuntimeError("simulated mutation crash")
    except RuntimeError:
        pass

    assert auth._latest_thermal_transition is None, "Failed to restore None for latest_thermal_transition"
    assert auth._pending_thermal is None, "Failed to restore None for pending_thermal"
    assert auth._committed_thermal_tail is None, "Failed to restore None for committed_thermal_tail"
    print("--- PART 3: COMPLETE NONE-FIELD ROLLBACK PASSED CLEANLY! ---")


if __name__ == "__main__":
    test_full_coupled_continuity()
    test_lived_action_mutation_restart_lifecycle()
    test_exact_none_rollback()
