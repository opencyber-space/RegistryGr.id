package watchdog

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sync"
	"time"
)

type EvidenceStore struct {
	mu          sync.RWMutex
	transcripts []ProbeResult
}

func NewEvidenceStore() *EvidenceStore {
	return &EvidenceStore{}
}

func (es *EvidenceStore) RecordTranscript(result ProbeResult) {
	es.mu.Lock()
	es.transcripts = append(es.transcripts, result)
	es.mu.Unlock()
}

func (es *EvidenceStore) GetTranscripts(indexerID string) []ProbeResult {
	es.mu.RLock()
	defer es.mu.RUnlock()
	var out []ProbeResult
	for _, t := range es.transcripts {
		if t.IndexerID == indexerID {
			out = append(out, t)
		}
	}
	return out
}

type L1Event struct {
	ID        string
	Kind      int
	PubKey    string
	CreatedAt int64
	Content   string
}

type L1Scanner struct {
	relays       []L1RelaySource
	groundTruth  *GroundTruthDatabase
	interval     time.Duration
}

type L1RelaySource interface {
	FetchEvents(ctx context.Context, since int64) ([]L1Event, error)
}

func NewL1Scanner(relays []L1RelaySource, gt *GroundTruthDatabase, interval time.Duration) *L1Scanner {
	return &L1Scanner{relays: relays, groundTruth: gt, interval: interval}
}

func (s *L1Scanner) Run(ctx context.Context) {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()
	var lastScan int64
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			for _, relay := range s.relays {
				events, err := relay.FetchEvents(ctx, lastScan)
				if err != nil {
					continue
				}
				for _, e := range events {
					s.groundTruth.Ingest(e)
				}
			}
			lastScan = time.Now().Unix()
		}
	}
}

type AuthorTimeline struct {
	PubKey string
	Events []L1Event
}

type GroundTruthDatabase struct {
	mu       sync.RWMutex
	events   []L1Event
	byAuthor map[string][]L1Event
	byAsset  map[string][]L1Event
}

func NewGroundTruthDatabase() *GroundTruthDatabase {
	return &GroundTruthDatabase{
		byAuthor: make(map[string][]L1Event),
		byAsset:  make(map[string][]L1Event),
	}
}

func (db *GroundTruthDatabase) Ingest(event L1Event) {
	db.mu.Lock()
	defer db.mu.Unlock()
	db.events = append(db.events, event)
	db.byAuthor[event.PubKey] = append(db.byAuthor[event.PubKey], event)
	db.byAsset[event.ID] = append(db.byAsset[event.ID], event)
}

func (db *GroundTruthDatabase) GetAuthorTimeline(pubKey string) []L1Event {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return db.byAuthor[pubKey]
}

func (db *GroundTruthDatabase) GetAssetHistory(assetID string) []L1Event {
	db.mu.RLock()
	defer db.mu.RUnlock()
	return db.byAsset[assetID]
}

type Verdict struct {
	IndexerID  string
	Omissions  []string
	Censored   []string
	Equivocal  []string
	IssuedAt   time.Time
}

type Comparator struct {
	groundTruth   *GroundTruthDatabase
	evidenceStore *EvidenceStore
}

func NewComparator(gt *GroundTruthDatabase, es *EvidenceStore) *Comparator {
	return &Comparator{groundTruth: gt, evidenceStore: es}
}

func (c *Comparator) Analyze(ctx context.Context, indexerID string) Verdict {
	transcripts := c.evidenceStore.GetTranscripts(indexerID)
	verdict := Verdict{IndexerID: indexerID, IssuedAt: time.Now()}
	for _, t := range transcripts {
		if !t.Consistent {
			verdict.Omissions = append(verdict.Omissions, t.Query)
		}
	}
	return verdict
}

type AuditReport struct {
	WatchdogKey string
	Verdicts    []Verdict
	MerkleRoot  string
	Sig         string
	IssuedAt    time.Time
}

type ReportSigner struct {
	identityKey []byte
}

func NewReportSigner(identityKey []byte) *ReportSigner {
	return &ReportSigner{identityKey: identityKey}
}

func (rs *ReportSigner) Sign(verdicts []Verdict) (*AuditReport, error) {
	data, err := json.Marshal(verdicts)
	if err != nil {
		return nil, err
	}
	sum := sha256.Sum256(append(data, rs.identityKey...))
	return &AuditReport{
		Verdicts: verdicts,
		Sig:      hex.EncodeToString(sum[:]),
		IssuedAt: time.Now().UTC(),
	}, nil
}

type ReputationScore struct {
	IndexerID   string
	Score       float64
	Evidence    []string
	Timestamps  []time.Time
	PublishedAt time.Time
}

type ReputationEventPublisher struct {
	nostrPublisher interface {
		Publish(ctx context.Context, event interface{}) error
	}
}

func NewReputationEventPublisher(pub interface {
	Publish(ctx context.Context, event interface{}) error
}) *ReputationEventPublisher {
	return &ReputationEventPublisher{nostrPublisher: pub}
}

func (rep *ReputationEventPublisher) Publish(ctx context.Context, score ReputationScore) error {
	return rep.nostrPublisher.Publish(ctx, score)
}
