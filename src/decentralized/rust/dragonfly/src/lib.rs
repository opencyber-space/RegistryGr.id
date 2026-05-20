use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

fn now_secs() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

#[derive(Debug, Clone)]
pub struct Chunk {
    pub content_id: String,
    pub index: usize,
    pub data: Vec<u8>,
    pub hash: String,
}

pub struct OriginFetcher {
    gateway_url: String,
}

impl OriginFetcher {
    pub fn new(gateway_url: String) -> Self {
        Self { gateway_url }
    }

    pub fn fetch_range(&self, asset_id: &str, start: usize, end: usize) -> Result<Vec<u8>, String> {
        let _url = format!("{}/object/{}", self.gateway_url, asset_id);
        let _range = format!("bytes={}-{}", start, end);
        Ok(vec![])
    }
}

pub struct DiskCache {
    store: RwLock<HashMap<String, Vec<u8>>>,
    max_size: usize,
    used: Mutex<usize>,
}

impl DiskCache {
    pub fn new(max_size: usize) -> Arc<Self> {
        Arc::new(Self {
            store: RwLock::new(HashMap::new()),
            max_size,
            used: Mutex::new(0),
        })
    }

    pub fn store_data(&self, key: &str, data: Vec<u8>) {
        let len = data.len();
        {
            let used = *self.used.lock().unwrap();
            if used + len > self.max_size {
                self.evict(len);
            }
        }
        self.store.write().unwrap().insert(key.to_string(), data);
        *self.used.lock().unwrap() += len;
    }

    pub fn get(&self, key: &str) -> Option<Vec<u8>> {
        self.store.read().unwrap().get(key).cloned()
    }

    pub fn evict_key(&self, key: &str) {
        if let Some(data) = self.store.write().unwrap().remove(key) {
            *self.used.lock().unwrap() -= data.len();
        }
    }

    fn evict(&self, needed: usize) {
        let mut store = self.store.write().unwrap();
        let mut used = self.used.lock().unwrap();
        let mut freed = 0;
        let keys: Vec<String> = store.keys().cloned().collect();
        for k in keys {
            if freed >= needed { break; }
            if let Some(data) = store.remove(&k) {
                freed += data.len();
                *used -= data.len();
            }
        }
    }
}

pub struct PieceServer {
    cache: Arc<DiskCache>,
}

impl PieceServer {
    pub fn new(cache: Arc<DiskCache>) -> Self {
        Self { cache }
    }

    pub fn serve(&self, key: &str) -> Option<Vec<u8>> {
        self.cache.get(key)
    }
}

pub struct CacheGarbageCollector {
    cache: Arc<DiskCache>,
    interval: Duration,
    max_size: usize,
}

impl CacheGarbageCollector {
    pub fn new(cache: Arc<DiskCache>, interval: Duration, max_size: usize) -> Self {
        Self { cache, interval, max_size }
    }

    pub fn run(&self) {
        loop {
            thread::sleep(self.interval);
            self.collect();
        }
    }

    fn collect(&self) {
        let used = *self.cache.used.lock().unwrap();
        if used <= self.max_size { return; }
        let excess = used - self.max_size;
        let keys: Vec<String> = self.cache.store.read().unwrap().keys().cloned().collect();
        let mut freed = 0;
        for k in keys {
            if freed >= excess { break; }
            if let Some(data) = self.cache.store.write().unwrap().remove(&k) {
                freed += data.len();
                *self.cache.used.lock().unwrap() -= data.len();
            }
        }
    }
}

pub struct IntegrityVerifier;

impl IntegrityVerifier {
    pub fn new() -> Self { Self }

    pub fn verify(&self, chunk: &Chunk) -> bool {
        hex::encode(Sha256::digest(&chunk.data)) == chunk.hash
    }
}

pub struct LocalCache {
    store: RwLock<HashMap<String, Chunk>>,
}

impl LocalCache {
    pub fn new() -> Arc<Self> {
        Arc::new(Self { store: RwLock::new(HashMap::new()) })
    }

    pub fn write(&self, chunk: Chunk) {
        let key = format!("{}:{}", chunk.content_id, chunk.index);
        self.store.write().unwrap().insert(key, chunk);
    }

    pub fn read(&self, content_id: &str, index: usize) -> Option<Chunk> {
        let key = format!("{}:{}", content_id, index);
        self.store.read().unwrap().get(&key).cloned()
    }
}

pub trait PeerSource: Send + Sync {
    fn fetch_chunk(&self, content_id: &str, index: usize) -> Result<Chunk, String>;
}

pub struct PieceDownloader {
    peers: Vec<Arc<dyn PeerSource>>,
    verifier: IntegrityVerifier,
    local_cache: Arc<LocalCache>,
}

impl PieceDownloader {
    pub fn new(peers: Vec<Arc<dyn PeerSource>>, verifier: IntegrityVerifier, local_cache: Arc<LocalCache>) -> Arc<Self> {
        Arc::new(Self { peers, verifier, local_cache })
    }

    pub fn download(&self, content_id: &str, index: usize) -> Result<Chunk, String> {
        if let Some(chunk) = self.local_cache.read(content_id, index) {
            return Ok(chunk);
        }
        for peer in &self.peers {
            if let Ok(chunk) = peer.fetch_chunk(content_id, index) {
                if self.verifier.verify(&chunk) {
                    self.local_cache.write(chunk.clone());
                    return Ok(chunk);
                }
            }
        }
        Err(format!("no peer could serve {}:{}", content_id, index))
    }
}

pub trait PeerSink: Send + Sync {
    fn send_chunk(&self, chunk: Chunk) -> Result<(), String>;
    fn id(&self) -> String;
}

pub struct PieceUploader {
    peers: Vec<Arc<dyn PeerSink>>,
}

impl PieceUploader {
    pub fn new(peers: Vec<Arc<dyn PeerSink>>) -> Self {
        Self { peers }
    }

    pub fn redistribute(&self, chunk: Chunk) {
        for peer in &self.peers {
            let p = Arc::clone(peer);
            let c = chunk.clone();
            thread::spawn(move || { let _ = p.send_chunk(c); });
        }
    }
}

pub struct RetryEngine {
    downloader: Arc<PieceDownloader>,
    max_retries: usize,
    backoff: Duration,
}

impl RetryEngine {
    pub fn new(downloader: Arc<PieceDownloader>, max_retries: usize, backoff: Duration) -> Self {
        Self { downloader, max_retries, backoff }
    }

    pub fn download(&self, content_id: &str, index: usize) -> Result<Chunk, String> {
        let mut last_err = String::new();
        for i in 0..self.max_retries {
            match self.downloader.download(content_id, index) {
                Ok(chunk) => return Ok(chunk),
                Err(e) => {
                    last_err = e;
                    thread::sleep(self.backoff * (i as u32 + 1));
                }
            }
        }
        Err(format!("max retries exceeded: {}", last_err))
    }
}
