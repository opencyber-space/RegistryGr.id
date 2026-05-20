package watchdog

import (
	"context"
	"math/rand"
	"time"
)

type ProbeResult struct {
	IndexerID   string
	Query       string
	Response    interface{}
	Latency     time.Duration
	IssuedAt    time.Time
	Consistent  bool
}

type L2Indexer interface {
	Query(ctx context.Context, req interface{}) (interface{}, error)
	ID() string
}

type L2ProbeEngine struct {
	indexers      []L2Indexer
	evidenceStore *EvidenceStore
	interval      time.Duration
}

func NewL2ProbeEngine(indexers []L2Indexer, es *EvidenceStore, interval time.Duration) *L2ProbeEngine {
	return &L2ProbeEngine{
		indexers:      indexers,
		evidenceStore: es,
		interval:      interval,
	}
}

func (pe *L2ProbeEngine) Run(ctx context.Context) {
	ticker := time.NewTicker(pe.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			pe.probe(ctx)
		}
	}
}

func (pe *L2ProbeEngine) probe(ctx context.Context) {
	if len(pe.indexers) == 0 {
		return
	}
	selected := pe.indexers[rand.Intn(len(pe.indexers))]
	query := pe.generateRandomQuery()
	start := time.Now()
	resp, err := selected.Query(ctx, query)
	latency := time.Since(start)
	result := ProbeResult{
		IndexerID: selected.ID(),
		Query:     query,
		Response:  resp,
		Latency:   latency,
		IssuedAt:  start,
		Consistent: err == nil,
	}
	pe.evidenceStore.RecordTranscript(result)
}

func (pe *L2ProbeEngine) generateRandomQuery() string {
	queries := []string{"list_assets", "get_manifest", "query_by_tag"}
	return queries[rand.Intn(len(queries))]
}
