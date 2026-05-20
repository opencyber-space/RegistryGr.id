package aggregator

import (
	"sync"
)

type SchedulerRecord struct {
	SchedulerID string
	PeerID      string
	Tags        []string
}

type AggregatorDatabase struct {
	mu         sync.RWMutex
	assets     map[string]*AssetRecord
	manifests  map[string]string
	tagIndex   map[string][]string
	schedulers map[string]*SchedulerRecord
}

func NewAggregatorDatabase() *AggregatorDatabase {
	return &AggregatorDatabase{
		assets:     make(map[string]*AssetRecord),
		manifests:  make(map[string]string),
		tagIndex:   make(map[string][]string),
		schedulers: make(map[string]*SchedulerRecord),
	}
}

func (db *AggregatorDatabase) PersistAsset(record *AssetRecord) {
	db.mu.Lock()
	defer db.mu.Unlock()
	db.assets[record.ID] = record
	for _, tag := range record.Tags {
		db.tagIndex[tag] = append(db.tagIndex[tag], record.ID)
	}
}

func (db *AggregatorDatabase) PersistManifest(assetID, manifest string) {
	db.mu.Lock()
	db.manifests[assetID] = manifest
	db.mu.Unlock()
}

func (db *AggregatorDatabase) PersistScheduler(rec *SchedulerRecord) {
	db.mu.Lock()
	db.schedulers[rec.SchedulerID] = rec
	db.mu.Unlock()
}

func (db *AggregatorDatabase) QueryByTag(tag string) []*AssetRecord {
	db.mu.RLock()
	ids := db.tagIndex[tag]
	db.mu.RUnlock()
	var result []*AssetRecord
	db.mu.RLock()
	for _, id := range ids {
		if a, ok := db.assets[id]; ok {
			result = append(result, a)
		}
	}
	db.mu.RUnlock()
	return result
}

func (db *AggregatorDatabase) GetAsset(id string) (*AssetRecord, bool) {
	db.mu.RLock()
	defer db.mu.RUnlock()
	a, ok := db.assets[id]
	return a, ok
}

func (db *AggregatorDatabase) ListSchedulers() []*SchedulerRecord {
	db.mu.RLock()
	defer db.mu.RUnlock()
	recs := make([]*SchedulerRecord, 0, len(db.schedulers))
	for _, r := range db.schedulers {
		recs = append(recs, r)
	}
	return recs
}
