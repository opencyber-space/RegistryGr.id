use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};
use std::sync::atomic::{AtomicU64, Ordering};

static GLOBAL_VERSION: AtomicU64 = AtomicU64::new(0);

const CHUNK_SIZE: usize = 4 * 1024 * 1024;

#[derive(Debug, Clone)]
pub struct Chunk {
    pub index: usize,
    pub offset: usize,
    pub length: usize,
    pub data: Vec<u8>,
}

pub struct Chunker {
    chunk_size: usize,
}

impl Chunker {
    pub fn new() -> Self {
        Self { chunk_size: CHUNK_SIZE }
    }

    pub fn with_size(chunk_size: usize) -> Self {
        Self { chunk_size }
    }

    pub fn split(&self, data: &[u8]) -> Vec<Chunk> {
        let mut chunks = Vec::new();
        let mut offset = 0;
        let mut index = 0;
        while offset < data.len() {
            let end = (offset + self.chunk_size).min(data.len());
            chunks.push(Chunk {
                index,
                offset,
                length: end - offset,
                data: data[offset..end].to_vec(),
            });
            offset = end;
            index += 1;
        }
        chunks
    }

    pub fn aligned_ranges(&self, chunks: &[Chunk]) -> Vec<(usize, usize)> {
        chunks.iter().map(|c| (c.offset, c.offset + c.length - 1)).collect()
    }
}

pub struct Hasher;

impl Hasher {
    pub fn new() -> Self {
        Self
    }

    pub fn hash_chunk(&self, data: &[u8]) -> Vec<u8> {
        Sha256::digest(data).to_vec()
    }

    pub fn compute_merkle_root(&self, chunks: &[Chunk]) -> Result<Vec<u8>, String> {
        if chunks.is_empty() {
            return Err("no chunks".into());
        }
        let hashes: Vec<Vec<u8>> = chunks.iter().map(|c| self.hash_chunk(&c.data)).collect();
        Ok(self.build_root(hashes))
    }

    fn build_root(&self, mut hashes: Vec<Vec<u8>>) -> Vec<u8> {
        if hashes.len() == 1 {
            return hashes.remove(0);
        }
        if hashes.len() % 2 != 0 {
            hashes.push(hashes.last().unwrap().clone());
        }
        let next: Vec<Vec<u8>> = hashes
            .chunks(2)
            .map(|pair| {
                let mut combined = pair[0].clone();
                combined.extend_from_slice(&pair[1]);
                Sha256::digest(&combined).to_vec()
            })
            .collect();
        self.build_root(next)
    }

    pub fn merkle_root_hex(&self, chunks: &[Chunk]) -> Result<String, String> {
        Ok(hex::encode(self.compute_merkle_root(chunks)?))
    }

    pub fn chunk_hash_hex(&self, data: &[u8]) -> String {
        hex::encode(self.hash_chunk(data))
    }
}

#[derive(Debug, Clone)]
pub struct AssetEntry {
    pub index: usize,
    pub offset: usize,
    pub length: usize,
    pub hash: String,
}

#[derive(Debug, Clone)]
pub struct Manifest {
    pub asset_id: String,
    pub version: u64,
    pub merkle_root: String,
    pub assets: Vec<AssetEntry>,
    pub created_at: u64,
}

pub struct ManifestBuilder {
    hasher: Hasher,
}

impl ManifestBuilder {
    pub fn new() -> Self {
        Self { hasher: Hasher::new() }
    }

    pub fn build(&self, chunks: &[Chunk], merkle_root: &[u8]) -> Result<Manifest, String> {
        let entries: Vec<AssetEntry> = chunks
            .iter()
            .map(|c| AssetEntry {
                index: c.index,
                offset: c.offset,
                length: c.length,
                hash: self.hasher.chunk_hash_hex(&c.data),
            })
            .collect();
        let version = GLOBAL_VERSION.fetch_add(1, Ordering::SeqCst) + 1;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        Ok(Manifest {
            asset_id: String::new(),
            version,
            merkle_root: hex::encode(merkle_root),
            assets: entries,
            created_at: now,
        })
    }
}

