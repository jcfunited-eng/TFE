//! Shared immutable evidence addressing and bounded delta construction.
//!
//! A content address is an integrity address only. It grants no causal,
//! cognitive, recall, or credit authority. Typed consumers remain responsible
//! for interpreting complete bodies and deciding whether they are admissible.

use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fmt;
use std::sync::Arc;

const ROOT_DOMAIN: &[u8] = b"GUALA_IMMUTABLE_EVIDENCE_DELTA_ROOT_V1";
const ROOT_COUNT_BYTES: usize = std::mem::size_of::<u64>();
const ROOT_ENTRY_BYTES: usize = 32 + std::mem::size_of::<u64>();

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct ContentAddress(pub [u8; 32]);

impl ContentAddress {
    pub fn of(bytes: &[u8]) -> Self {
        Self(Sha256::digest(bytes).into())
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AddressedImmutableObject {
    pub address: ContentAddress,
    pub bytes: Arc<[u8]>,
}

impl AddressedImmutableObject {
    pub fn from_body(bytes: Vec<u8>) -> Self {
        let address = ContentAddress::of(&bytes);
        Self {
            address,
            bytes: Arc::from(bytes),
        }
    }
}

pub trait ImmutableObjectResolver {
    fn resolve(&self, address: ContentAddress) -> Option<Arc<[u8]>>;
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DeltaEnvelope {
    pub max_objects: usize,
    pub max_object_bytes: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DeltaAccounting {
    pub object_count: usize,
    pub total_object_bytes: usize,
    pub root_input_bytes: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImmutableDelta {
    pub objects: Vec<AddressedImmutableObject>,
    pub root: ContentAddress,
    pub accounting: DeltaAccounting,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Error {
    EmptyEnvelope,
    ArithmeticOverflow,
    ObjectBudgetExceeded {
        required: usize,
        admitted: usize,
    },
    ByteBudgetExceeded {
        required: usize,
        admitted: usize,
    },
    AddressBodyMismatch {
        declared: ContentAddress,
        derived: ContentAddress,
    },
    AddressCollision(ContentAddress),
    NonCanonicalReplay,
    ReplayRootMismatch {
        expected: ContentAddress,
        actual: ContentAddress,
    },
}

impl fmt::Display for Error {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(output, "{self:?}")
    }
}

impl std::error::Error for Error {}

pub struct BoundedImmutableDeltaBuilder {
    objects: BTreeMap<ContentAddress, Arc<[u8]>>,
    total_object_bytes: usize,
    envelope: DeltaEnvelope,
}

impl BoundedImmutableDeltaBuilder {
    pub fn new(envelope: DeltaEnvelope) -> Result<Self, Error> {
        if envelope.max_objects == 0 || envelope.max_object_bytes == 0 {
            return Err(Error::EmptyEnvelope);
        }
        Ok(Self {
            objects: BTreeMap::new(),
            total_object_bytes: 0,
            envelope,
        })
    }

    pub fn add(&mut self, bytes: Vec<u8>) -> Result<ContentAddress, Error> {
        self.add_addressed(AddressedImmutableObject::from_body(bytes))
    }

    pub fn add_addressed(
        &mut self,
        object: AddressedImmutableObject,
    ) -> Result<ContentAddress, Error> {
        if let Some(existing) = self.objects.get(&object.address) {
            if existing.as_ref() == object.bytes.as_ref() {
                return Ok(object.address);
            }
            return Err(Error::AddressCollision(object.address));
        }

        let derived = ContentAddress::of(&object.bytes);
        if derived != object.address {
            return Err(Error::AddressBodyMismatch {
                declared: object.address,
                derived,
            });
        }

        let required_objects = self
            .objects
            .len()
            .checked_add(1)
            .ok_or(Error::ArithmeticOverflow)?;
        if required_objects > self.envelope.max_objects {
            return Err(Error::ObjectBudgetExceeded {
                required: required_objects,
                admitted: self.envelope.max_objects,
            });
        }

        let required_bytes = self
            .total_object_bytes
            .checked_add(object.bytes.len())
            .ok_or(Error::ArithmeticOverflow)?;
        if required_bytes > self.envelope.max_object_bytes {
            return Err(Error::ByteBudgetExceeded {
                required: required_bytes,
                admitted: self.envelope.max_object_bytes,
            });
        }

        self.total_object_bytes = required_bytes;
        self.objects.insert(object.address, object.bytes);
        Ok(object.address)
    }

    pub fn objects(&self) -> &BTreeMap<ContentAddress, Arc<[u8]>> {
        &self.objects
    }

    pub fn object_count(&self) -> usize {
        self.objects.len()
    }

    pub fn total_object_bytes(&self) -> usize {
        self.total_object_bytes
    }

    pub fn finish(self) -> Result<ImmutableDelta, Error> {
        let accounting = accounting(self.objects.len(), self.total_object_bytes)?;
        let root = root_of(&self.objects, accounting)?;
        let objects = self
            .objects
            .into_iter()
            .map(|(address, bytes)| AddressedImmutableObject { address, bytes })
            .collect();
        Ok(ImmutableDelta {
            objects,
            root,
            accounting,
        })
    }

    pub fn replay(
        objects: &[AddressedImmutableObject],
        envelope: DeltaEnvelope,
        expected_root: ContentAddress,
    ) -> Result<ImmutableDelta, Error> {
        if objects
            .windows(2)
            .any(|pair| pair[0].address >= pair[1].address)
        {
            return Err(Error::NonCanonicalReplay);
        }
        let mut builder = Self::new(envelope)?;
        for object in objects {
            builder.add_addressed(object.clone())?;
        }
        let replayed = builder.finish()?;
        if replayed.root != expected_root {
            return Err(Error::ReplayRootMismatch {
                expected: expected_root,
                actual: replayed.root,
            });
        }
        Ok(replayed)
    }
}

fn accounting(object_count: usize, total_object_bytes: usize) -> Result<DeltaAccounting, Error> {
    let root_input_bytes = ROOT_DOMAIN
        .len()
        .checked_add(ROOT_COUNT_BYTES)
        .and_then(|bytes| {
            object_count
                .checked_mul(ROOT_ENTRY_BYTES)
                .and_then(|entries| bytes.checked_add(entries))
        })
        .ok_or(Error::ArithmeticOverflow)?;
    Ok(DeltaAccounting {
        object_count,
        total_object_bytes,
        root_input_bytes,
    })
}

fn root_of(
    objects: &BTreeMap<ContentAddress, Arc<[u8]>>,
    accounting: DeltaAccounting,
) -> Result<ContentAddress, Error> {
    let object_count =
        u64::try_from(accounting.object_count).map_err(|_| Error::ArithmeticOverflow)?;
    let mut digest = Sha256::new();
    digest.update(ROOT_DOMAIN);
    digest.update(object_count.to_le_bytes());
    for (address, bytes) in objects {
        let body_len = u64::try_from(bytes.len()).map_err(|_| Error::ArithmeticOverflow)?;
        digest.update(address.0);
        digest.update(body_len.to_le_bytes());
    }
    Ok(ContentAddress(digest.finalize().into()))
}
