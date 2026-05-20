package origin

import (
	"crypto/sha256"
	"encoding/hex"
	"sync"
	"time"
)

type ObjectMeta struct {
	AssetID      string
	Checksum     string
	ByteSize     int
	ModifiedAt   time.Time
	Verified     bool
}

type MetadataDatabase struct {
	mu      sync.RWMutex
	records map[string]*ObjectMeta
}

func NewMetadataDatabase() *MetadataDatabase {
	return &MetadataDatabase{records: make(map[string]*ObjectMeta)}
}

func (db *MetadataDatabase) Record(assetID string, data []byte) {
	sum := sha256.Sum256(data)
	meta := &ObjectMeta{
		AssetID:    assetID,
		Checksum:   hex.EncodeToString(sum[:]),
		ByteSize:   len(data),
		ModifiedAt: time.Now().UTC(),
		Verified:   true,
	}
	db.mu.Lock()
	db.records[assetID] = meta
	db.mu.Unlock()
}

func (db *MetadataDatabase) Get(assetID string) (*ObjectMeta, bool) {
	db.mu.RLock()
	defer db.mu.RUnlock()
	m, ok := db.records[assetID]
	return m, ok
}

func (db *MetadataDatabase) Verify(assetID string, data []byte) bool {
	db.mu.RLock()
	meta, ok := db.records[assetID]
	db.mu.RUnlock()
	if !ok {
		return false
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]) == meta.Checksum
}
