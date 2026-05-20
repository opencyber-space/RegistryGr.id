use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

#[derive(Debug, Clone)]
pub struct ProbeResult {
    pub indexer_id: String,
    pub query: String,
    pub latency_ms: u64,
    pub issued_at: u64,
    pub consistent: bool,
}

pub struct EvidenceStore {
    transcripts: Mutex<Vec<ProbeResult>>,
}

impl EvidenceStore {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { transcripts: Mutex::new(vec![]) })
    }

    pub fn record_transcript(&self, result: ProbeResult) {
        self.transcripts.lock().unwrap().push(result);
    }

    pub fn get_transcripts(&self, indexer_id: &str) -> Vec<ProbeResult> {
        self.transcripts
            .lock()
            .unwrap()
            .iter()
            .filter(|t| t.indexer_id == indexer_id)
            .cloned()
            .collect()
    }
}

pub trait L2Indexer: Send + Sync {
    fn query(&self, req: &str) -> Result<String, String>;
    fn id(&self) -> String;
}

pub struct L2ProbeEngine {
    indexers: Vec<Arc<dyn L2Indexer>>,
    evidence_store: Arc<EvidenceStore>,
    interval: Duration,
}

impl L2ProbeEngine {
    pub fn new(indexers: Vec<Arc<dyn L2Indexer>>, evidence_store: Arc<EvidenceStore>, interval: Duration) -> Self {
        Self { indexers, evidence_store, interval }
    }

    pub fn run(&self) {
        loop {
            thread::sleep(self.interval);
            self.probe();
        }
    }

    fn probe(&self) {
        if self.indexers.is_empty() { return; }
        let selected = &self.indexers[0];
        let queries = ["list_assets", "get_manifest", "query_by_tag"];
        let query = queries[now_secs() as usize % queries.len()];
        let start = now_secs();
        let (consistent, _resp) = match selected.query(query) {
            Ok(r) => (true, r),
            Err(_) => (false, String::new()),
        };
        let latency_ms = (now_secs() - start) * 1000;
        self.evidence_store.record_transcript(ProbeResult {
            indexer_id: selected.id(),
            query: query.to_string(),
            latency_ms,
            issued_at: start,
            consistent,
        });
    }
}

#[derive(Debug, Clone)]
pub struct L1Event {
    pub id: String,
    pub kind: u32,
    pub pubkey: String,
    pub created_at: u64,
    pub content: String,
}

pub struct GroundTruthDatabase {
    events: Mutex<Vec<L1Event>>,
    by_author: Mutex<HashMap<String, Vec<L1Event>>>,
    by_asset: Mutex<HashMap<String, Vec<L1Event>>>,
}

impl GroundTruthDatabase {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            events: Mutex::new(vec![]),
            by_author: Mutex::new(HashMap::new()),
            by_asset: Mutex::new(HashMap::new()),
        })
    }

    pub fn ingest(&self, event: L1Event) {
        self.by_author.lock().unwrap().entry(event.pubkey.clone()).or_default().push(event.clone());
        self.by_asset.lock().unwrap().entry(event.id.clone()).or_default().push(event.clone());
        self.events.lock().unwrap().push(event);
    }

    pub fn get_author_timeline(&self, pubkey: &str) -> Vec<L1Event> {
        self.by_author.lock().unwrap().get(pubkey).cloned().unwrap_or_default()
    }

    pub fn get_asset_history(&self, asset_id: &str) -> Vec<L1Event> {
        self.by_asset.lock().unwrap().get(asset_id).cloned().unwrap_or_default()
    }
}

pub trait L1RelaySource: Send + Sync {
    fn fetch_events(&self, since: u64) -> Result<Vec<L1Event>, String>;
}

pub struct L1Scanner {
    relays: Vec<Arc<dyn L1RelaySource>>,
    ground_truth: Arc<GroundTruthDatabase>,
    interval: Duration,
}

impl L1Scanner {
    pub fn new(relays: Vec<Arc<dyn L1RelaySource>>, ground_truth: Arc<GroundTruthDatabase>, interval: Duration) -> Self {
        Self { relays, ground_truth, interval }
    }

    pub fn run(&self) {
        let mut last_scan = now_secs();
        loop {
            thread::sleep(self.interval);
            for relay in &self.relays {
                if let Ok(events) = relay.fetch_events(last_scan) {
                    for e in events {
                        self.ground_truth.ingest(e);
                    }
                }
            }
            last_scan = now_secs();
        }
    }
}

#[derive(Debug, Clone)]
pub struct Verdict {
    pub indexer_id: String,
    pub omissions: Vec<String>,
    pub censored: Vec<String>,
    pub equivocal: Vec<String>,
    pub issued_at: u64,
}

pub struct Comparator {
    ground_truth: Arc<GroundTruthDatabase>,
    evidence_store: Arc<EvidenceStore>,
}

impl Comparator {
    pub fn new(ground_truth: Arc<GroundTruthDatabase>, evidence_store: Arc<EvidenceStore>) -> Self {
        Self { ground_truth, evidence_store }
    }

    pub fn analyze(&self, indexer_id: &str) -> Verdict {
        let transcripts = self.evidence_store.get_transcripts(indexer_id);
        let omissions: Vec<String> = transcripts
            .iter()
            .filter(|t| !t.consistent)
            .map(|t| t.query.clone())
            .collect();
        Verdict {
            indexer_id: indexer_id.to_string(),
            omissions,
            censored: vec![],
            equivocal: vec![],
            issued_at: now_secs(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct AuditReport {
    pub watchdog_key: String,
    pub verdicts: Vec<Verdict>,
    pub merkle_root: String,
    pub sig: String,
    pub issued_at: u64,
}

pub struct ReportSigner {
    identity_key: Vec<u8>,
}

impl ReportSigner {
    pub fn new(identity_key: Vec<u8>) -> Self {
        Self { identity_key }
    }

    pub fn sign(&self, verdicts: Vec<Verdict>) -> AuditReport {
        let data: String = verdicts.iter().map(|v| v.indexer_id.clone()).collect::<Vec<_>>().join(",");
        let mut payload = data.into_bytes();
        payload.extend_from_slice(&self.identity_key);
        let sig = hex::encode(Sha256::digest(&payload));
        let root = hex::encode(Sha256::digest(sig.as_bytes()));
        AuditReport {
            watchdog_key: hex::encode(Sha256::digest(&self.identity_key)),
            verdicts,
            merkle_root: root,
            sig,
            issued_at: now_secs(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct ReputationScore {
    pub indexer_id: String,
    pub score: f64,
    pub evidence: Vec<String>,
    pub published_at: u64,
}

pub trait NostrEventPublisher: Send + Sync {
    fn publish(&self, content: &str) -> Result<(), String>;
}

pub struct ReputationEventPublisher {
    publisher: Arc<dyn NostrEventPublisher>,
}

impl ReputationEventPublisher {
    pub fn new(publisher: Arc<dyn NostrEventPublisher>) -> Self {
        Self { publisher }
    }

    pub fn publish(&self, score: &ReputationScore) -> Result<(), String> {
        let content = format!("{{\"indexer_id\":\"{}\",\"score\":{}}}", score.indexer_id, score.score);
        self.publisher.publish(&content)
    }
}
