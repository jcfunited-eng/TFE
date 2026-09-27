"""Geometric falsifiers; fixtures describe geometry, not learned experience."""
from types import SimpleNamespace as S
from dsf_ai_service.guala_functional_organism import _door_motor_commands, move_commands_toward
from dsf_ai_service.substrate.embodiment_world import PositionMM, PoseMM, RoomBoundsMM


def scene(x=8380,y=8024,axis='x',radius=250,obstacles=((8573,7614,150),)):
    def pos(x,y): return PositionMM(x,y,0) if axis=='x' else PositionMM(y,x,0)
    body=S(body_id='guala-body-1',pose=PoseMM(pos(x,y),0),radius_mm=radius,held_object_id=None)
    portal=S(portal_id='door',axis=axis,plane_mm=9000,aperture_min_mm=6900,aperture_max_mm=8300,region_ids=('from','to'))
    bounds=RoomBoundsMM(pos(5600,5000),PositionMM(9000,10000,2600) if axis=='x' else PositionMM(10000,9000,2600))
    objects=tuple(S(object_id='obstacle-'+str(i),position=pos(a,b),radius_mm=r) for i,(a,b,r) in enumerate(obstacles))
    snap=S(self_body_id=body.body_id,bodies=(body,),objects=objects,regions=(S(region_id='from',bounds=bounds),),portals=(portal,))
    return snap,portal,body


def test_occupied_centre_has_no_invented_sidestep():
    snap,_,_=scene()
    assert move_commands_toward(snap,PositionMM(8400,7600,0),0)==()


def test_free_aperture_reached_without_two_point_reversal():
    for axis in ('x','y'):
        snap,p,b=scene(axis=axis)
        first=_door_motor_commands(snap,p,'from')
        assert first
        expected = PositionMM(8400,8024,0) if axis=='x' else PositionMM(8024,8400,0)
        assert first[0].target_pose.position == expected
        b.pose=first[0].target_pose
        crossing=_door_motor_commands(snap,p,'from')
        assert len(crossing)==1
        destination=crossing[0].target_pose.position
        assert (destination.x if axis=='x' else destination.y)==9600
        assert (destination.y if axis=='x' else destination.x)==8024


def test_fully_blocked_or_narrow_aperture_abstains():
    snap,p,_=scene(obstacles=((9000,7600,700),))
    assert _door_motor_commands(snap,p,'from')==()
    snap,p,_=scene(radius=701,obstacles=())
    assert _door_motor_commands(snap,p,'from')==()


def test_contact_tangency_matches_world_strict_collision():
    snap,p,b=scene(x=8400,y=8014)
    commands=_door_motor_commands(snap,p,'from')
    assert len(commands)==1
    assert commands[0].target_pose.position==PositionMM(9600,8014,0)
