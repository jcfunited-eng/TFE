//! Canonical typed hippocampal episode custody and sparse paged navigation.
//!
//! The index is an immutable navigation surface only.  It retains the exact
//! caller-admitted episode body, one posting per participating mounted neuron
//! lineage, and a fixed 32-nibble persistent radix root.  It emits addresses
//! and typed episode bytes; it cannot emit recognition, recall, meaning, or
//! cognitive capital.

use crate::sha256::sha256;
use std::collections::BTreeMap;

pub(crate) type NeuronLineage = [u8; 16];
pub(crate) type HippocampalAddress = [u8; 32];

const EPISODE_MAGIC: &[u8; 8] = b"GLHEP02\0";
const EPISODE_V3_MAGIC: &[u8; 8] = b"GLHEP03\0";
const POSTING_MAGIC: &[u8; 8] = b"GLHPS01\0";
const RADIX_MAGIC: &[u8; 8] = b"GLHRN01\0";
const STATE_MAGIC: &[u8; 8] = b"GLHST01\0";
// Structural (layout-only) magics of the evidence bodies this custody splits
// into content-addressed snapshot objects. The bytes are owned and validated
// by the resident cognitive boundary; custody never interprets them beyond
// the framing needed to store each retained snapshot exactly once.
const EVIDENCE_EXPERIENCE_V2_MAGIC: &[u8; 8] = b"GLEXP02\0";
const EVIDENCE_RECURRENT_MAGIC: &[u8; 8] = b"GLHRE01\0";
const RADIX_DEPTH: usize = 32;
const ADDRESS_BYTES: usize = 32;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum HippocampalError {
    EmptyParticipants,
    DuplicateOrUnorderedParticipants,
    ZeroGeneration,
    NonAdvancingGeneration,
    EmptyTypedBody,
    EmptyEnvelope,
    ObjectCountBudget { required: usize, available: usize },
    ObjectByteBudget { required: usize, available: usize },
    TraversalCountBudget,
    TraversalByteBudget,
    MissingObject(HippocampalAddress),
    AddressMismatch(HippocampalAddress),
    MalformedObject,
    WrongObjectType,
    LineageMismatch,
    PostingOrderViolation,
    ColdCustodyUnavailable(String),
    ArithmeticOverflow,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct EpisodeParticipant {
    pub(crate) lineage: NeuronLineage,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TypedEpisodeAdmission {
    pub(crate) predecessor_generation: u64,
    pub(crate) episode_generation: u64,
    pub(crate) source_authority: [u8; 32],
    pub(crate) source_body: Box<[u8]>,
    pub(crate) source_port_count: usize,
    pub(crate) source_sample_count: usize,
    pub(crate) source_occurrence_count: usize,
    pub(crate) source_occurrence_frame_count: usize,
    pub(crate) source_occurrence_index: usize,
    pub(crate) physical_mosaic: Box<[u8]>,
    pub(crate) original_transition_evidence: Box<[u8]>,
    pub(crate) recurrent_transition_evidence: Box<[u8]>,
    pub(crate) participants: Box<[EpisodeParticipant]>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct HippocampalAdmissionEnvelope {
    pub(crate) max_objects: usize,
    pub(crate) max_object_bytes: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct HippocampalTraversalEnvelope {
    pub(crate) max_postings: usize,
    pub(crate) max_decoded_bytes: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Default)]
pub(crate) struct HippocampalCheckpoint {
    root: Option<HippocampalAddress>,
    latest_episode: Option<HippocampalAddress>,
}

impl HippocampalCheckpoint {
    pub(crate) fn root(&self) -> Option<HippocampalAddress> {
        self.root
    }

    pub(crate) fn latest_episode(&self) -> Option<HippocampalAddress> {
        self.latest_episode
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Default)]
pub(crate) struct ResidentHippocampalIndex {
    checkpoint: HippocampalCheckpoint,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HippocampalColdObject {
    address: HippocampalAddress,
    body: Box<[u8]>,
}

impl HippocampalColdObject {
    pub(crate) fn from_parts(address: HippocampalAddress, body: Box<[u8]>) -> Self {
        Self { address, body }
    }

    pub fn address(&self) -> HippocampalAddress {
        self.address
    }

    pub fn body(&self) -> &[u8] {
        &self.body
    }
}

/// External immutable custody required by the native resident runtime.
/// `publish_atomic` must either retain the complete supplied delta or retain
/// none of it. The organism never supplies a default production authority.
pub trait HippocampalColdPort {
    fn read_object(&self, address: HippocampalAddress) -> Result<Option<Box<[u8]>>, String>;

    fn publish_atomic(&mut self, objects: &[HippocampalColdObject]) -> Result<(), String>;
}

/// In-memory cold custody exists only as a deterministic test adapter.
#[cfg(test)]
#[derive(Clone, Debug, Eq, PartialEq, Default)]
pub(crate) struct HippocampalColdStore {
    objects: BTreeMap<HippocampalAddress, Box<[u8]>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PreparedHippocampalAdmission {
    predecessor: HippocampalCheckpoint,
    successor: HippocampalCheckpoint,
    objects: BTreeMap<HippocampalAddress, Box<[u8]>>,
    episode_address: HippocampalAddress,
    posting_count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PublishedHippocampalAdmission {
    predecessor: HippocampalCheckpoint,
    successor: HippocampalCheckpoint,
    episode_address: HippocampalAddress,
}

impl PreparedHippocampalAdmission {
    pub(crate) fn episode_address(&self) -> HippocampalAddress {
        self.episode_address
    }

    pub(crate) fn posting_count(&self) -> usize {
        self.posting_count
    }

    pub(crate) fn prepared_object_count(&self) -> usize {
        self.objects.len()
    }

    pub(crate) fn successor(&self) -> HippocampalCheckpoint {
        self.successor
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct NavigatedPosting {
    pub(crate) episode_generation: u64,
    pub(crate) episode_address: HippocampalAddress,
    pub(crate) episode_bytes: Box<[u8]>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct HippocampalTraversalPage {
    pub(crate) postings: Vec<NavigatedPosting>,
    pub(crate) continuation: Option<HippocampalAddress>,
    pub(crate) decoded_bytes: usize,
}

/// Retained only as an unconstructable compile-time boundary for the separate
/// pre-D3 capital observer.  The arbitrary caller-selected navigator admission
/// function has been removed; canonical episode postings above are the only
/// constructable hippocampal state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct HippocampalSparsePath {
    navigator_neurons: Box<[usize]>,
    formation_members: Box<[usize]>,
    physical_contact_indices: Box<[usize]>,
}

impl HippocampalSparsePath {
    pub(crate) fn navigator_neurons(&self) -> &[usize] {
        &self.navigator_neurons
    }

    pub(crate) fn formation_members(&self) -> &[usize] {
        &self.formation_members
    }

    pub(crate) fn physical_contact_indices(&self) -> &[usize] {
        &self.physical_contact_indices
    }
}

impl ResidentHippocampalIndex {
    pub(crate) fn checkpoint(&self) -> HippocampalCheckpoint {
        self.checkpoint
    }

    pub(crate) fn from_checkpoint(checkpoint: HippocampalCheckpoint) -> Self {
        Self { checkpoint }
    }

    pub(crate) fn prepare(
        &self,
        cold: &dyn HippocampalColdPort,
        episode: &TypedEpisodeAdmission,
        envelope: HippocampalAdmissionEnvelope,
    ) -> Result<PreparedHippocampalAdmission, HippocampalError> {
        if envelope.max_objects == 0 || envelope.max_object_bytes == 0 {
            return Err(HippocampalError::EmptyEnvelope);
        }
        validate_episode(episode)?;
        let mut prepared = BTreeMap::new();
        let (episode_bytes, referenced_bodies) = encode_episode_record(episode)?;
        for body in referenced_bodies {
            add_object(&mut prepared, body);
        }
        let episode_address = add_object(&mut prepared, episode_bytes);
        let mut root = self.checkpoint.root;

        for participant in episode.participants.iter() {
            let prior = posting_head_from(cold, root, participant.lineage, &prepared)?;
            if let Some(prior_address) = prior {
                let prior_bytes = resolve(cold, &prepared, prior_address)?;
                let prior_posting = decode_posting(&prior_bytes)?;
                if prior_posting.lineage != participant.lineage {
                    return Err(HippocampalError::LineageMismatch);
                }
                if prior_posting.episode_generation >= episode.episode_generation {
                    return Err(HippocampalError::NonAdvancingGeneration);
                }
            }
            let posting = PostingSegment {
                lineage: participant.lineage,
                episode_generation: episode.episode_generation,
                episode_address,
                prior,
            };
            let posting_address = add_object(&mut prepared, encode_posting(posting));
            root = Some(path_copy(
                cold,
                root,
                participant.lineage,
                posting_address,
                &mut prepared,
            )?);
        }

        let total_bytes = prepared.values().try_fold(0usize, |total, body| {
            total
                .checked_add(body.len())
                .ok_or(HippocampalError::ArithmeticOverflow)
        })?;
        if prepared.len() > envelope.max_objects {
            return Err(HippocampalError::ObjectCountBudget {
                required: prepared.len(),
                available: envelope.max_objects,
            });
        }
        if total_bytes > envelope.max_object_bytes {
            return Err(HippocampalError::ObjectByteBudget {
                required: total_bytes,
                available: envelope.max_object_bytes,
            });
        }
        Ok(PreparedHippocampalAdmission {
            predecessor: self.checkpoint,
            successor: HippocampalCheckpoint {
                root,
                latest_episode: Some(episode_address),
            },
            objects: prepared,
            episode_address,
            posting_count: episode.participants.len(),
        })
    }

    pub(crate) fn adopt(
        &mut self,
        published: PublishedHippocampalAdmission,
    ) -> Result<HippocampalAddress, HippocampalError> {
        if self.checkpoint != published.predecessor {
            return Err(HippocampalError::NonAdvancingGeneration);
        }
        self.checkpoint = published.successor;
        Ok(published.episode_address)
    }

    pub(crate) fn navigate(
        &self,
        cold: &dyn HippocampalColdPort,
        lineage: NeuronLineage,
        continuation: Option<HippocampalAddress>,
        envelope: HippocampalTraversalEnvelope,
    ) -> Result<HippocampalTraversalPage, HippocampalError> {
        if envelope.max_postings == 0 {
            return Err(HippocampalError::TraversalCountBudget);
        }
        if envelope.max_decoded_bytes == 0 {
            return Err(HippocampalError::TraversalByteBudget);
        }
        let mut next = match continuation {
            Some(address) => Some(address),
            None => posting_head_from(cold, self.checkpoint.root, lineage, &BTreeMap::new())?,
        };
        let mut postings = Vec::new();
        let mut decoded_bytes = 0usize;
        while let Some(address) = next {
            if postings.len() == envelope.max_postings {
                break;
            }
            let posting_bytes = read_exact(cold, address)?;
            let posting = decode_posting(&posting_bytes)?;
            if posting.lineage != lineage {
                return Err(HippocampalError::LineageMismatch);
            }
            let episode_bytes = read_exact(cold, posting.episode_address)?;
            let (episode_generation, participants) = decode_episode_summary(&episode_bytes)?;
            if episode_generation != posting.episode_generation
                || participants
                    .binary_search_by_key(&lineage, |participant| participant.lineage)
                    .is_err()
            {
                return Err(HippocampalError::LineageMismatch);
            }
            let required = decoded_bytes
                .checked_add(posting_bytes.len())
                .and_then(|value| value.checked_add(episode_bytes.len()))
                .ok_or(HippocampalError::ArithmeticOverflow)?;
            if required > envelope.max_decoded_bytes {
                if postings.is_empty() {
                    return Err(HippocampalError::TraversalByteBudget);
                }
                break;
            }
            decoded_bytes = required;
            postings.push(NavigatedPosting {
                episode_generation: posting.episode_generation,
                episode_address: posting.episode_address,
                episode_bytes: episode_bytes.clone(),
            });
            next = posting.prior;
        }
        Ok(HippocampalTraversalPage {
            postings,
            continuation: next,
            decoded_bytes,
        })
    }

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
}

pub(crate) fn publish_hippocampal_admission(
    cold: &mut dyn HippocampalColdPort,
    prepared: &PreparedHippocampalAdmission,
) -> Result<PublishedHippocampalAdmission, HippocampalError> {
    publish_hippocampal_admission_checked(cold, prepared, |_| Ok(()))
        .map(|(published, _, _, _)| published)
}

fn publish_hippocampal_admission_checked<F>(
    cold: &mut dyn HippocampalColdPort,
    prepared: &PreparedHippocampalAdmission,
    mut before_object_or_commit: F,
) -> Result<(PublishedHippocampalAdmission, usize, usize, usize), HippocampalError>
where
    F: FnMut(usize) -> Result<(), HippocampalError>,
{
    let mut delta = Vec::new();
    let mut inspected_objects = 0usize;
    let mut delta_bytes = 0usize;
    for (address, bytes) in &prepared.objects {
        before_object_or_commit(inspected_objects)?;
        if sha256(bytes) != *address {
            return Err(HippocampalError::AddressMismatch(*address));
        }
        if let Some(existing) = read_optional(cold, *address)? {
            if existing.as_ref() != bytes.as_ref() {
                return Err(HippocampalError::AddressMismatch(*address));
            }
        } else {
            delta_bytes = delta_bytes
                .checked_add(bytes.len())
                .ok_or(HippocampalError::ArithmeticOverflow)?;
            delta.push(HippocampalColdObject {
                address: *address,
                body: bytes.clone(),
            });
        }
        inspected_objects = inspected_objects
            .checked_add(1)
            .ok_or(HippocampalError::ArithmeticOverflow)?;
    }
    before_object_or_commit(inspected_objects)?;

    let delta_objects = delta.len();
    cold.publish_atomic(&delta)
        .map_err(HippocampalError::ColdCustodyUnavailable)?;
    for object in &delta {
        if read_exact(cold, object.address)?.as_ref() != object.body.as_ref() {
            return Err(HippocampalError::AddressMismatch(object.address));
        }
    }
    Ok((
        PublishedHippocampalAdmission {
            predecessor: prepared.predecessor,
            successor: prepared.successor,
            episode_address: prepared.episode_address,
        },
        inspected_objects,
        delta_objects,
        delta_bytes,
    ))
}

pub(crate) fn resolve_hippocampal_episode(
    cold: &dyn HippocampalColdPort,
    address: HippocampalAddress,
) -> Result<TypedEpisodeAdmission, HippocampalError> {
    let bytes = read_exact(cold, address)?;
    decode_episode(cold, &bytes)
}

pub(crate) fn validate_hippocampal_checkpoint(
    cold: &dyn HippocampalColdPort,
    checkpoint: HippocampalCheckpoint,
) -> Result<(), HippocampalError> {
    if let Some(root) = checkpoint.root {
        let bytes = read_exact(cold, root)?;
        let node = decode_radix(&bytes)?;
        if node.depth != 0 {
            return Err(HippocampalError::MalformedObject);
        }
    }
    if let Some(episode) = checkpoint.latest_episode {
        let bytes = read_exact(cold, episode)?;
        decode_episode(cold, &bytes)?;
    }
    Ok(())
}

fn posting_head_from(
    cold: &dyn HippocampalColdPort,
    root: Option<HippocampalAddress>,
    lineage: NeuronLineage,
    prepared: &BTreeMap<HippocampalAddress, Box<[u8]>>,
) -> Result<Option<HippocampalAddress>, HippocampalError> {
    let Some(mut address) = root else {
        return Ok(None);
    };
    for depth in 0..RADIX_DEPTH {
        let bytes = resolve(cold, prepared, address)?;
        let node = decode_radix(&bytes)?;
        if usize::from(node.depth) != depth {
            return Err(HippocampalError::MalformedObject);
        }
        let next = node.children[nibble(lineage, depth)];
        if depth + 1 == RADIX_DEPTH {
            return Ok(next);
        }
        let Some(next_address) = next else {
            return Ok(None);
        };
        address = next_address;
    }
    Err(HippocampalError::MalformedObject)
}

fn path_copy(
    cold: &dyn HippocampalColdPort,
    root: Option<HippocampalAddress>,
    lineage: NeuronLineage,
    posting: HippocampalAddress,
    prepared: &mut BTreeMap<HippocampalAddress, Box<[u8]>>,
) -> Result<HippocampalAddress, HippocampalError> {
    let mut old_nodes = Vec::with_capacity(RADIX_DEPTH);
    let mut next = root;
    for depth in 0..RADIX_DEPTH {
        let node = if let Some(address) = next {
            let bytes = resolve(cold, prepared, address)?;
            let decoded = decode_radix(&bytes)?;
            if usize::from(decoded.depth) != depth {
                return Err(HippocampalError::MalformedObject);
            }
            decoded
        } else {
            RadixNode::empty(depth)?
        };
        next = if depth + 1 < RADIX_DEPTH {
            node.children[nibble(lineage, depth)]
        } else {
            None
        };
        old_nodes.push(node);
    }
    let mut child = posting;
    for depth in (0..RADIX_DEPTH).rev() {
        let mut node = old_nodes.pop().ok_or(HippocampalError::MalformedObject)?;
        node.children[nibble(lineage, depth)] = Some(child);
        child = add_object(prepared, encode_radix(&node));
    }
    Ok(child)
}

#[cfg(test)]
impl HippocampalColdStore {
    pub(crate) fn object_count(&self) -> usize {
        self.objects.len()
    }

    pub(crate) fn resolve_episode(
        &self,
        address: HippocampalAddress,
    ) -> Result<TypedEpisodeAdmission, HippocampalError> {
        resolve_hippocampal_episode(self, address)
    }

    pub(crate) fn publish(
        &mut self,
        prepared: &PreparedHippocampalAdmission,
    ) -> Result<PublishedHippocampalAdmission, HippocampalError> {
        publish_hippocampal_admission(self, prepared)
    }

    fn publish_checked<F>(
        &mut self,
        prepared: &PreparedHippocampalAdmission,
        before_object_or_commit: F,
    ) -> Result<(PublishedHippocampalAdmission, usize, usize, usize), HippocampalError>
    where
        F: FnMut(usize) -> Result<(), HippocampalError>,
    {
        publish_hippocampal_admission_checked(self, prepared, before_object_or_commit)
    }

    pub(crate) fn validate_checkpoint(
        &self,
        checkpoint: HippocampalCheckpoint,
    ) -> Result<(), HippocampalError> {
        validate_hippocampal_checkpoint(self, checkpoint)
    }

    fn posting_head_from(
        &self,
        root: Option<HippocampalAddress>,
        lineage: NeuronLineage,
        prepared: &BTreeMap<HippocampalAddress, Box<[u8]>>,
    ) -> Result<Option<HippocampalAddress>, HippocampalError> {
        posting_head_from(self, root, lineage, prepared)
    }
}

#[cfg(test)]
impl HippocampalColdPort for HippocampalColdStore {
    fn read_object(&self, address: HippocampalAddress) -> Result<Option<Box<[u8]>>, String> {
        Ok(self.objects.get(&address).cloned())
    }

    fn publish_atomic(&mut self, objects: &[HippocampalColdObject]) -> Result<(), String> {
        for object in objects {
            if let Some(existing) = self.objects.get(&object.address) {
                if existing.as_ref() != object.body.as_ref() {
                    return Err("immutable cold object collision".to_owned());
                }
            }
        }
        for object in objects {
            self.objects
                .entry(object.address)
                .or_insert_with(|| object.body.clone());
        }
        Ok(())
    }
}

#[derive(Clone, Copy)]
struct PostingSegment {
    lineage: NeuronLineage,
    episode_generation: u64,
    episode_address: HippocampalAddress,
    prior: Option<HippocampalAddress>,
}

#[derive(Clone)]
struct RadixNode {
    depth: u8,
    children: [Option<HippocampalAddress>; 16],
}

impl RadixNode {
    fn empty(depth: usize) -> Result<Self, HippocampalError> {
        Ok(Self {
            depth: u8::try_from(depth).map_err(|_| HippocampalError::ArithmeticOverflow)?,
            children: [None; 16],
        })
    }
}

fn validate_episode(episode: &TypedEpisodeAdmission) -> Result<(), HippocampalError> {
    if episode.episode_generation == 0 {
        return Err(HippocampalError::ZeroGeneration);
    }
    if episode.predecessor_generation >= episode.episode_generation {
        return Err(HippocampalError::NonAdvancingGeneration);
    }
    if episode.source_body.is_empty()
        || episode.physical_mosaic.is_empty()
        || episode.original_transition_evidence.is_empty()
        || episode.recurrent_transition_evidence.is_empty()
    {
        return Err(HippocampalError::EmptyTypedBody);
    }
    if episode.source_port_count == 0
        || episode.source_sample_count == 0
        || episode.source_occurrence_count == 0
        || episode.source_occurrence_frame_count == 0
        || episode.source_occurrence_index >= episode.source_occurrence_count
    {
        return Err(HippocampalError::MalformedObject);
    }
    if sha256(&episode.source_body) != episode.source_authority {
        return Err(HippocampalError::AddressMismatch(episode.source_authority));
    }
    if episode.participants.is_empty() {
        return Err(HippocampalError::EmptyParticipants);
    }
    if episode
        .participants
        .windows(2)
        .any(|pair| pair[0].lineage >= pair[1].lineage)
    {
        return Err(HippocampalError::DuplicateOrUnorderedParticipants);
    }
    Ok(())
}

/// Structural decomposition of one original-transition evidence body
/// (`GLEXP02`, self-contained form) into its retained cohort snapshots. Bodies
/// that do not carry that exact layout stay whole; both directions are exact
/// byte-level inverses so the reconstructed body is identical.
enum OriginalEvidenceSplit<'a> {
    Whole(&'a [u8]),
    Split {
        pre: &'a [u8],
        post: Option<&'a [u8]>,
        tail: &'a [u8],
    },
}

fn split_original_evidence(body: &[u8]) -> OriginalEvidenceSplit<'_> {
    fn parse(body: &[u8]) -> Result<OriginalEvidenceSplit<'_>, HippocampalError> {
        let mut reader = Reader::new(body);
        if reader.take(EVIDENCE_EXPERIENCE_V2_MAGIC.len())? != EVIDENCE_EXPERIENCE_V2_MAGIC
            || reader.u8()? != 0
        {
            return Err(HippocampalError::MalformedObject);
        }
        let pre = reader.bytes()?;
        let post = match reader.u8()? {
            0 => None,
            1 => Some(reader.bytes()?),
            _ => return Err(HippocampalError::MalformedObject),
        };
        let tail = reader.take(body.len() - reader.cursor)?;
        if pre.is_empty() || post.is_some_and(<[u8]>::is_empty) {
            return Err(HippocampalError::MalformedObject);
        }
        Ok(OriginalEvidenceSplit::Split { pre, post, tail })
    }
    parse(body).unwrap_or(OriginalEvidenceSplit::Whole(body))
}

fn assemble_original_evidence(
    pre: &[u8],
    post: Option<&[u8]>,
    tail: &[u8],
) -> Result<Vec<u8>, HippocampalError> {
    let mut body = Vec::new();
    body.extend_from_slice(EVIDENCE_EXPERIENCE_V2_MAGIC);
    body.push(0);
    push_bytes(&mut body, pre)?;
    match post {
        None => body.push(0),
        Some(post) => {
            body.push(1);
            push_bytes(&mut body, post)?;
        }
    }
    body.extend_from_slice(tail);
    Ok(body)
}

/// Structural decomposition of one recurrent-transition evidence body
/// (`GLHRE01`) into its learned and recurrent cohort snapshots.
enum RecurrentEvidenceSplit<'a> {
    Whole(&'a [u8]),
    Split {
        meta: &'a [u8],
        learned: &'a [u8],
        recurrent: &'a [u8],
    },
}

fn split_recurrent_evidence(body: &[u8]) -> RecurrentEvidenceSplit<'_> {
    fn parse(body: &[u8]) -> Result<RecurrentEvidenceSplit<'_>, HippocampalError> {
        let mut reader = Reader::new(body);
        if reader.take(EVIDENCE_RECURRENT_MAGIC.len())? != EVIDENCE_RECURRENT_MAGIC {
            return Err(HippocampalError::MalformedObject);
        }
        let meta = reader.bytes()?;
        let learned = reader.bytes()?;
        let recurrent = reader.bytes()?;
        if !reader.finished() || learned.is_empty() || recurrent.is_empty() {
            return Err(HippocampalError::MalformedObject);
        }
        Ok(RecurrentEvidenceSplit::Split {
            meta,
            learned,
            recurrent,
        })
    }
    parse(body).unwrap_or(RecurrentEvidenceSplit::Whole(body))
}

fn assemble_recurrent_evidence(
    meta: &[u8],
    learned: &[u8],
    recurrent: &[u8],
) -> Result<Vec<u8>, HippocampalError> {
    let mut body = Vec::new();
    body.extend_from_slice(EVIDENCE_RECURRENT_MAGIC);
    push_bytes(&mut body, meta)?;
    push_bytes(&mut body, learned)?;
    push_bytes(&mut body, recurrent)?;
    Ok(body)
}

fn push_referenced_body(
    output: &mut Vec<u8>,
    references: &mut Vec<Vec<u8>>,
    body: &[u8],
) -> Result<(), HippocampalError> {
    output.extend_from_slice(&sha256(body));
    if !references
        .iter()
        .any(|existing| existing.as_slice() == body)
    {
        references.push(body.to_vec());
    }
    Ok(())
}

/// Encode one admitted episode as its current `GLHEP03` record plus the
/// referenced snapshot/evidence bodies. The record retains 32-byte content
/// addresses where the retired layout retained inline copies; the referenced
/// bodies are published into the same immutable cold custody, which already
/// stores each distinct object exactly once.
fn encode_episode_record(
    episode: &TypedEpisodeAdmission,
) -> Result<(Vec<u8>, Vec<Vec<u8>>), HippocampalError> {
    validate_episode(episode)?;
    let mut output = Vec::new();
    let mut references = Vec::new();
    output.extend_from_slice(EPISODE_V3_MAGIC);
    output.extend_from_slice(&episode.predecessor_generation.to_le_bytes());
    output.extend_from_slice(&episode.episode_generation.to_le_bytes());
    output.extend_from_slice(&episode.source_authority);
    push_bytes(&mut output, &episode.source_body)?;
    push_usize(&mut output, episode.source_port_count)?;
    push_usize(&mut output, episode.source_sample_count)?;
    push_usize(&mut output, episode.source_occurrence_count)?;
    push_usize(&mut output, episode.source_occurrence_frame_count)?;
    push_usize(&mut output, episode.source_occurrence_index)?;
    push_bytes(&mut output, &episode.physical_mosaic)?;
    match split_original_evidence(&episode.original_transition_evidence) {
        OriginalEvidenceSplit::Whole(body) => {
            output.push(0);
            push_referenced_body(&mut output, &mut references, body)?;
        }
        OriginalEvidenceSplit::Split { pre, post, tail } => {
            output.push(1);
            push_referenced_body(&mut output, &mut references, pre)?;
            match post {
                None => output.push(0),
                Some(post) => {
                    output.push(1);
                    push_referenced_body(&mut output, &mut references, post)?;
                }
            }
            push_bytes(&mut output, tail)?;
        }
    }
    match split_recurrent_evidence(&episode.recurrent_transition_evidence) {
        RecurrentEvidenceSplit::Whole(body) => {
            output.push(0);
            push_referenced_body(&mut output, &mut references, body)?;
        }
        RecurrentEvidenceSplit::Split {
            meta,
            learned,
            recurrent,
        } => {
            output.push(1);
            push_bytes(&mut output, meta)?;
            push_referenced_body(&mut output, &mut references, learned)?;
            push_referenced_body(&mut output, &mut references, recurrent)?;
        }
    }
    push_usize(&mut output, episode.participants.len())?;
    for participant in episode.participants.iter() {
        output.extend_from_slice(&participant.lineage);
    }
    Ok((output, references))
}

/// The retired inline episode layout, retained only so bodies admitted before
/// the content-addressed record still restore and re-verify canonically.
fn encode_episode_v2(episode: &TypedEpisodeAdmission) -> Result<Vec<u8>, HippocampalError> {
    validate_episode(episode)?;
    let mut output = Vec::new();
    output.extend_from_slice(EPISODE_MAGIC);
    output.extend_from_slice(&episode.predecessor_generation.to_le_bytes());
    output.extend_from_slice(&episode.episode_generation.to_le_bytes());
    output.extend_from_slice(&episode.source_authority);
    push_bytes(&mut output, &episode.source_body)?;
    push_usize(&mut output, episode.source_port_count)?;
    push_usize(&mut output, episode.source_sample_count)?;
    push_usize(&mut output, episode.source_occurrence_count)?;
    push_usize(&mut output, episode.source_occurrence_frame_count)?;
    push_usize(&mut output, episode.source_occurrence_index)?;
    push_bytes(&mut output, &episode.physical_mosaic)?;
    push_bytes(&mut output, &episode.original_transition_evidence)?;
    push_bytes(&mut output, &episode.recurrent_transition_evidence)?;
    push_usize(&mut output, episode.participants.len())?;
    for participant in episode.participants.iter() {
        output.extend_from_slice(&participant.lineage);
    }
    Ok(output)
}

struct EpisodeRecordPrefix {
    predecessor_generation: u64,
    episode_generation: u64,
    source_authority: HippocampalAddress,
    source_body: Box<[u8]>,
    source_port_count: usize,
    source_sample_count: usize,
    source_occurrence_count: usize,
    source_occurrence_frame_count: usize,
    source_occurrence_index: usize,
    physical_mosaic: Box<[u8]>,
}

fn decode_episode_record_prefix<'a>(
    reader: &mut Reader<'a>,
) -> Result<EpisodeRecordPrefix, HippocampalError> {
    Ok(EpisodeRecordPrefix {
        predecessor_generation: reader.u64()?,
        episode_generation: reader.u64()?,
        source_authority: reader.address()?,
        source_body: reader.bytes()?.to_vec().into_boxed_slice(),
        source_port_count: reader.usize()?,
        source_sample_count: reader.usize()?,
        source_occurrence_count: reader.usize()?,
        source_occurrence_frame_count: reader.usize()?,
        source_occurrence_index: reader.usize()?,
        physical_mosaic: reader.bytes()?.to_vec().into_boxed_slice(),
    })
}

enum OriginalEvidenceReference {
    Whole(HippocampalAddress),
    Split {
        pre: HippocampalAddress,
        post: Option<HippocampalAddress>,
        tail: Box<[u8]>,
    },
}

enum RecurrentEvidenceReference {
    Whole(HippocampalAddress),
    Split {
        meta: Box<[u8]>,
        learned: HippocampalAddress,
        recurrent: HippocampalAddress,
    },
}

struct EpisodeRecord {
    prefix: EpisodeRecordPrefix,
    original: OriginalEvidenceReference,
    recurrent: RecurrentEvidenceReference,
    participants: Box<[EpisodeParticipant]>,
}

fn decode_episode_record(encoded: &[u8]) -> Result<EpisodeRecord, HippocampalError> {
    let mut reader = Reader::new(encoded);
    if reader.take(EPISODE_V3_MAGIC.len())? != EPISODE_V3_MAGIC {
        return Err(HippocampalError::WrongObjectType);
    }
    let prefix = decode_episode_record_prefix(&mut reader)?;
    let original = match reader.u8()? {
        0 => OriginalEvidenceReference::Whole(reader.address()?),
        1 => {
            let pre = reader.address()?;
            let post = match reader.u8()? {
                0 => None,
                1 => Some(reader.address()?),
                _ => return Err(HippocampalError::MalformedObject),
            };
            let tail = reader.bytes()?.to_vec().into_boxed_slice();
            OriginalEvidenceReference::Split { pre, post, tail }
        }
        _ => return Err(HippocampalError::MalformedObject),
    };
    let recurrent = match reader.u8()? {
        0 => RecurrentEvidenceReference::Whole(reader.address()?),
        1 => {
            let meta = reader.bytes()?.to_vec().into_boxed_slice();
            RecurrentEvidenceReference::Split {
                meta,
                learned: reader.address()?,
                recurrent: reader.address()?,
            }
        }
        _ => return Err(HippocampalError::MalformedObject),
    };
    let count = reader.usize()?;
    reader.require_records(count, 16)?;
    let mut participants = Vec::new();
    participants
        .try_reserve_exact(count)
        .map_err(|_| HippocampalError::ArithmeticOverflow)?;
    for _ in 0..count {
        let lineage = reader.lineage()?;
        participants.push(EpisodeParticipant { lineage });
    }
    if !reader.finished() {
        return Err(HippocampalError::MalformedObject);
    }
    Ok(EpisodeRecord {
        prefix,
        original,
        recurrent,
        participants: participants.into_boxed_slice(),
    })
}

/// Record-level view of one retained episode: exactly the fields navigation is
/// entitled to (generation ordering and participant binding) without pulling
/// the referenced snapshot bodies out of cold custody.
fn decode_episode_summary(
    encoded: &[u8],
) -> Result<(u64, Box<[EpisodeParticipant]>), HippocampalError> {
    if encoded.get(..EPISODE_V3_MAGIC.len()) == Some(EPISODE_V3_MAGIC.as_slice()) {
        let record = decode_episode_record(encoded)?;
        Ok((record.prefix.episode_generation, record.participants))
    } else {
        let episode = decode_episode_inline(encoded)?;
        Ok((episode.episode_generation, episode.participants))
    }
}

fn decode_episode_inline(encoded: &[u8]) -> Result<TypedEpisodeAdmission, HippocampalError> {
    let mut reader = Reader::new(encoded);
    if reader.take(EPISODE_MAGIC.len())? != EPISODE_MAGIC {
        return Err(HippocampalError::WrongObjectType);
    }
    let prefix = decode_episode_record_prefix(&mut reader)?;
    let original_transition_evidence = reader.bytes()?.to_vec().into_boxed_slice();
    let recurrent_transition_evidence = reader.bytes()?.to_vec().into_boxed_slice();
    let count = reader.usize()?;
    reader.require_records(count, 16)?;
    let mut participants = Vec::new();
    participants
        .try_reserve_exact(count)
        .map_err(|_| HippocampalError::ArithmeticOverflow)?;
    for _ in 0..count {
        let lineage = reader.lineage()?;
        participants.push(EpisodeParticipant { lineage });
    }
    if !reader.finished() {
        return Err(HippocampalError::MalformedObject);
    }
    let episode = TypedEpisodeAdmission {
        predecessor_generation: prefix.predecessor_generation,
        episode_generation: prefix.episode_generation,
        source_authority: prefix.source_authority,
        source_body: prefix.source_body,
        source_port_count: prefix.source_port_count,
        source_sample_count: prefix.source_sample_count,
        source_occurrence_count: prefix.source_occurrence_count,
        source_occurrence_frame_count: prefix.source_occurrence_frame_count,
        source_occurrence_index: prefix.source_occurrence_index,
        physical_mosaic: prefix.physical_mosaic,
        original_transition_evidence,
        recurrent_transition_evidence,
        participants: participants.into_boxed_slice(),
    };
    validate_episode(&episode)?;
    if encode_episode_v2(&episode)? != encoded {
        return Err(HippocampalError::MalformedObject);
    }
    Ok(episode)
}

/// Reconstruct one complete typed episode from either admitted layout. For the
/// content-addressed record every referenced body is fetched from custody
/// (content-verified by address on read) and reassembled into the exact
/// original evidence bytes; the canonical re-encode proof then re-splits the
/// reconstruction and must reproduce the record byte-for-byte.
fn decode_episode(
    cold: &dyn HippocampalColdPort,
    encoded: &[u8],
) -> Result<TypedEpisodeAdmission, HippocampalError> {
    if encoded.get(..EPISODE_V3_MAGIC.len()) != Some(EPISODE_V3_MAGIC.as_slice()) {
        return decode_episode_inline(encoded);
    }
    let record = decode_episode_record(encoded)?;
    let original_transition_evidence = match &record.original {
        OriginalEvidenceReference::Whole(address) => read_exact(cold, *address)?.into_vec(),
        OriginalEvidenceReference::Split { pre, post, tail } => {
            let pre = read_exact(cold, *pre)?;
            let post = post.map(|address| read_exact(cold, address)).transpose()?;
            assemble_original_evidence(&pre, post.as_deref(), tail)?
        }
    };
    let recurrent_transition_evidence = match &record.recurrent {
        RecurrentEvidenceReference::Whole(address) => read_exact(cold, *address)?.into_vec(),
        RecurrentEvidenceReference::Split {
            meta,
            learned,
            recurrent,
        } => {
            let learned = read_exact(cold, *learned)?;
            let recurrent = read_exact(cold, *recurrent)?;
            assemble_recurrent_evidence(meta, &learned, &recurrent)?
        }
    };
    let episode = TypedEpisodeAdmission {
        predecessor_generation: record.prefix.predecessor_generation,
        episode_generation: record.prefix.episode_generation,
        source_authority: record.prefix.source_authority,
        source_body: record.prefix.source_body,
        source_port_count: record.prefix.source_port_count,
        source_sample_count: record.prefix.source_sample_count,
        source_occurrence_count: record.prefix.source_occurrence_count,
        source_occurrence_frame_count: record.prefix.source_occurrence_frame_count,
        source_occurrence_index: record.prefix.source_occurrence_index,
        physical_mosaic: record.prefix.physical_mosaic,
        original_transition_evidence: original_transition_evidence.into_boxed_slice(),
        recurrent_transition_evidence: recurrent_transition_evidence.into_boxed_slice(),
        participants: record.participants,
    };
    validate_episode(&episode)?;
    if encode_episode_record(&episode)?.0 != encoded {
        return Err(HippocampalError::MalformedObject);
    }
    Ok(episode)
}

fn encode_posting(posting: PostingSegment) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(POSTING_MAGIC);
    output.extend_from_slice(&posting.lineage);
    output.extend_from_slice(&posting.episode_generation.to_le_bytes());
    output.extend_from_slice(&posting.episode_address);
    push_optional_address(&mut output, posting.prior);
    output
}

fn decode_posting(encoded: &[u8]) -> Result<PostingSegment, HippocampalError> {
    let mut reader = Reader::new(encoded);
    if reader.take(POSTING_MAGIC.len())? != POSTING_MAGIC {
        return Err(HippocampalError::WrongObjectType);
    }
    let posting = PostingSegment {
        lineage: reader.lineage()?,
        episode_generation: reader.u64()?,
        episode_address: reader.address()?,
        prior: reader.optional_address()?,
    };
    if posting.episode_generation == 0 || !reader.finished() {
        return Err(HippocampalError::MalformedObject);
    }
    Ok(posting)
}

fn encode_radix(node: &RadixNode) -> Vec<u8> {
    let mut output = Vec::with_capacity(RADIX_MAGIC.len() + 1 + 16 * 33);
    output.extend_from_slice(RADIX_MAGIC);
    output.push(node.depth);
    for child in node.children {
        push_optional_address(&mut output, child);
    }
    output
}

fn decode_radix(encoded: &[u8]) -> Result<RadixNode, HippocampalError> {
    let mut reader = Reader::new(encoded);
    if reader.take(RADIX_MAGIC.len())? != RADIX_MAGIC {
        return Err(HippocampalError::WrongObjectType);
    }
    let depth = reader.u8()?;
    if usize::from(depth) >= RADIX_DEPTH {
        return Err(HippocampalError::MalformedObject);
    }
    let mut children = [None; 16];
    for child in &mut children {
        *child = reader.optional_address()?;
    }
    if !reader.finished() {
        return Err(HippocampalError::MalformedObject);
    }
    Ok(RadixNode { depth, children })
}

fn add_object(
    objects: &mut BTreeMap<HippocampalAddress, Box<[u8]>>,
    bytes: Vec<u8>,
) -> HippocampalAddress {
    let address = sha256(&bytes);
    objects
        .entry(address)
        .or_insert_with(|| bytes.into_boxed_slice());
    address
}

fn read_optional(
    cold: &dyn HippocampalColdPort,
    address: HippocampalAddress,
) -> Result<Option<Box<[u8]>>, HippocampalError> {
    let body = cold
        .read_object(address)
        .map_err(HippocampalError::ColdCustodyUnavailable)?;
    if let Some(bytes) = body.as_ref() {
        if sha256(bytes) != address {
            return Err(HippocampalError::AddressMismatch(address));
        }
    }
    Ok(body)
}

fn read_exact(
    cold: &dyn HippocampalColdPort,
    address: HippocampalAddress,
) -> Result<Box<[u8]>, HippocampalError> {
    read_optional(cold, address)?.ok_or(HippocampalError::MissingObject(address))
}

fn resolve(
    cold: &dyn HippocampalColdPort,
    prepared: &BTreeMap<HippocampalAddress, Box<[u8]>>,
    address: HippocampalAddress,
) -> Result<Box<[u8]>, HippocampalError> {
    let bytes = match prepared.get(&address) {
        Some(bytes) => bytes.clone(),
        None => read_exact(cold, address)?,
    };
    if sha256(&bytes) != address {
        return Err(HippocampalError::AddressMismatch(address));
    }
    Ok(bytes)
}

fn nibble(lineage: NeuronLineage, depth: usize) -> usize {
    let byte = lineage[depth / 2];
    usize::from(if depth % 2 == 0 {
        byte >> 4
    } else {
        byte & 0x0f
    })
}

fn push_usize(output: &mut Vec<u8>, value: usize) -> Result<(), HippocampalError> {
    output.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| HippocampalError::ArithmeticOverflow)?
            .to_le_bytes(),
    );
    Ok(())
}

