use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
pub struct Event {
    pub id: String,
    pub pubkey: String,
    pub created_at: u64,
    pub kind: u32,
    pub content: String,
    pub sig: String,
}

#[derive(Debug, Clone)]
pub struct AssetRecord {
    pub id: String,
    pub author_key: String,
    pub manifest: String,
    pub version: u64,
    pub tags: Vec<String>,
    pub deleted: bool,
    pub deleted_at: Option<u64>,
    pub updated_at: u64,
}

pub struct SignatureValidator;

impl SignatureValidator {
    pub fn new() -> Self { Self }

    pub fn validate(&self, event: &Event) -> Result<(), String> {
        if event.id.is_empty() { return Err("missing id".into()); }
        if event.pubkey.is_empty() { return Err("missing pubkey".into()); }
        if event.sig.is_empty() { return Err("missing sig".into()); }
        let payload = format!(
            "[0,\"{}\",{},{},\"[]\",\"{}\"]",
            event.pubkey, event.created_at, event.kind, event.content
        );
        let expected = hex::encode(Sha256::digest(payload.as_bytes()));
        if expected != event.id {
            return Err("id mismatch".into());
        }
        Ok(())
    }
}

pub struct WriteAheadLog {
    file: Mutex<File>,
    seq: Mutex<u64>,
}

impl WriteAheadLog {
    pub fn new(path: &str) -> Result<Arc<Self>, String> {
        let file = OpenOptions::new()
            .append(true)
            .create(true)
            .read(true)
            .open(path)
            .map_err(|e| e.to_string())?;
        Ok(Arc::new(Self {
            file: Mutex::new(file),
            seq: Mutex::new(0),
        }))
    }

    pub fn log(&self, event: &Event) {
        let mut seq = self.seq.lock().unwrap();
        *seq += 1;
        let entry = format!(
            "{{\"seq\":{},\"id\":\"{}\",\"kind\":{}}}\n",
            *seq, event.id, event.kind
        );
        let mut file = self.file.lock().unwrap();
        let _ = file.write_all(entry.as_bytes());
        let _ = file.flush();
    }
}

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

pub struct StateBuilder {
    assets: RwLock<HashMap<String, AssetRecord>>,
    wal: Arc<WriteAheadLog>,
}

impl StateBuilder {
    pub fn new(wal: Arc<WriteAheadLog>) -> Arc<Self> {
        Arc::new(Self {
            assets: RwLock::new(HashMap::new()),
            wal,
        })
    }

    pub fn apply(&self, event: Event) {
        self.wal.log(&event);
        match event.kind {
            30000 => self.apply_asset(&event),
            5 => self.apply_deletion(&event),
            _ => {}
        }
    }

    fn apply_asset(&self, event: &Event) {
        let mut assets = self.assets.write().unwrap();
        let existing = assets.get(&event.id);
        if let Some(e) = existing {
            if e.version >= event.created_at {
                return;
            }
        }
        assets.insert(
            event.id.clone(),
            AssetRecord {
                id: event.id.clone(),
                author_key: event.pubkey.clone(),
                manifest: event.content.clone(),
                version: event.created_at,
                tags: vec![],
                deleted: false,
                deleted_at: None,
                updated_at: now_secs(),
            },
        );
    }

    fn apply_deletion(&self, event: &Event) {
        let mut assets = self.assets.write().unwrap();
        for record in assets.values_mut() {
            if record.author_key == event.pubkey {
                record.deleted = true;
                record.deleted_at = Some(now_secs());
            }
        }
    }

    pub fn get_asset(&self, id: &str) -> Option<AssetRecord> {
        self.assets.read().unwrap().get(id).cloned()
    }

    pub fn list_assets(&self) -> Vec<AssetRecord> {
        self.assets
            .read()
            .unwrap()
            .values()
            .filter(|r| !r.deleted)
            .cloned()
            .collect()
    }
}

pub struct AggregatorDatabase {
    assets: RwLock<HashMap<String, AssetRecord>>,
    tag_index: RwLock<HashMap<String, Vec<String>>>,
    schedulers: RwLock<HashMap<String, String>>,
}

impl AggregatorDatabase {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            assets: RwLock::new(HashMap::new()),
            tag_index: RwLock::new(HashMap::new()),
            schedulers: RwLock::new(HashMap::new()),
        })
    }

    pub fn persist_asset(&self, record: AssetRecord) {
        let mut tag_idx = self.tag_index.write().unwrap();
        for tag in &record.tags {
            tag_idx.entry(tag.clone()).or_default().push(record.id.clone());
        }
        self.assets.write().unwrap().insert(record.id.clone(), record);
    }

    pub fn get_asset(&self, id: &str) -> Option<AssetRecord> {
        self.assets.read().unwrap().get(id).cloned()
    }

    pub fn query_by_tag(&self, tag: &str) -> Vec<AssetRecord> {
        let tag_idx = self.tag_index.read().unwrap();
        let ids = match tag_idx.get(tag) {
            Some(ids) => ids.clone(),
            None => return vec![],
        };
        let assets = self.assets.read().unwrap();
        ids.iter().filter_map(|id| assets.get(id).cloned()).collect()
    }

    pub fn persist_scheduler(&self, scheduler_id: String, info: String) {
        self.schedulers.write().unwrap().insert(scheduler_id, info);
    }
}

pub struct HotCache {
    store: Mutex<HashMap<String, (Vec<u8>, u64)>>,
    ttl: u64,
}

