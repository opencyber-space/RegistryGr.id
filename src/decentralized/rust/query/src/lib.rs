use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

#[derive(Debug, Clone)]
pub struct QueryRequest {
    pub asset_id: Option<String>,
    pub tags: Vec<String>,
    pub author_id: Option<String>,
    pub limit: usize,
}

impl Default for QueryRequest {
    fn default() -> Self {
        Self { asset_id: None, tags: vec![], author_id: None, limit: 50 }
    }
}

#[derive(Debug, Clone)]
pub struct AssetResult {
    pub id: String,
    pub manifest: String,
    pub version: u64,
}

#[derive(Debug, Clone)]
pub struct QueryResponse {
    pub assets: Vec<AssetResult>,
    pub merkle_proof: Vec<String>,
    pub signature: String,
    pub transcript: String,
}

impl Default for QueryResponse {
    fn default() -> Self {
        Self { assets: vec![], merkle_proof: vec![], signature: String::new(), transcript: String::new() }
    }
}

pub trait AssetStore: Send + Sync {
    fn get_asset(&self, id: &str) -> Option<AssetResult>;
    fn query_by_tag(&self, tag: &str) -> Vec<AssetResult>;
    fn list_assets(&self) -> Vec<AssetResult>;
}

pub trait Cache: Send + Sync {
    fn get(&self, key: &str) -> Option<QueryResponse>;
    fn set(&self, key: &str, value: QueryResponse);
}

pub struct QueryAPI {
    store: Arc<dyn AssetStore>,
    cache: Arc<dyn Cache>,
    signing_key: Vec<u8>,
}

impl QueryAPI {
    pub fn new(store: Arc<dyn AssetStore>, cache: Arc<dyn Cache>, signing_key: Vec<u8>) -> Self {
        Self { store, cache, signing_key }
    }

    pub fn execute(&self, req: QueryRequest) -> QueryResponse {
        let cache_key = self.cache_key(&req);
        if let Some(cached) = self.cache.get(&cache_key) {
            return cached;
        }
        let mut results = vec![];
        if let Some(id) = &req.asset_id {
            if let Some(asset) = self.store.get_asset(id) {
                results.push(asset);
            }
        }
        for tag in &req.tags {
            results.extend(self.store.query_by_tag(tag));
        }
        let mut resp = QueryResponse {
            assets: results,
            transcript: format!("{{\"ts\":{}}}", now_secs()),
            ..Default::default()
        };
        resp.signature = self.sign_response(&resp);
        self.cache.set(&cache_key, resp.clone());
        resp
    }

    fn sign_response(&self, resp: &QueryResponse) -> String {
        let data: String = resp.assets.iter().map(|a| a.id.clone()).collect();
        let mut payload = data.into_bytes();
        payload.extend_from_slice(&self.signing_key);
        hex::encode(Sha256::digest(&payload))
    }

    fn cache_key(&self, req: &QueryRequest) -> String {
        let data = format!("{:?}", req.asset_id);
        hex::encode(Sha256::digest(data.as_bytes()))
    }
}

pub trait Indexer: Send + Sync {
    fn query(&self, req: QueryRequest) -> QueryResponse;
    fn id(&self) -> String;
}

pub struct Resolver {
    indexers: RwLock<Vec<Arc<dyn Indexer>>>,
}

impl Resolver {
    pub fn new(indexers: Vec<Arc<dyn Indexer>>) -> Self {
        Self { indexers: RwLock::new(indexers) }
    }

    pub fn select_quorum(&self, _req: &QueryRequest) -> Vec<Arc<dyn Indexer>> {
        let all = self.indexers.read().unwrap();
        let quorum_size = (all.len() / 2) + 1;
        all.iter().take(quorum_size).cloned().collect()
    }

    pub fn add_indexer(&self, indexer: Arc<dyn Indexer>) {
        self.indexers.write().unwrap().push(indexer);
    }
}

pub struct Verifier;

impl Verifier {
    pub fn new() -> Self { Self }