fn push_bytes(output: &mut Vec<u8>, bytes: &[u8]) -> Result<(), HippocampalError> {
    push_usize(output, bytes.len())?;
    output.extend_from_slice(bytes);
    Ok(())
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

    fn require_records(&self, count: usize, minimum: usize) -> Result<(), HippocampalError> {
        let required = count
            .checked_mul(minimum)
            .ok_or(HippocampalError::ArithmeticOverflow)?;
        if required > self.encoded.len().saturating_sub(self.cursor) {
            return Err(HippocampalError::MalformedObject);
        }
        Ok(())
    }

    fn u8(&mut self) -> Result<u8, HippocampalError> {
        Ok(self.take(1)?[0])
    }

    fn u64(&mut self) -> Result<u64, HippocampalError> {
        Ok(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| HippocampalError::MalformedObject)?,
        ))
    }

    fn usize(&mut self) -> Result<usize, HippocampalError> {
        usize::try_from(self.u64()?).map_err(|_| HippocampalError::ArithmeticOverflow)
    }

    fn bytes(&mut self) -> Result<&'a [u8], HippocampalError> {
        let count = self.usize()?;
        self.take(count)
    }

    fn lineage(&mut self) -> Result<NeuronLineage, HippocampalError> {
        self.take(16)?
            .try_into()
            .map_err(|_| HippocampalError::MalformedObject)
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

    fn lineage(value: u8) -> NeuronLineage {
        let mut lineage = [0u8; 16];
        lineage[15] = value;
        lineage
    }

    fn episode(generation: u64, lineages: &[NeuronLineage]) -> TypedEpisodeAdmission {
        let source_body = vec![1, generation as u8].into_boxed_slice();
        TypedEpisodeAdmission {
            predecessor_generation: generation - 1,
            episode_generation: generation,
            source_authority: sha256(&source_body),
            source_body,
            source_port_count: 1,
            source_sample_count: 1,
            source_occurrence_count: 1,
            source_occurrence_frame_count: 1,
            source_occurrence_index: 0,
            physical_mosaic: vec![2, generation as u8].into_boxed_slice(),
            original_transition_evidence: vec![3, generation as u8].into_boxed_slice(),
            recurrent_transition_evidence: vec![4, generation as u8].into_boxed_slice(),
            participants: lineages
                .iter()
                .map(|lineage| EpisodeParticipant { lineage: *lineage })
                .collect::<Vec<_>>()
                .into_boxed_slice(),
        }
    }

    fn admission_envelope(participants: usize) -> HippocampalAdmissionEnvelope {
        HippocampalAdmissionEnvelope {
            max_objects: 5 + participants * (1 + RADIX_DEPTH),
            max_object_bytes: 1_000_000,
        }
    }

    #[test]
    fn retired_cohort_local_episode_layout_fails_closed() {
        let cold = HippocampalColdStore::default();
        let mut retired = encode_episode_v2(&episode(1, &[lineage(1)])).unwrap();
        retired[..EPISODE_MAGIC.len()].copy_from_slice(b"GLHEP01\0");
        assert_eq!(
            decode_episode(&cold, &retired),
            Err(HippocampalError::WrongObjectType)
        );
    }

    #[test]
    fn split_episode_stores_shared_snapshots_once_and_round_trips_via_directory_store() {
        use crate::hippocampal_directory_cold_store::DirectoryHippocampalColdStore;

        let root = std::env::temp_dir().join(format!(
            "guala-episode-reference-test-{}-{}",
            std::process::id(),
            line!(),
        ));
        let _ = std::fs::remove_dir_all(&root);
        let mut cold = DirectoryHippocampalColdStore::open(&root).unwrap();
        let object_count = |root: &std::path::Path| std::fs::read_dir(root).unwrap().count();

        let pre = b"pre-experience-snapshot-body".to_vec();
        let shared = b"post-and-learned-snapshot-body".to_vec();
        let recurrent = b"recurrent-snapshot-body".to_vec();
        let build = |generation: u64, recurrent_body: &[u8]| {
            let source_body: Box<[u8]> = vec![1, generation as u8].into_boxed_slice();
            TypedEpisodeAdmission {
                predecessor_generation: generation - 1,
                episode_generation: generation,
                source_authority: sha256(&source_body),
                source_body,
                source_port_count: 1,
                source_sample_count: 1,
                source_occurrence_count: 1,
                source_occurrence_frame_count: 1,
                source_occurrence_index: 0,
                physical_mosaic: vec![2, generation as u8].into_boxed_slice(),
                original_transition_evidence: assemble_original_evidence(
                    &pre,
                    Some(&shared),
                    b"bool-tail",
                )
                .unwrap()
                .into_boxed_slice(),
                recurrent_transition_evidence: assemble_recurrent_evidence(
                    b"recurrence-meta",
                    &shared,
                    recurrent_body,
                )
                .unwrap()
                .into_boxed_slice(),
                participants: Box::new([EpisodeParticipant {
                    lineage: lineage(1),
                }]),
            }
        };

        let first = build(1, &recurrent);
        let mut index = ResidentHippocampalIndex::default();
        let prepared = index
            .prepare(&cold, &first, admission_envelope(1))
            .unwrap();
        // record + pre + shared(post == learned, interned once) + recurrent
        // + one posting + one radix path copy.
        assert_eq!(prepared.prepared_object_count(), 4 + 1 + RADIX_DEPTH);
        let published = publish_hippocampal_admission(&mut cold, &prepared).unwrap();
        index.adopt(published).unwrap();
        let first_count = object_count(&root);
        assert_eq!(first_count, 4 + 1 + RADIX_DEPTH);
        let resolved = resolve_hippocampal_episode(
            &cold,
            index.checkpoint().latest_episode().unwrap(),
        )
        .unwrap();
        assert_eq!(resolved, first);

        // A later episode reusing the same snapshots republishes none of them.
        let second = build(2, b"second-recurrent-snapshot-body");
        let prepared = index
            .prepare(&cold, &second, admission_envelope(1))
            .unwrap();
        let published = publish_hippocampal_admission(&mut cold, &prepared).unwrap();
        index.adopt(published).unwrap();
        let second_count = object_count(&root);
        // New: record, the one changed snapshot, posting, radix path copy.
        assert_eq!(second_count - first_count, 3 + RADIX_DEPTH);
        let resolved = resolve_hippocampal_episode(
            &cold,
            index.checkpoint().latest_episode().unwrap(),
        )
        .unwrap();
        assert_eq!(resolved, second);
        validate_hippocampal_checkpoint(&cold, index.checkpoint()).unwrap();
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn retired_inline_episode_layout_still_resolves_exactly() {
        let cold = HippocampalColdStore::default();
        let admitted = episode(1, &[lineage(1), lineage(2)]);
        let inline = encode_episode_v2(&admitted).unwrap();
        assert_eq!(decode_episode(&cold, &inline).unwrap(), admitted);
    }

    #[test]
    fn one_three_and_four_participants_prepare_with_exact_fixed_depth_bound() {
        for count in [1usize, 3, 4] {
            let lineages = (1..=count)
                .map(|value| lineage(value as u8))
                .collect::<Vec<_>>();
            let state = ResidentHippocampalIndex::default();
            let cold = HippocampalColdStore::default();
            let prepared = state
                .prepare(&cold, &episode(1, &lineages), admission_envelope(count))
                .unwrap();
            assert_eq!(prepared.posting_count(), count);
            assert!(prepared.prepared_object_count() <= 3 + count * (1 + RADIX_DEPTH));
            assert_eq!(state, ResidentHippocampalIndex::default());
        }
    }

    #[test]
    fn ordered_postings_page_with_count_and_byte_continuation_without_cognition() {
        let target = lineage(1);
        let unrelated = lineage(2);
        let mut state = ResidentHippocampalIndex::default();
        let mut cold = HippocampalColdStore::default();
        let first = state
            .prepare(
                &cold,
                &episode(1, &[target, unrelated]),
                admission_envelope(2),
            )
            .unwrap();
        let published = cold.publish(&first).unwrap();
        state.adopt(published).unwrap();
        let checkpoint_bytes = state.encode().unwrap().len();
        let unrelated_head = cold
            .posting_head_from(state.checkpoint.root, unrelated, &BTreeMap::new())
            .unwrap();
        let second = state
            .prepare(&cold, &episode(2, &[target]), admission_envelope(1))
            .unwrap();
        let published = cold.publish(&second).unwrap();
        state.adopt(published).unwrap();
        assert_eq!(state.encode().unwrap().len(), checkpoint_bytes);
        assert_eq!(
            cold.posting_head_from(state.checkpoint.root, unrelated, &BTreeMap::new())
                .unwrap(),
            unrelated_head
        );

        let first_page = state
            .navigate(
                &cold,
                target,
                None,
                HippocampalTraversalEnvelope {
                    max_postings: 1,
                    max_decoded_bytes: 1_000_000,
                },
            )
            .unwrap();
        assert_eq!(first_page.postings.len(), 1);
        assert_eq!(first_page.postings[0].episode_generation, 2);
        assert!(first_page.continuation.is_some());
        let second_page = state
            .navigate(
                &cold,
                target,
                first_page.continuation,
                HippocampalTraversalEnvelope {
                    max_postings: 1,
                    max_decoded_bytes: 1_000_000,
                },
            )
            .unwrap();
        assert_eq!(second_page.postings[0].episode_generation, 1);
        assert!(second_page.continuation.is_none());
    }

    #[test]
    fn exact_cold_restore_rejects_missing_tampered_malformed_and_trailing_state() {
        let target = lineage(1);
        let mut state = ResidentHippocampalIndex::default();
        let mut cold = HippocampalColdStore::default();
        let prepared = state
            .prepare(&cold, &episode(1, &[target]), admission_envelope(1))
            .unwrap();
        let published = cold.publish(&prepared).unwrap();
        state.adopt(published).unwrap();
        let bytes = state.encode().unwrap();
        assert_eq!(ResidentHippocampalIndex::decode(&bytes).unwrap(), state);
        cold.validate_checkpoint(state.checkpoint()).unwrap();

        let mut trailing = bytes.clone();
        trailing.push(0);
        assert!(ResidentHippocampalIndex::decode(&trailing).is_err());
        let mut tampered = cold.clone();
        *tampered
            .objects
            .get_mut(&state.checkpoint.root.unwrap())
            .unwrap()
            .last_mut()
            .unwrap() ^= 1;
        assert!(tampered.validate_checkpoint(state.checkpoint()).is_err());
        let mut missing = cold.clone();
        missing.objects.remove(&state.checkpoint.root.unwrap());
        assert!(missing.validate_checkpoint(state.checkpoint()).is_err());
        assert!(ResidentHippocampalIndex::decode(b"wrong").is_err());
    }

    #[test]
    fn traversal_envelopes_refuse_zero_or_too_small_work() {
        let target = lineage(1);
        let mut state = ResidentHippocampalIndex::default();
        let mut cold = HippocampalColdStore::default();
        let prepared = state
            .prepare(&cold, &episode(1, &[target]), admission_envelope(1))
            .unwrap();
        let published = cold.publish(&prepared).unwrap();
        state.adopt(published).unwrap();
        assert_eq!(
            state.navigate(
                &cold,
                target,
                None,
                HippocampalTraversalEnvelope {
                    max_postings: 0,
                    max_decoded_bytes: 1
                }
            ),
            Err(HippocampalError::TraversalCountBudget)
        );
        assert_eq!(
            state.navigate(
                &cold,
                target,
                None,
                HippocampalTraversalEnvelope {
                    max_postings: 1,
                    max_decoded_bytes: 1
                }
            ),
            Err(HippocampalError::TraversalByteBudget)
        );
    }

    #[test]
    fn failed_cold_batch_leaves_checkpoint_and_store_unchanged() {
        let target = lineage(1);
        let state = ResidentHippocampalIndex::default();
        let mut cold = HippocampalColdStore::default();
        let prepared = state
            .prepare(&cold, &episode(1, &[target]), admission_envelope(1))
            .unwrap();
        let predecessor = state;
        let cold_predecessor = cold.clone();
        let prepared_object_count = prepared.objects.len();
        assert_eq!(
            cold.publish_checked(&prepared, |completed| {
                if completed == prepared_object_count {
                    Err(HippocampalError::MalformedObject)
                } else {
                    Ok(())
                }
            }),
            Err(HippocampalError::MalformedObject)
        );
        assert_eq!(state, predecessor);
        assert_eq!(cold, cold_predecessor);

        let mut corrupted = prepared;
        let first = *corrupted.objects.keys().next().unwrap();
        corrupted.objects.get_mut(&first).unwrap()[0] ^= 1;
        assert!(cold.publish(&corrupted).is_err());
        assert_eq!(state, predecessor);
        assert_eq!(cold, cold_predecessor);
    }

    #[test]
    fn publication_work_and_delta_allocation_ignore_large_unrelated_history() {
        let target = lineage(1);
        let state = ResidentHippocampalIndex::default();
        let empty = HippocampalColdStore::default();
        let prepared = state
            .prepare(&empty, &episode(1, &[target]), admission_envelope(1))
            .unwrap();

        let mut without_history = empty;
        let (_, empty_inspected, empty_delta_objects, empty_delta_bytes) = without_history
            .publish_checked(&prepared, |_| Ok(()))
            .unwrap();

        let mut with_history = HippocampalColdStore::default();
        for ordinal in 0..16_384u64 {
            let mut body = b"unrelated immutable cold object".to_vec();
            body.extend_from_slice(&ordinal.to_be_bytes());
            let address = sha256(&body);
            with_history
                .objects
                .insert(address, body.into_boxed_slice());
        }
        let unrelated_count = with_history.object_count();
        let (_, history_inspected, history_delta_objects, history_delta_bytes) =
            with_history.publish_checked(&prepared, |_| Ok(())).unwrap();

        assert_eq!(history_inspected, empty_inspected);
        assert_eq!(history_delta_objects, empty_delta_objects);
        assert_eq!(history_delta_bytes, empty_delta_bytes);
        assert_eq!(history_inspected, prepared.objects.len());
        assert_eq!(
            with_history.object_count(),
            unrelated_count + history_delta_objects
        );
    }

    #[test]
    fn source_address_divergence_and_duplicate_member_binding_are_rejected() {
        let target = lineage(1);
        let cold = HippocampalColdStore::default();
        let state = ResidentHippocampalIndex::default();
        let mut changed_source = episode(1, &[target]);
        changed_source.source_body[0] ^= 1;
        assert!(matches!(
            state.prepare(&cold, &changed_source, admission_envelope(1)),
            Err(HippocampalError::AddressMismatch(_))
        ));

        let mut duplicate_member = episode(1, &[target, lineage(2)]);
        duplicate_member.participants[1].lineage = duplicate_member.participants[0].lineage;
        assert_eq!(
            state.prepare(&cold, &duplicate_member, admission_envelope(2)),
            Err(HippocampalError::DuplicateOrUnorderedParticipants)
        );
    }
}