#[derive(Debug, Clone)]
pub struct Policy {
    pub propagation_intent: String,
    pub distribution_scope: String,
    pub ttl_seconds: u64,
    pub deletion_semantics: String,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            propagation_intent: "public".into(),
            distribution_scope: "global".into(),
            ttl_seconds: 86400,
            deletion_semantics: "tombstone".into(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct EncodedManifest {
    pub manifest: Manifest,
    pub policy: Policy,
}

pub struct PolicyEncoder;

impl PolicyEncoder {
    pub fn new() -> Self {
        Self
    }

    pub fn encode(&self, manifest: Manifest, policy: Policy) -> EncodedManifest {
        EncodedManifest { manifest, policy }
    }
}

#[derive(Debug, Clone)]
pub struct SignedEvent {
    pub id: String,
    pub pubkey: String,
    pub created_at: u64,
    pub kind: u32,
    pub content: String,
    pub sig: String,
    pub tags: Vec<Vec<String>>,
}

pub struct Signer;

impl Signer {
    pub fn new() -> Self {
        Self
    }

    pub fn sign(&self, encoded: &EncodedManifest, priv_key: &[u8]) -> Result<Vec<SignedEvent>, String> {
        let pub_key = self.derive_pubkey(priv_key);
        let content = format!(
            "{{\"version\":{},\"merkle_root\":\"{}\"}}",
            encoded.manifest.version, encoded.manifest.merkle_root
        );
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        let event_id = self.derive_id(&pub_key, now, 30000, &content);
        let sig = self.sign_payload(&event_id, priv_key);
        Ok(vec![SignedEvent {
            id: event_id,
            pubkey: pub_key,
            created_at: now,
            kind: 30000,
            content,
            sig,
            tags: vec![],
        }])
    }

    fn derive_pubkey(&self, priv_key: &[u8]) -> String {
        hex::encode(Sha256::digest(priv_key))
    }

    fn derive_id(&self, pub_key: &str, created_at: u64, kind: u32, content: &str) -> String {
        let payload = format!("[0,\"{}\",{},{},{},{:?}]", pub_key, created_at, kind, "[]", content);
        hex::encode(Sha256::digest(payload.as_bytes()))
    }

    fn sign_payload(&self, event_id: &str, priv_key: &[u8]) -> String {
        let mut data = priv_key.to_vec();
        data.extend_from_slice(event_id.as_bytes());
        hex::encode(Sha256::digest(&data))
    }
}

pub trait NostrPublisher: Send + Sync {
    fn publish_all(&self, events: &[SignedEvent]) -> Result<(), String>;
}

pub trait OriginUploader: Send + Sync {
    fn upload(&self, data: &[u8], asset_id: &str) -> Result<(), String>;
}

#[derive(Debug, Clone)]
pub struct UploadState {
    pub asset_id: String,
    pub completed_steps: std::collections::HashSet<String>,
    pub failed_step: Option<String>,
    pub chunks: Vec<Chunk>,
    pub merkle_root: Option<Vec<u8>>,
    pub manifest: Option<Manifest>,
    pub encoded_manifest: Option<EncodedManifest>,
    pub signed_events: Vec<SignedEvent>,
}

impl UploadState {
    pub fn new(asset_id: String) -> Self {
        Self {
            asset_id,
            completed_steps: std::collections::HashSet::new(),
            failed_step: None,
            chunks: vec![],
            merkle_root: None,
            manifest: None,
            encoded_manifest: None,
            signed_events: vec![],
        }
    }
}

pub struct SDKCore {
    chunker: Chunker,
    hasher: Hasher,
    manifest_builder: ManifestBuilder,
    policy_encoder: PolicyEncoder,
    signer: Signer,
    nostr_publisher: Box<dyn NostrPublisher>,
    origin_uploader: Box<dyn OriginUploader>,
    max_retries: usize,
    backoff_base_ms: u64,
}

impl SDKCore {
    pub fn new(nostr_publisher: Box<dyn NostrPublisher>, origin_uploader: Box<dyn OriginUploader>) -> Self {
        Self {
            chunker: Chunker::new(),
            hasher: Hasher::new(),
            manifest_builder: ManifestBuilder::new(),
            policy_encoder: PolicyEncoder::new(),
            signer: Signer::new(),
            nostr_publisher,
            origin_uploader,
            max_retries: 5,
            backoff_base_ms: 1000,
        }
    }

    pub fn upload(&self, asset: &[u8], policy: Policy, priv_key: &[u8]) -> Result<(), String> {
        let asset_id = hex::encode(Sha256::digest(asset));
        let mut state = UploadState::new(asset_id);

        if !state.completed_steps.contains("chunk") {
            self.with_retry(|| {
                state.chunks = self.chunker.split(asset);
                Ok(())
            })?;
            state.completed_steps.insert("chunk".into());
        }

        if !state.completed_steps.contains("hash") {
            self.with_retry(|| {
                state.merkle_root = Some(self.hasher.compute_merkle_root(&state.chunks)?);
                Ok(())
            })?;
            state.completed_steps.insert("hash".into());
        }

        if !state.completed_steps.contains("manifest") {
            self.with_retry(|| {
                let root = state.merkle_root.as_ref().ok_or("no root")?;
                state.manifest = Some(self.manifest_builder.build(&state.chunks, root)?);
                Ok(())
            })?;
            state.completed_steps.insert("manifest".into());
        }

        if !state.completed_steps.contains("encode") {
            self.with_retry(|| {
                let manifest = state.manifest.clone().ok_or("no manifest")?;
                state.encoded_manifest = Some(self.policy_encoder.encode(manifest, policy.clone()));
                Ok(())
            })?;
            state.completed_steps.insert("encode".into());
        }

        if !state.completed_steps.contains("sign") {
            self.with_retry(|| {
                let encoded = state.encoded_manifest.as_ref().ok_or("no encoded")?;
                state.signed_events = self.signer.sign(encoded, priv_key)?;
                Ok(())
            })?;
            state.completed_steps.insert("sign".into());
        }

        if !state.completed_steps.contains("publish") {
            self.with_retry(|| self.nostr_publisher.publish_all(&state.signed_events))?;
            state.completed_steps.insert("publish".into());
        }

        if !state.completed_steps.contains("upload") {
            self.with_retry(|| self.origin_uploader.upload(asset, &state.asset_id))?;
            state.completed_steps.insert("upload".into());
        }

        Ok(())
    }

    fn with_retry<F: Fn() -> Result<(), String>>(&self, f: F) -> Result<(), String> {
        let mut last_err = String::new();
        for i in 0..self.max_retries {
            match f() {
                Ok(()) => return Ok(()),
                Err(e) => {
                    last_err = e;
                    let wait = self.backoff_base_ms * 2u64.pow(i as u32);
                    std::thread::sleep(std::time::Duration::from_millis(wait));
                }
            }
        }
        Err(last_err)
    }
}
