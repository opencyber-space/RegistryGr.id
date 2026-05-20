use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::sync::atomic::{AtomicI64, AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

pub struct ConsistentHashEngine {
    ring: RwLock<Vec<(u64, String)>>,
    vnodes: usize,
}

impl ConsistentHashEngine {
    pub fn new(vnodes: usize) -> Arc<Self> {
        Arc::new(Self { ring: RwLock::new(vec![]), vnodes })
    }

    pub fn add_scheduler(&self, id: &str) {
        let mut ring = self.ring.write().unwrap();
        for i in 0..self.vnodes {
            let key = format!("{}{}", id, i);
            let hash = u64::from_be_bytes(Sha256::digest(key.as_bytes())[..8].try_into().unwrap());
            ring.push((hash, id.to_string()));
        }
        ring.sort_by_key(|(h, _)| *h);
    }

    pub fn assign(&self, content_id: &str) -> Option<String> {
        let ring = self.ring.read().unwrap();
        if ring.is_empty() { return None; }
        let hash = u64::from_be_bytes(Sha256::digest(content_id.as_bytes())[..8].try_into().unwrap());
        for (h, id) in ring.iter() {
            if *h >= hash {
                return Some(id.clone());
            }
        }
        Some(ring[0].1.clone())
    }
}

#[derive(Debug, Clone)]
pub struct HealthStatus {
    pub scheduler_id: String,
    pub alive: bool,
    pub rtt_ms: u64,
    pub checked_at: u64,
}

pub trait SchedulerProber: Send + Sync {
    fn probe(&self) -> Result<u64, String>;
    fn id(&self) -> String;
}

pub struct SchedulerHealthMonitor {
    statuses: RwLock<HashMap<String, HealthStatus>>,
    probers: Mutex<Vec<Arc<dyn SchedulerProber>>>,
    interval: Duration,
}

impl SchedulerHealthMonitor {
    pub fn new(interval: Duration) -> Arc<Self> {
        Arc::new(Self {
            statuses: RwLock::new(HashMap::new()),
            probers: Mutex::new(vec![]),
            interval,
        })
    }

    pub fn add_prober(&self, prober: Arc<dyn SchedulerProber>) {
        self.probers.lock().unwrap().push(prober);
    }

    pub fn run(self: &Arc<Self>) {
        let monitor = Arc::clone(self);
        thread::spawn(move || loop {
            thread::sleep(monitor.interval);
            let probers = monitor.probers.lock().unwrap().clone();
            for prober in probers {
                let (alive, rtt) = match prober.probe() {
                    Ok(rtt) => (true, rtt),
                    Err(_) => (false, 0),
                };
                let status = HealthStatus {
                    scheduler_id: prober.id(),
                    alive,
                    rtt_ms: rtt,
                    checked_at: now_secs(),
                };
                monitor.statuses.write().unwrap().insert(prober.id(), status);
            }
        });
    }

    pub fn is_alive(&self, id: &str) -> bool {
        self.statuses.read().unwrap().get(id).map_or(false, |s| s.alive)
    }
}

pub struct DecisionCache {
    store: Mutex<HashMap<String, (String, u64)>>,
    ttl: u64,
}

impl DecisionCache {
    pub fn new(ttl: u64) -> Arc<Self> {
        Arc::new(Self { store: Mutex::new(HashMap::new()), ttl })
    }

    pub fn set(&self, content_id: &str, scheduler_id: &str) {
        let exp = now_secs() + self.ttl;
        self.store.lock().unwrap().insert(content_id.to_string(), (scheduler_id.to_string(), exp));
    }

    pub fn get(&self, content_id: &str) -> Option<String> {
        let mut store = self.store.lock().unwrap();
        match store.get(content_id) {
            Some((id, exp)) if *exp > now_secs() => Some(id.clone()),
            Some(_) => { store.remove(content_id); None }
            None => None,
        }
    }
}

pub struct Bridge {
    state: RwLock<HashMap<String, String>>,
}

impl Bridge {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { state: RwLock::new(HashMap::new()) })
    }

    pub fn update(&self, key: &str, value: &str) {
        self.state.write().unwrap().insert(key.to_string(), value.to_string());
    }

    pub fn get(&self, key: &str) -> Option<String> {
        self.state.read().unwrap().get(key).cloned()
    }
}

pub struct ManagerAPIFacade {
    hash_engine: Arc<ConsistentHashEngine>,
    decision_cache: Arc<DecisionCache>,
    health_monitor: Arc<SchedulerHealthMonitor>,
    bridge: Arc<Bridge>,
}

impl ManagerAPIFacade {
    pub fn new(
        hash_engine: Arc<ConsistentHashEngine>,
        decision_cache: Arc<DecisionCache>,
        health_monitor: Arc<SchedulerHealthMonitor>,
        bridge: Arc<Bridge>,
    ) -> Self {
        Self { hash_engine, decision_cache, health_monitor, bridge }
    }

