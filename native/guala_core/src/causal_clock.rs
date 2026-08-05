//! Dimensionally distinct local progress coordinates.
//!
//! These values are not an organism age, an identity, a publication
//! authority, or a shared metronome.  Each coordinate belongs to exactly one
//! physical or evidentiary process.  Causal binding between processes is made
//! by lineage, location, occurrence, and content-addressed transition
//! evidence; equal numeric coordinates carry no cross-process meaning.

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct MountedRevision(u64);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct KrimelackInterval(u64);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct MembraneInterval(u64);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct ChannelInterval(u128);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct FluidInterval(u64);

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct EpisodeHeight(u64);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalStep<T> {
    predecessor: T,
    successor: T,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum LocalClockError {
    Discontinuous,
}

macro_rules! local_coordinate {
    ($name:ident, $integer:ty) => {
        impl $name {
            pub(crate) const fn new(value: $integer) -> Self {
                Self(value)
            }

            pub(crate) const fn value(self) -> $integer {
                self.0
            }

            fn immediate_successor(self) -> Option<Self> {
                self.0.checked_add(1).map(Self)
            }
        }

        impl LocalStep<$name> {
            pub(crate) fn new(
                predecessor: $name,
                successor: $name,
            ) -> Result<Self, LocalClockError> {
                if predecessor.immediate_successor() != Some(successor) {
                    return Err(LocalClockError::Discontinuous);
                }
                Ok(Self {
                    predecessor,
                    successor,
                })
            }
        }
    };
}

local_coordinate!(MountedRevision, u64);
local_coordinate!(KrimelackInterval, u64);
local_coordinate!(MembraneInterval, u64);
local_coordinate!(ChannelInterval, u128);
local_coordinate!(FluidInterval, u64);
local_coordinate!(EpisodeHeight, u64);

impl<T: Copy> LocalStep<T> {
    pub(crate) const fn predecessor(self) -> T {
        self.predecessor
    }

    pub(crate) const fn successor(self) -> T {
        self.successor
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_domain_admits_only_its_own_immediate_local_step() {
        assert!(LocalStep::<MountedRevision>::new(
            MountedRevision::new(13),
            MountedRevision::new(14),
        )
        .is_ok());
        assert!(LocalStep::<KrimelackInterval>::new(
            KrimelackInterval::new(2),
            KrimelackInterval::new(3),
        )
        .is_ok());
        assert!(LocalStep::<MembraneInterval>::new(
            MembraneInterval::new(40),
            MembraneInterval::new(41),
        )
        .is_ok());
        assert!(LocalStep::<ChannelInterval>::new(
            ChannelInterval::new(900),
            ChannelInterval::new(901),
        )
        .is_ok());
        assert!(
            LocalStep::<FluidInterval>::new(FluidInterval::new(7), FluidInterval::new(8),).is_ok()
        );
        assert!(
            LocalStep::<EpisodeHeight>::new(EpisodeHeight::new(21), EpisodeHeight::new(22),)
                .is_ok()
        );
    }

    #[test]
    fn a_gap_or_repetition_is_not_a_local_transition() {
        assert_eq!(
            LocalStep::<MembraneInterval>::new(MembraneInterval::new(4), MembraneInterval::new(4),),
            Err(LocalClockError::Discontinuous),
        );
        assert_eq!(
            LocalStep::<FluidInterval>::new(FluidInterval::new(4), FluidInterval::new(6)),
            Err(LocalClockError::Discontinuous),
        );
    }

    #[test]
    fn coordinates_round_trip_without_cross_domain_conversion() {
        let membrane = MembraneInterval::new(13);
        let mounted = MountedRevision::new(13);
        assert_eq!(membrane.value(), 13);
        assert_eq!(mounted.value(), 13);
    }
}
