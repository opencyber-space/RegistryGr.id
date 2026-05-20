package aggregator

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sync"
	"time"
)

type CheckpointBuilder struct {
	stateBuilder *StateBuilder
}

func NewCheckpointBuilder(sb *StateBuilder) *CheckpointBuilder {
	return &CheckpointBuilder{stateBuilder: sb}
}

func (cb *CheckpointBuilder) DeriveRoot() (string, error) {
	assets := cb.stateBuilder.ListAssets()
	data, err := json.Marshal(assets)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

type ThresholdSignature struct {
	IndexerID string
	Sig       string
	Root      string
	SignedAt  time.Time
}

type QuorumSigner struct {
	mu         sync.Mutex
	signatures map[string][]ThresholdSignature
	threshold  int
}

func NewQuorumSigner(threshold int) *QuorumSigner {
	return &QuorumSigner{
		signatures: make(map[string][]ThresholdSignature),
		threshold:  threshold,
	}
}

func (qs *QuorumSigner) AddSignature(root string, sig ThresholdSignature) bool {
	qs.mu.Lock()
	defer qs.mu.Unlock()
	qs.signatures[root] = append(qs.signatures[root], sig)
	return len(qs.signatures[root]) >= qs.threshold
}

func (qs *QuorumSigner) GetSignatures(root string) []ThresholdSignature {
	qs.mu.Lock()
	defer qs.mu.Unlock()
	return qs.signatures[root]
}

type CheckpointRecord struct {
	Root      string
	Epoch     uint64
	Sigs      []ThresholdSignature
	CreatedAt time.Time
}

type CheckpointDatabase struct {
	mu      sync.RWMutex
	records []*CheckpointRecord
}

func NewCheckpointDatabase() *CheckpointDatabase {
	return &CheckpointDatabase{}
}

func (db *CheckpointDatabase) Store(record *CheckpointRecord) {
	db.mu.Lock()
	db.records = append(db.records, record)
	db.mu.Unlock()
}

func (db *CheckpointDatabase) Latest() *CheckpointRecord {
	db.mu.RLock()
	defer db.mu.RUnlock()
	if len(db.records) == 0 {
		return nil
	}
	return db.records[len(db.records)-1]
}

func (db *CheckpointDatabase) GetByEpoch(epoch uint64) *CheckpointRecord {
	db.mu.RLock()
	defer db.mu.RUnlock()
	for _, r := range db.records {
		if r.Epoch == epoch {
			return r
		}
	}
	return nil
}

type CheckpointEventPublisher struct {
	publisher interface {
		PublishAll(ctx context.Context, events []SignedEvent) error
	}
}

func NewCheckpointEventPublisher(pub interface {
	PublishAll(ctx context.Context, events []SignedEvent) error
}) *CheckpointEventPublisher {
	return &CheckpointEventPublisher{publisher: pub}
}

func (cep *CheckpointEventPublisher) Publish(ctx context.Context, record *CheckpointRecord) error {
	content, _ := json.Marshal(record)
	event := SignedEvent{
		Kind:      30003,
		Content:   string(content),
		CreatedAt: time.Now().Unix(),
	}
	return cep.publisher.PublishAll(ctx, []SignedEvent{event})
}