    pub fn verify_author_signature(&self, resp: &QueryResponse, _pub_key: &str) -> bool {
        !resp.signature.is_empty()
    }

    pub fn verify_merkle_proof(&self, asset_id: &str, proof: &[String], root: &str) -> bool {
        if proof.is_empty() { return false; }
        let mut current = asset_id.to_string();
        for sibling in proof {
            let combined = format!("{}{}", current, sibling);
            current = hex::encode(Sha256::digest(combined.as_bytes()));
        }
        current == root
    }

    pub fn verify_l2_signature(&self, resp: &QueryResponse, _checkpoint_root: &str) -> bool {
        !resp.signature.is_empty()
    }

    pub fn verify_all(&self, resp: &QueryResponse, pub_key: &str, checkpoint_root: &str) -> bool {
        if !self.verify_author_signature(resp, pub_key) { return false; }
        if !checkpoint_root.is_empty() && !resp.merkle_proof.is_empty() {
            for asset in &resp.assets {
                if !self.verify_merkle_proof(&asset.id, &resp.merkle_proof, checkpoint_root) {
                    return false;
                }
            }
        }
        self.verify_l2_signature(resp, checkpoint_root)
    }
}

pub struct ResultUnion;

impl ResultUnion {
    pub fn new() -> Self { Self }

    pub fn merge(&self, responses: Vec<QueryResponse>) -> QueryResponse {
        let mut seen: HashMap<String, AssetResult> = HashMap::new();
        for resp in responses {
            for asset in resp.assets {
                let entry = seen.entry(asset.id.clone()).or_insert_with(|| asset.clone());
                if asset.version > entry.version {
                    *entry = asset;
                }
            }
        }
        let mut merged: Vec<AssetResult> = seen.into_values().collect();
        merged.sort_by(|a, b| b.version.cmp(&a.version));
        QueryResponse { assets: merged, ..Default::default() }
    }
}

#[derive(Debug, Clone)]
pub struct WatchdogReport {
    pub indexer_id: String,
    pub score: f64,
    pub issued_at: u64,
}

pub struct ReputationFilter {
    decay_rate: f64,
    reports: Mutex<HashMap<String, Vec<WatchdogReport>>>,
}

impl ReputationFilter {
    pub fn new(decay_rate: f64) -> Self {
        Self { decay_rate, reports: Mutex::new(HashMap::new()) }
    }

    pub fn add_report(&self, report: WatchdogReport) {
        self.reports.lock().unwrap().entry(report.indexer_id.clone()).or_default().push(report);
    }

    pub fn score(&self, indexer_id: &str) -> f64 {
        let reports = self.reports.lock().unwrap();
        let rs = match reports.get(indexer_id) {
            Some(r) if !r.is_empty() => r.clone(),
            _ => return 1.0,
        };
        let now = now_secs() as f64;
        let (mut ws, mut wt) = (0.0f64, 0.0f64);
        for r in &rs {
            let age = (now - r.issued_at as f64) / 3600.0;
            let w = (-self.decay_rate * age).exp();
            ws += r.score * w;
            wt += w;
        }
        if wt == 0.0 { 1.0 } else { ws / wt }
    }

    pub fn filter(&self, assets: Vec<AssetResult>, _min_score: f64) -> Vec<AssetResult> {
        assets
    }
}

pub trait L1RelayReader: Send + Sync {
    fn query(&self, req: QueryRequest) -> Result<QueryResponse, String>;
}

pub struct FallbackReader {
    l1_relays: Vec<Arc<dyn L1RelayReader>>,
}

impl FallbackReader {
    pub fn new(l1_relays: Vec<Arc<dyn L1RelayReader>>) -> Self {
        Self { l1_relays }
    }

    pub fn read(&self, req: QueryRequest) -> Result<QueryResponse, String> {
        let mut last_err = String::from("no relays");
        for relay in &self.l1_relays {
            match relay.query(req.clone()) {
                Ok(resp) => return Ok(resp),
                Err(e) => last_err = e,
            }
        }
        Err(last_err)
    }
}
