package nostr

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"
)

type Event struct {
	ID        string     `json:"id"`
	PubKey    string     `json:"pubkey"`
	CreatedAt int64      `json:"created_at"`
	Kind      int        `json:"kind"`
	Content   string     `json:"content"`
	Sig       string     `json:"sig"`
	Tags      [][]string `json:"tags"`
}

type Subscription struct {
	ID      string
	Filters []Filter
	Ch      chan Event
}

type Filter struct {
	Kinds   []int
	Authors []string
	Since   *int64
	Until   *int64
}

type Relay struct {
	mu            sync.RWMutex
	events        []Event
	subscriptions map[string]*Subscription
	role          string
	upstream      []string
}

func NewRelay(role string, upstream []string) *Relay {
	return &Relay{
		subscriptions: make(map[string]*Subscription),
		role:          role,
		upstream:      upstream,
	}
}

func (r *Relay) PersistEvent(event Event) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.events = append(r.events, event)
	r.notifySubscribers(event)
}

func (r *Relay) notifySubscribers(event Event) {
	for _, sub := range r.subscriptions {
		if r.matchesFilters(event, sub.Filters) {
			select {
			case sub.Ch <- event:
			default:
			}
		}
	}
}

func (r *Relay) matchesFilters(event Event, filters []Filter) bool {
	if len(filters) == 0 {
		return true
	}
	for _, f := range filters {
		for _, k := range f.Kinds {
			if k == event.Kind {
				return true
			}
		}
	}
	return false
}

func (r *Relay) Subscribe(subID string, filters []Filter) *Subscription {
	sub := &Subscription{
		ID:      subID,
		Filters: filters,
		Ch:      make(chan Event, 100),
	}
	r.mu.Lock()
	r.subscriptions[subID] = sub
	r.mu.Unlock()
	return sub
}

func (r *Relay) Unsubscribe(subID string) {
	r.mu.Lock()
	delete(r.subscriptions, subID)
	r.mu.Unlock()
}

func (r *Relay) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	r.mu.RLock()
	events := make([]Event, len(r.events))
	copy(events, r.events)
	r.mu.RUnlock()
	json.NewEncoder(w).Encode(events)
}

func (r *Relay) ReplicateFrom(source *Relay) {
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			source.mu.RLock()
			newEvents := make([]Event, len(source.events))
			copy(newEvents, source.events)
			source.mu.RUnlock()
			r.mu.Lock()
			existing := make(map[string]struct{})
			for _, e := range r.events {
				existing[e.ID] = struct{}{}
			}
			for _, e := range newEvents {
				if _, ok := existing[e.ID]; !ok {
					r.events = append(r.events, e)
					r.notifySubscribers(e)
				}
			}
			r.mu.Unlock()
		}
	}()
}

type RelayA struct{ *Relay }
type RelayB struct{ *Relay }
type RelayC struct{ *Relay }

func NewRelayA() *RelayA {
	return &RelayA{NewRelay("primary", nil)}
}

func NewRelayB(a *RelayA) *RelayB {
	rb := &RelayB{NewRelay("replica", nil)}
	rb.ReplicateFrom(a.Relay)
	return rb
}

func NewRelayC(b *RelayB) *RelayC {
	rc := &RelayC{NewRelay("redundant", nil)}
	rc.ReplicateFrom(b.Relay)
	return rc
}
