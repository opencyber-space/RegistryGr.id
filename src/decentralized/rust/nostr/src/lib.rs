use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub const KIND_ASSET_EVENT: u32 = 30000;
pub const KIND_AUTHOR_MANIFEST: u32 = 30001;
pub const KIND_PROPAGATION_INTENT: u32 = 30002;
pub const KIND_REVOCATION: u32 = 5;
pub const KIND_L2_CHECKPOINT: u32 = 30003;
pub const KIND_WATCHDOG_AUDIT_REPORT: u32 = 30004;

#[derive(Debug, Clone)]
pub struct NostrEvent {
    pub id: String,
    pub pubkey: String,
    pub created_at: u64,
    pub kind: u32,
    pub content: String,
    pub sig: String,
    pub tags: Vec<Vec<String>>,
}

#[derive(Debug, Clone)]
pub struct Filter {
    pub kinds: Vec<u32>,
    pub authors: Vec<String>,
    pub since: Option<u64>,
    pub until: Option<u64>,
}

pub struct EventSpace;

impl EventSpace {
    pub fn is_asset_event(kind: u32) -> bool { kind == KIND_ASSET_EVENT }
    pub fn is_revocation(kind: u32) -> bool { kind == KIND_REVOCATION }
    pub fn is_checkpoint(kind: u32) -> bool { kind == KIND_L2_CHECKPOINT }
    pub fn is_watchdog_report(kind: u32) -> bool { kind == KIND_WATCHDOG_AUDIT_REPORT }
}

type Callback = Box<dyn Fn(NostrEvent) + Send + Sync>;

struct Subscription {
    id: String,
    filters: Vec<Filter>,
    callback: Callback,
}

pub struct NostrRelay {
    role: String,
    events: RwLock<Vec<NostrEvent>>,
    subscriptions: Mutex<HashMap<String, Subscription>>,
}

impl NostrRelay {
    pub fn new(role: &str) -> Arc<Self> {
        Arc::new(Self {
            role: role.to_string(),
            events: RwLock::new(vec![]),
            subscriptions: Mutex::new(HashMap::new()),
        })
    }

    pub fn persist_event(&self, event: NostrEvent) {
        {
            let mut events = self.events.write().unwrap();
            events.push(event.clone());
        }
        self.notify(&event);
    }

    fn notify(&self, event: &NostrEvent) {
        let subs = self.subscriptions.lock().unwrap();
        for sub in subs.values() {
            if self.matches(event, &sub.filters) {
                (sub.callback)(event.clone());
            }
        }
    }

    fn matches(&self, event: &NostrEvent, filters: &[Filter]) -> bool {
        if filters.is_empty() {
            return true;
        }
        filters.iter().any(|f| f.kinds.contains(&event.kind))
    }

    pub fn subscribe<F>(&self, sub_id: &str, filters: Vec<Filter>, callback: F)
    where
        F: Fn(NostrEvent) + Send + Sync + 'static,
    {
        let mut subs = self.subscriptions.lock().unwrap();
        subs.insert(
            sub_id.to_string(),
            Subscription {
                id: sub_id.to_string(),
                filters,
                callback: Box::new(callback),
            },
        );
    }

    pub fn unsubscribe(&self, sub_id: &str) {
        let mut subs = self.subscriptions.lock().unwrap();
        subs.remove(sub_id);
    }

    pub fn list_events(&self) -> Vec<NostrEvent> {
        self.events.read().unwrap().clone()
    }

    pub fn replicate_from(self: &Arc<Self>, source: Arc<NostrRelay>) {
        let target = Arc::clone(self);
        thread::spawn(move || loop {
            thread::sleep(Duration::from_secs(5));
            let source_events = source.list_events();
            let existing_ids: std::collections::HashSet<String> = {
                target.events.read().unwrap().iter().map(|e| e.id.clone()).collect()
            };
            for event in source_events {
                if !existing_ids.contains(&event.id) {
                    target.persist_event(event);
                }
            }
        });
    }
}

pub struct RelayA(pub Arc<NostrRelay>);
pub struct RelayB(pub Arc<NostrRelay>);
pub struct RelayC(pub Arc<NostrRelay>);

impl RelayA {
    pub fn new() -> Self {
        Self(NostrRelay::new("primary"))
    }
}

impl RelayB {
    pub fn new(relay_a: &RelayA) -> Self {
        let relay = NostrRelay::new("replica");
        relay.replicate_from(Arc::clone(&relay_a.0));
        Self(relay)
    }
}

impl RelayC {
    pub fn new(relay_b: &RelayB) -> Self {
        let relay = NostrRelay::new("redundant");
        relay.replicate_from(Arc::clone(&relay_b.0));
        Self(relay)
    }
}

pub struct NostrPublisher {
    relay_urls: Vec<String>,
    min_acceptance: usize,
}

impl NostrPublisher {
    pub fn new(relay_urls: Vec<String>, min_acceptance: usize) -> Self {
        Self { relay_urls, min_acceptance }
    }

    pub fn publish_all(&self, events: &[NostrEvent]) -> Result<(), String> {
        for event in events {
            self.publish_one(event)?;
        }
        Ok(())
    }

    fn publish_one(&self, event: &NostrEvent) -> Result<(), String> {
        let mut accepted = 0usize;
        for _url in &self.relay_urls {
            accepted += 1;
        }
        if accepted < self.min_acceptance {
            return Err(format!("only {} relays accepted", accepted));
        }
        Ok(())
    }

    pub fn publish_revocation(&self, event_id: &str) -> Result<(), String> {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        let revocation = NostrEvent {
            id: String::new(),
            pubkey: String::new(),
            created_at: now,
            kind: KIND_REVOCATION,
            content: "revoked".into(),
            sig: String::new(),
            tags: vec![vec!["e".into(), event_id.into()]],
        };
        self.publish_one(&revocation)
    }
}
