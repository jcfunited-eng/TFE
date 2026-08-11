//! The retired hippocampal cold-custody checkpoint, kept only as persisted
//! layout.
//!
//! WHAT THIS USED TO BE, and why it is gone (owner's order, 2026-08-06/07).
//! This module owned a durable content-addressed archive of every admitted
//! reassembly: one typed episode record, its referenced snapshot bodies, one
//! posting per participating neuron lineage, and a 32-nibble persistent radix
//! path copy per participant.  MEASURED on Guala's own restored body: one
//! lesson containing four reassemblies published **3,572 new files** — about
//! 893 objects per reassembly, 33 of them per participating neuron.  Her live
//! archive reached 230,396 objects from 72 lessons against a declared bound
//! (`GUALA_MAX_COLD_REQUIRED_FILES`) of 16,384 that nothing enforced, and the
//! orphaned `.stage-` files left by interrupted publications wedged every
//! write on a hard NFS mount and took production down.
//!
//! It bought nothing.  Her memories are RETAINED FORMATIONS IN HER BODY;
//! recognition (`admit_physical_mosaic`) reads her body and never the archive.
//! This module's own doc said it "emits addresses and typed episode bytes; it
//! cannot emit recognition, recall, meaning, or cognitive capital."  Its only
//! consumer was the dynamic-formation classifier, whose eight counts measured
//! ZERO on her live body and were read by no surface anywhere.  The governing
//! doctrine (docs/GUALA_DARPA_FIRST_PROOF_BOUNDARY_2026-08-04.md §4) names
//! "database retrieval presented as recall" among the mechanisms that must not
//! be extended.
//!
//! WHAT REMAINS, and why.  A body persisted before this change carries a
//! 74-byte hippocampal checkpoint inside its cognitive image.  Removing the
//! field would make every existing body — including the one live in
//! production, of which there is no second copy of its lived experience —
//! fail to decode.  So the checkpoint is retained EXACTLY as it was laid out
//! (`GLHST01` + two optional 32-byte addresses), it round-trips byte-for-byte
//! in both directions, and it is otherwise inert: it is carried forward
//! unchanged across every transition, it is never advanced, never published,
//! and never dereferenced.  The addresses in an existing body still name real
//! objects in that body's archive directory; nothing in this crate reads them.
//!
//! THE SEVERING TEST: `HippocampalColdPort` is gone and no type in this crate
//! can create, stage, rename or delete a file in cold custody.  The capability
//! is absent, not merely unused.

pub(crate) type HippocampalAddress = [u8; 32];

const STATE_MAGIC: &[u8; 8] = b"GLHST01\0";
const ADDRESS_BYTES: usize = 32;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum HippocampalError {
    MalformedObject,
    ArithmeticOverflow,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Default)]
pub(crate) struct HippocampalCheckpoint {
    root: Option<HippocampalAddress>,
    latest_episode: Option<HippocampalAddress>,
}

/// The retired checkpoint a persisted body still carries.
///
/// Read-only in the strongest sense available: it has no constructor that
/// takes an address, so no transition can ever set one.  A body that already
/// carries addresses keeps them verbatim; a body born after this change
/// carries the default (both absent) forever.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Default)]
pub(crate) struct ResidentHippocampalIndex {
    checkpoint: HippocampalCheckpoint,
}

impl ResidentHippocampalIndex {
    pub(crate) fn encode(&self) -> Result<Vec<u8>, HippocampalError> {
        let mut output = Vec::new();
        output.extend_from_slice(STATE_MAGIC);
        push_optional_address(&mut output, self.checkpoint.root);
        push_optional_address(&mut output, self.checkpoint.latest_episode);
        Ok(output)
    }

    pub(crate) fn decode(encoded: &[u8]) -> Result<Self, HippocampalError> {
        let mut reader = Reader::new(encoded);
        if reader.take(STATE_MAGIC.len())? != STATE_MAGIC {
            return Err(HippocampalError::MalformedObject);
        }
        let checkpoint = HippocampalCheckpoint {
            root: reader.optional_address()?,
            latest_episode: reader.optional_address()?,
        };
        if !reader.finished() {
            return Err(HippocampalError::MalformedObject);
        }
        let state = Self { checkpoint };
        if state.encode()? != encoded {
            return Err(HippocampalError::MalformedObject);
        }
        Ok(state)
    }

    /// True when this body predates the archive's retirement and still names
    /// objects in its own cold-custody directory.  Nothing dereferences them;
    /// this exists so the retirement can be ASSERTED — that a body born after
    /// the change never acquires one — rather than assumed.
    #[cfg(test)]
    pub(crate) fn carries_retired_archive_reference(&self) -> bool {
        self.checkpoint.root.is_some() || self.checkpoint.latest_episode.is_some()
    }
}

