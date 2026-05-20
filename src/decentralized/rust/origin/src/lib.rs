use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
pub struct ObjectMeta {
    pub asset_id: String,
    pub checksum: String,
    pub byte_size: usize,
    pub modified_at: u64,
    pub verified: bool,
}

pub struct MetadataDatabase {
    records: RwLock<HashMap<String, ObjectMeta>>,
}

impl MetadataDatabase {
    pub fn new() -> Arc<Self> {
        Arc::new(Self {
            records: RwLock::new(HashMap::new()),
        })
    }

    pub fn record(&self, asset_id: &str, data: &[u8]) {
        let checksum = hex::encode(Sha256::digest(data));
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        let meta = ObjectMeta {
            asset_id: asset_id.to_string(),
            checksum,
            byte_size: data.len(),
            modified_at: now,
            verified: true,
        };
        self.records.write().unwrap().insert(asset_id.to_string(), meta);
    }

    pub fn get(&self, asset_id: &str) -> Option<ObjectMeta> {
        self.records.read().unwrap().get(asset_id).cloned()
    }

    pub fn verify(&self, asset_id: &str, data: &[u8]) -> bool {
        match self.get(asset_id) {
            Some(meta) => hex::encode(Sha256::digest(data)) == meta.checksum,
            None => false,
        }
    }
}

pub struct ObjectGateway {
    objects: RwLock<HashMap<String, Vec<u8>>>,
    meta_db: Arc<MetadataDatabase>,
}

impl ObjectGateway {
    pub fn new(meta_db: Arc<MetadataDatabase>) -> Arc<Self> {
        Arc::new(Self {
            objects: RwLock::new(HashMap::new()),
            meta_db,
        })
    }

    pub fn store(&self, asset_id: &str, data: Vec<u8>) {
        self.meta_db.record(asset_id, &data);
        self.objects.write().unwrap().insert(asset_id.to_string(), data);
    }

    pub fn get(&self, asset_id: &str) -> Option<Vec<u8>> {
        self.objects.read().unwrap().get(asset_id).cloned()
    }

    pub fn serve_range(&self, asset_id: &str, start: usize, end: usize) -> Option<Vec<u8>> {
        self.get(asset_id).map(|data| data[start..=end].to_vec())
    }

    pub fn commit(&self, asset_id: &str) -> Result<(), String> {
        if self.get(asset_id).is_some() {
            Ok(())
        } else {
            Err(format!("asset {} not found", asset_id))
        }
    }
}

pub struct OriginUploader {
    gateway_url: String,
    chunk_size: usize,
}

impl OriginUploader {
    pub fn new(gateway_url: String) -> Self {
        Self {
            gateway_url,
            chunk_size: 4 * 1024 * 1024,
        }
    }

    pub fn upload(&self, data: &[u8], asset_id: &str) -> Result<(), String> {
        let total = data.len();
        let mut offset = 0;
        while offset < total {
            let end = (offset + self.chunk_size).min(total);
            let chunk = &data[offset..end];
            self.upload_chunk(asset_id, offset, total - 1, chunk)?;
            offset = end;
        }
        self.commit_upload(asset_id)
    }

    fn upload_chunk(&self, asset_id: &str, start: usize, end: usize, _data: &[u8]) -> Result<(), String> {
        let _url = format!("{}/upload/{}", self.gateway_url, asset_id);
        let _range = format!("bytes={}-{}/*", start, end);
        Ok(())
    }

    fn commit_upload(&self, asset_id: &str) -> Result<(), String> {
        let _url = format!("{}/upload/{}/commit", self.gateway_url, asset_id);
        Ok(())
    }
}