    pub fn select_scheduler(&self, content_id: &str) -> Option<String> {
        if let Some(cached) = self.decision_cache.get(content_id) {
            if self.health_monitor.is_alive(&cached) {
                return Some(cached);
            }
        }
        let selected = self.hash_engine.assign(content_id)?;
        self.decision_cache.set(content_id, &selected);
        Some(selected)
    }

    pub fn preheat(&self, _content_id: &str) {}
    pub fn keepalive(&self, _scheduler_id: &str) {}
}

#[derive(Debug, Clone)]
pub struct TaskSpec {
    pub content_id: String,
    pub scheduler_id: String,
    pub intent: String,
    pub scope: String,
    pub ttl_secs: u64,
}

pub struct PolicyEngine;

impl PolicyEngine {
    pub fn new() -> Self { Self }

    pub fn evaluate(&self, spec: &TaskSpec) -> bool {
        spec.ttl_secs > 0 && !spec.intent.is_empty()
    }
}

#[derive(Debug, Clone)]
pub struct Task {
    pub id: String,
    pub content_id: String,
    pub scheduler_id: String,
    pub status: String,
    pub created_at: u64,
    pub expires_at: u64,
}

pub struct TaskOrchestrator {
    tasks: Mutex<HashMap<String, Task>>,
    preheat: Mutex<std::collections::HashSet<String>>,
}

impl TaskOrchestrator {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            tasks: Mutex::new(HashMap::new()),
            preheat: Mutex::new(std::collections::HashSet::new()),
        })
    }

    pub fn create_task(&self, task: Task) {
        self.tasks.lock().unwrap().insert(task.id.clone(), task);
    }

    pub fn invalidate_task(&self, id: &str) {
        if let Some(t) = self.tasks.lock().unwrap().get_mut(id) {
            t.status = "invalidated".to_string();
        }
    }

    pub fn reconcile_preheat(&self, content_id: &str) {
        self.preheat.lock().unwrap().insert(content_id.to_string());
    }

    pub fn reconcile_eviction(&self, content_id: &str) {
        self.preheat.lock().unwrap().remove(content_id);
    }
}

#[derive(Debug, Clone)]
pub struct PlacementRequest {
    pub content_id: String,
    pub peer_id: String,
    pub priority: i32,
}

#[derive(Debug, Clone)]
pub struct PlacementResponse {
    pub scheduler_id: String,
    pub peer_id: String,
}

pub struct SchedulerAPI {
    facade: Arc<ManagerAPIFacade>,
    task_manager: Arc<TaskManager>,
}

impl SchedulerAPI {
    pub fn new(facade: Arc<ManagerAPIFacade>, task_manager: Arc<TaskManager>) -> Self {
        Self { facade, task_manager }
    }

    pub fn handle_placement(&self, req: PlacementRequest) -> PlacementResponse {
        let scheduler_id = self.facade.select_scheduler(&req.content_id).unwrap_or_default();
        PlacementResponse { scheduler_id, peer_id: req.peer_id }
    }
}

#[derive(Debug, Clone)]
pub struct TaskState {
    pub id: String,
    pub content_id: String,
    pub status: String,
    pub ttl_secs: u64,
    pub created_at: u64,
}

pub struct TaskManager {
    tasks: Mutex<HashMap<String, TaskState>>,
}

impl TaskManager {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { tasks: Mutex::new(HashMap::new()) })
    }

    pub fn track(&self, task: TaskState) {
        self.tasks.lock().unwrap().insert(task.id.clone(), task);
    }

    pub fn expire(&self) {
        let now = now_secs();
        let mut tasks = self.tasks.lock().unwrap();
        tasks.retain(|_, t| now <= t.created_at + t.ttl_secs);
    }

    pub fn get(&self, id: &str) -> Option<TaskState> {
        self.tasks.lock().unwrap().get(id).cloned()
    }
}

#[derive(Debug, Clone)]
pub struct PeerEntry {
    pub id: String,
    pub addr: String,
    pub score: f64,
    pub last_seen: u64,
}

pub struct PeerManager {
    peers: RwLock<HashMap<String, PeerEntry>>,
}

impl PeerManager {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { peers: RwLock::new(HashMap::new()) })
    }

    pub fn register(&self, peer: PeerEntry) {
        self.peers.write().unwrap().insert(peer.id.clone(), peer);
    }

    pub fn update_score(&self, peer_id: &str, score: f64) {
        if let Some(p) = self.peers.write().unwrap().get_mut(peer_id) {
            p.score = score;
        }
    }

    pub fn best_peers(&self, n: usize) -> Vec<PeerEntry> {
        let mut all: Vec<PeerEntry> = self.peers.read().unwrap().values().cloned().collect();
        all.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        all.into_iter().take(n).collect()
    }
}

