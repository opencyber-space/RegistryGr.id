package aggregator

import (
	"context"
	"sync"
	"time"
)

type StateDelta struct {
	FromVersion uint64
	ToVersion   uint64
	Changes     []*AssetRecord
}

type L2StateSynchronizer struct {
	mu        sync.RWMutex
	peers     []L2Peer
	version   uint64
	builder   *StateBuilder
	interval  time.Duration
}

type L2Peer interface {
	ExchangeDelta(ctx context.Context, delta StateDelta) (StateDelta, error)
}

func NewL2StateSynchronizer(builder *StateBuilder, peers []L2Peer, interval time.Duration) *L2StateSynchronizer {
	return &L2StateSynchronizer{
		builder:  builder,
		peers:    peers,
		interval: interval,
	}
}

func (s *L2StateSynchronizer) Run(ctx context.Context) {
	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.syncWithPeers(ctx)
		}
	}
}

func (s *L2StateSynchronizer) syncWithPeers(ctx context.Context) {
	s.mu.RLock()
	currentVersion := s.version
	s.mu.RUnlock()

	delta := StateDelta{
		FromVersion: currentVersion,
		ToVersion:   currentVersion,
		Changes:     s.builder.ListAssets(),
	}

	for _, peer := range s.peers {
		remoteDelta, err := peer.ExchangeDelta(ctx, delta)
		if err != nil {
			continue
		}
		s.applyDelta(remoteDelta)
	}
}

func (s *L2StateSynchronizer) applyDelta(delta StateDelta) {
	for _, record := range delta.Changes {
		s.builder.Apply(Event{
			ID:        record.ID,
			PubKey:    record.AuthorKey,
			CreatedAt: int64(record.Version),
			Kind:      30000,
			Content:   record.Manifest,
		})
	}
	s.mu.Lock()
	if delta.ToVersion > s.version {
		s.version = delta.ToVersion
	}
	s.mu.Unlock()
}
