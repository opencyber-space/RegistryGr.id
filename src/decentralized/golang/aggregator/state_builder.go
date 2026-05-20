package aggregator

import (
	"sort"
	"sync"
	"time"
)

type AssetRecord struct {
	ID        string
	AuthorKey string
	Manifest  string
	Version   uint64
	Tags      []string
	Deleted   bool
	DeletedAt *time.Time
	UpdatedAt time.Time
}

type StateBuilder struct {
	mu      sync.RWMutex
	assets  map[string]*AssetRecord
	wal     *WriteAheadLog
}

func NewStateBuilder(wal *WriteAheadLog) *StateBuilder {
	return &StateBuilder{
		assets: make(map[string]*AssetRecord),
		wal:    wal,
	}
}

func (sb *StateBuilder) Apply(event Event) {
	sb.wal.Log(event)
	sb.mu.Lock()
	defer sb.mu.Unlock()
	switch event.Kind {
	case 30000:
		sb.applyAsset(event)
	case 5:
		sb.applyDeletion(event)
	}
}

func (sb *StateBuilder) applyAsset(event Event) {
	existing, ok := sb.assets[event.ID]
	if ok && existing.Version >= uint64(event.CreatedAt) {
		return
	}
	sb.assets[event.ID] = &AssetRecord{
		ID:        event.ID,
		AuthorKey: event.PubKey,
		Manifest:  event.Content,
		Version:   uint64(event.CreatedAt),
		UpdatedAt: time.Now().UTC(),
	}
}

func (sb *StateBuilder) applyDeletion(event Event) {
	for _, tag := range extractETags(event) {
		if record, ok := sb.assets[tag]; ok {
			now := time.Now().UTC()
			record.Deleted = true
			record.DeletedAt = &now
		}
	}
}

func (sb *StateBuilder) GetAsset(id string) (*AssetRecord, bool) {
	sb.mu.RLock()
	defer sb.mu.RUnlock()
	r, ok := sb.assets[id]
	return r, ok
}

func (sb *StateBuilder) ListAssets() []*AssetRecord {
	sb.mu.RLock()
	defer sb.mu.RUnlock()
	records := make([]*AssetRecord, 0, len(sb.assets))
	for _, r := range sb.assets {
		if !r.Deleted {
			records = append(records, r)
		}
	}
	sort.Slice(records, func(i, j int) bool {
		return records[i].Version > records[j].Version
	})
	return records
}

func extractETags(event Event) []string {
	return nil
}
