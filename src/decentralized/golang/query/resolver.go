package query

import (
	"math/rand"
	"sync"
)

type Indexer interface {
	Query(req QueryRequest) QueryResponse
	ID() string
}

type Resolver struct {
	mu       sync.RWMutex
	indexers []Indexer
}

func NewResolver(indexers []Indexer) *Resolver {
	return &Resolver{indexers: indexers}
}

func (r *Resolver) SelectQuorum(req QueryRequest) ([]Indexer, int) {
	r.mu.RLock()
	pool := make([]Indexer, len(r.indexers))
	copy(pool, r.indexers)
	r.mu.RUnlock()
	rand.Shuffle(len(pool), func(i, j int) { pool[i], pool[j] = pool[j], pool[i] })
	quorumSize := (len(pool) / 2) + 1
	if quorumSize > len(pool) {
		quorumSize = len(pool)
	}
	return pool[:quorumSize], quorumSize
}

func (r *Resolver) AddIndexer(indexer Indexer) {
	r.mu.Lock()
	r.indexers = append(r.indexers, indexer)
	r.mu.Unlock()
}

func (r *Resolver) RemoveIndexer(id string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	filtered := r.indexers[:0]
	for _, ix := range r.indexers {
		if ix.ID() != id {
			filtered = append(filtered, ix)
		}
	}
	r.indexers = filtered
}