impl HotCache {
    pub fn new(ttl_secs: u64) -> Arc<Self> {
        let cache = Arc::new(Self {
            store: Mutex::new(HashMap::new()),
            ttl: ttl_secs,
        });
        let c = Arc::clone(&cache);
        thread::spawn(move || loop {
            thread::sleep(Duration::from_secs(ttl_secs / 2));
            let now = now_secs();
            let mut store = c.store.lock().unwrap();
            store.retain(|_, (_, exp)| *exp > now);
        });
        cache
    }

    pub fn set(&self, key: String, value: Vec<u8>) {
        let exp = now_secs() + self.ttl;
        self.store.lock().unwrap().insert(key, (value, exp));
    }

    pub fn get(&self, key: &str) -> Option<Vec<u8>> {
        let mut store = self.store.lock().unwrap();
        match store.get(key) {
            Some((val, exp)) if *exp > now_secs() => Some(val.clone()),
            Some(_) => {
                store.remove(key);
                None
            }
            None => None,
        }
    }

    pub fn delete(&self, key: &str) {
        self.store.lock().unwrap().remove(key);
    }
}

#[derive(Debug, Clone)]
pub struct StateDelta {
    pub from_version: u64,
    pub to_version: u64,
    pub changes: Vec<AssetRecord>,
}

pub trait L2Peer: Send + Sync {
    fn exchange_delta(&self, delta: StateDelta) -> Result<StateDelta, String>;
}

pub struct L2StateSynchronizer {
    builder: Arc<StateBuilder>,
    peers: Vec<Box<dyn L2Peer>>,
    interval: Duration,
    version: Mutex<u64>,
}

impl L2StateSynchronizer {
    pub fn new(builder: Arc<StateBuilder>, peers: Vec<Box<dyn L2Peer>>, interval: Duration) -> Self {
        Self {
            builder,
            peers,
            interval,
            version: Mutex::new(0),
        }
    }

    pub fn run(&self) {
        loop {
            thread::sleep(self.interval);
            self.sync();
        }
    }

    fn sync(&self) {
        let current = *self.version.lock().unwrap();
        let delta = StateDelta {
            from_version: current,
            to_version: current,
            changes: self.builder.list_assets(),
        };
        for peer in &self.peers {
            if let Ok(remote) = peer.exchange_delta(delta.clone()) {
                self.apply_delta(remote);
            }
        }
    }

    fn apply_delta(&self, delta: StateDelta) {
        for record in delta.changes {
            self.builder.apply(Event {
                id: record.id,
                pubkey: record.author_key,
                created_at: record.version,
                kind: 30000,
                content: record.manifest,
                sig: String::new(),
            });
        }
        let mut v = self.version.lock().unwrap();
        if delta.to_version > *v {
            *v = delta.to_version;
        }
    }
}

pub struct CheckpointBuilder {
    state_builder: Arc<StateBuilder>,
}

impl CheckpointBuilder {
    pub fn new(state_builder: Arc<StateBuilder>) -> Self {
        Self { state_builder }
    }

    pub fn derive_root(&self) -> String {
        let assets = self.state_builder.list_assets();
        let data = assets.iter().map(|a| a.id.clone()).collect::<Vec<_>>().join(",");
        hex::encode(Sha256::digest(data.as_bytes()))
    }
}

#[derive(Debug, Clone)]
pub struct ThresholdSignature {
    pub indexer_id: String,
    pub sig: String,
    pub root: String,
    pub signed_at: u64,
}

#[derive(Debug, Clone)]
pub struct CheckpointRecord {
    pub root: String,
    pub epoch: u64,
    pub sigs: Vec<ThresholdSignature>,
    pub created_at: u64,
}

pub struct QuorumSigner {
    threshold: usize,
    sigs: Mutex<HashMap<String, Vec<ThresholdSignature>>>,
}

impl QuorumSigner {
    pub fn new(threshold: usize) -> Self {
        Self { threshold, sigs: Mutex::new(HashMap::new()) }
    }

    pub fn add_signature(&self, root: String, sig: ThresholdSignature) -> bool {
        let mut sigs = self.sigs.lock().unwrap();
        let entry = sigs.entry(root).or_default();
        entry.push(sig);
        entry.len() >= self.threshold
    }

    pub fn get_signatures(&self, root: &str) -> Vec<ThresholdSignature> {
        self.sigs.lock().unwrap().get(root).cloned().unwrap_or_default()
    }
}

pub struct CheckpointDatabase {
    records: Mutex<Vec<CheckpointRecord>>,
}

impl CheckpointDatabase {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { records: Mutex::new(vec![]) })
    }

    pub fn store(&self, record: CheckpointRecord) {
        self.records.lock().unwrap().push(record);
    }

    pub fn latest(&self) -> Option<CheckpointRecord> {
        self.records.lock().unwrap().last().cloned()
    }

    pub fn get_by_epoch(&self, epoch: u64) -> Option<CheckpointRecord> {
        self.records.lock().unwrap().iter().find(|r| r.epoch == epoch).cloned()
    }
}

pub struct RelayConsumer {
    seen: Mutex<std::collections::HashSet<String>>,
    callbacks: Mutex<Vec<Box<dyn Fn(Event) + Send + Sync>>>,
}

impl RelayConsumer {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            seen: Mutex::new(std::collections::HashSet::new()),
            callbacks: Mutex::new(vec![]),
        })
    }

    pub fn on_event<F>(&self, f: F)
    where
        F: Fn(Event) + Send + Sync + 'static,
    {
        self.callbacks.lock().unwrap().push(Box::new(f));
    }

    pub fn ingest(&self, event: Event) {
        {
            let mut seen = self.seen.lock().unwrap();
            if seen.contains(&event.id) {
                return;
            }
            seen.insert(event.id.clone());
        }
        let callbacks = self.callbacks.lock().unwrap();
        for cb in callbacks.iter() {
            cb(event.clone());
        }
    }
}