#[derive(Debug, Clone)]
pub struct PieceEntry {
    pub content_id: String,
    pub chunk_idx: usize,
    pub hash: String,
    pub available: bool,
    pub peer_ids: Vec<String>,
}

pub struct PieceManager {
    pieces: RwLock<HashMap<String, PieceEntry>>,
}

impl PieceManager {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { pieces: RwLock::new(HashMap::new()) })
    }

    pub fn register(&self, piece: PieceEntry) {
        let key = format!("{}:{}", piece.content_id, piece.chunk_idx);
        self.pieces.write().unwrap().insert(key, piece);
    }

    pub fn validate_checksum(&self, content_id: &str, idx: usize, expected: &str) -> bool {
        let key = format!("{}:{}", content_id, idx);
        self.pieces.read().unwrap().get(&key).map_or(false, |p| p.hash == expected)
    }
}

pub struct TopologyBuilder {
    fan_out: usize,
}

impl TopologyBuilder {
    pub fn new(fan_out: usize) -> Self { Self { fan_out } }

    pub fn build(&self, peer_ids: &[String]) -> HashMap<String, Vec<String>> {
        let mut tree: HashMap<String, Vec<String>> = peer_ids.iter().map(|id| (id.clone(), vec![])).collect();
        for (i, id) in peer_ids.iter().enumerate() {
            let start = i * self.fan_out + 1;
            let end = (start + self.fan_out).min(peer_ids.len());
            tree.get_mut(id).unwrap().extend(peer_ids[start..end].iter().cloned());
        }
        tree
    }
}

pub struct LoadController {
    limits: RwLock<HashMap<String, u64>>,
    counters: RwLock<HashMap<String, AtomicU64>>,
}

impl LoadController {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            limits: RwLock::new(HashMap::new()),
            counters: RwLock::new(HashMap::new()),
        })
    }

    pub fn set_limit(&self, peer_id: &str, limit: u64) {
        self.limits.write().unwrap().insert(peer_id.to_string(), limit);
        self.counters.write().unwrap().insert(peer_id.to_string(), AtomicU64::new(0));
    }

    pub fn allow(&self, peer_id: &str) -> bool {
        let limits = self.limits.read().unwrap();
        let limit = match limits.get(peer_id) {
            Some(l) => *l,
            None => return true,
        };
        let counters = self.counters.read().unwrap();
        match counters.get(peer_id) {
            Some(c) => {
                let current = c.load(Ordering::SeqCst);
                if current >= limit { false } else { c.fetch_add(1, Ordering::SeqCst); true }
            }
            None => true,
        }
    }
}

pub struct FailureHandler {
    task_manager: Arc<TaskManager>,
    peer_manager: Arc<PeerManager>,
}

impl FailureHandler {
    pub fn new(task_manager: Arc<TaskManager>, peer_manager: Arc<PeerManager>) -> Self {
        Self { task_manager, peer_manager }
    }

    pub fn handle(&self, task_id: &str, _error: &str) {
        if let Some(mut task) = self.task_manager.get(task_id) {
            task.status = "failed".to_string();
            self.task_manager.track(task);
        }
    }

    pub fn repair_distribution(&self, _content_id: &str) -> Result<(), String> {
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct MetricsSnapshot {
    pub latency_us: u64,
    pub throughput_bytes: u64,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub timestamp: u64,
}

pub struct MetricsExporter {
    latency: AtomicU64,
    hits: AtomicU64,
    misses: AtomicU64,
    bytes: AtomicU64,
    snapshots: Mutex<Vec<MetricsSnapshot>>,
}

impl MetricsExporter {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            latency: AtomicU64::new(0),
            hits: AtomicU64::new(0),
            misses: AtomicU64::new(0),
            bytes: AtomicU64::new(0),
            snapshots: Mutex::new(vec![]),
        })
    }

    pub fn record_latency(&self, us: u64) { self.latency.store(us, Ordering::SeqCst); }
    pub fn record_cache_hit(&self) { self.hits.fetch_add(1, Ordering::SeqCst); }
    pub fn record_cache_miss(&self) { self.misses.fetch_add(1, Ordering::SeqCst); }
    pub fn record_bytes(&self, n: u64) { self.bytes.fetch_add(n, Ordering::SeqCst); }

    pub fn snapshot(&self) -> MetricsSnapshot {
        MetricsSnapshot {
            latency_us: self.latency.load(Ordering::SeqCst),
            throughput_bytes: self.bytes.load(Ordering::SeqCst),
            cache_hits: self.hits.load(Ordering::SeqCst),
            cache_misses: self.misses.load(Ordering::SeqCst),
            timestamp: now_secs(),
        }
    }

    pub fn publish(&self) {
        let snap = self.snapshot();
        self.snapshots.lock().unwrap().push(snap);
    }
}
