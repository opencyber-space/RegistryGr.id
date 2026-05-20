package aggregator

import (
	"context"
	"sync"
	"time"
)

type Event struct {
	ID        string
	PubKey    string
	CreatedAt int64
	Kind      int
	Content   string
	Sig       string
}

type RelayConsumer struct {
	relays         []EventSource
	seen           map[string]struct{}
	mu             sync.Mutex
	replayWindow   time.Duration
	out            chan Event
}

type EventSource interface {
	Subscribe(ctx context.Context, since int64) (<-chan Event, error)
}

func NewRelayConsumer(relays []EventSource, replayWindow time.Duration) *RelayConsumer {
	return &RelayConsumer{
		relays:       relays,
		seen:         make(map[string]struct{}),
		replayWindow: replayWindow,
		out:          make(chan Event, 1024),
	}
}

func (rc *RelayConsumer) Start(ctx context.Context) (<-chan Event, error) {
	since := time.Now().Add(-rc.replayWindow).Unix()
	for _, relay := range rc.relays {
		ch, err := relay.Subscribe(ctx, since)
		if err != nil {
			continue
		}
		go rc.ingest(ctx, ch)
	}
	return rc.out, nil
}

func (rc *RelayConsumer) ingest(ctx context.Context, ch <-chan Event) {
	for {
		select {
		case <-ctx.Done():
			return
		case event, ok := <-ch:
			if !ok {
				return
			}
			rc.mu.Lock()
			_, dup := rc.seen[event.ID]
			if !dup {
				rc.seen[event.ID] = struct{}{}
			}
			rc.mu.Unlock()
			if !dup {
				select {
				case rc.out <- event:
				case <-ctx.Done():
					return
				}
			}
		}
	}
}