fn push_optional_address(output: &mut Vec<u8>, address: Option<HippocampalAddress>) {
    output.push(u8::from(address.is_some()));
    output.extend_from_slice(&address.unwrap_or([0; 32]));
}

struct Reader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> Reader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], HippocampalError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(HippocampalError::ArithmeticOverflow)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(HippocampalError::MalformedObject)?;
        self.cursor = end;
        Ok(value)
    }

    fn u8(&mut self) -> Result<u8, HippocampalError> {
        Ok(self.take(1)?[0])
    }

    fn address(&mut self) -> Result<HippocampalAddress, HippocampalError> {
        self.take(ADDRESS_BYTES)?
            .try_into()
            .map_err(|_| HippocampalError::MalformedObject)
    }

    fn optional_address(&mut self) -> Result<Option<HippocampalAddress>, HippocampalError> {
        let present = self.u8()?;
        let address = self.address()?;
        match present {
            0 if address == [0; 32] => Ok(None),
            1 => Ok(Some(address)),
            _ => Err(HippocampalError::MalformedObject),
        }
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The exact 74 bytes a body persisted BEFORE the archive's retirement
    /// carries when it has published at least once: `GLHST01` plus a present
    /// radix root and a present latest-episode address.  Kept as a literal so
    /// the retired layout can never drift, with or without the writer.
    fn published_checkpoint_bytes() -> Vec<u8> {
        let mut encoded = Vec::new();
        encoded.extend_from_slice(STATE_MAGIC);
        encoded.push(1);
        encoded.extend_from_slice(&[0xa7; 32]);
        encoded.push(1);
        encoded.extend_from_slice(&[0x5c; 32]);
        encoded
    }

    #[test]
    fn a_body_written_before_the_retirement_still_decodes_and_re_encodes_exactly() {
        let encoded = published_checkpoint_bytes();
        assert_eq!(encoded.len(), 8 + 33 + 33);
        let decoded = ResidentHippocampalIndex::decode(&encoded).unwrap();
        assert!(decoded.carries_retired_archive_reference());
        assert_eq!(decoded.encode().unwrap(), encoded);
    }

    #[test]
    fn a_body_born_after_the_retirement_carries_the_absent_checkpoint_at_the_same_width() {
        let fresh = ResidentHippocampalIndex::default();
        let encoded = fresh.encode().unwrap();
        assert_eq!(encoded.len(), published_checkpoint_bytes().len());
        assert!(!fresh.carries_retired_archive_reference());
        assert_eq!(ResidentHippocampalIndex::decode(&encoded).unwrap(), fresh);
    }

    #[test]
    fn malformed_present_flags_trailing_bytes_and_wrong_magic_fail_closed() {
        let encoded = published_checkpoint_bytes();
        let mut wrong_magic = encoded.clone();
        wrong_magic[0] = b'X';
        assert_eq!(
            ResidentHippocampalIndex::decode(&wrong_magic),
            Err(HippocampalError::MalformedObject)
        );
        let mut trailing = encoded.clone();
        trailing.push(0);
        assert_eq!(
            ResidentHippocampalIndex::decode(&trailing),
            Err(HippocampalError::MalformedObject)
        );
        let mut truncated = encoded.clone();
        truncated.pop();
        assert_eq!(
            ResidentHippocampalIndex::decode(&truncated),
            Err(HippocampalError::MalformedObject)
        );
        let mut absent_flag_with_address = encoded.clone();
        absent_flag_with_address[8] = 0;
        assert_eq!(
            ResidentHippocampalIndex::decode(&absent_flag_with_address),
            Err(HippocampalError::MalformedObject)
        );
        let mut impossible_flag = encoded;
        impossible_flag[8] = 2;
        assert_eq!(
            ResidentHippocampalIndex::decode(&impossible_flag),
            Err(HippocampalError::MalformedObject)
        );
    }

    /// The whole point of the change: the crate cannot write cold custody.
    /// This is a compile-time fact, asserted here so the intent survives —
    /// there is no port, no publication and no staging path to call.
    #[test]
    fn the_organism_has_no_way_to_publish_a_cold_object() {
        let source = std::fs::read_to_string(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/src/hippocampal_sparse_path.rs"
        ))
        .unwrap();
        for forbidden in [
            "publish_atomic",
            "HippocampalColdPort",
            "PreparedHippocampalAdmission",
            ".stage-",
        ] {
            assert!(
                !source.contains(&format!("fn {forbidden}"))
                    && !source.contains(&format!("trait {forbidden}"))
                    && !source.contains(&format!("struct {forbidden}")),
                "the retired publication machinery reappeared: {forbidden}"
            );
        }
    }
}
