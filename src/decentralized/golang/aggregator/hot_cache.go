package aggregator

import (
	"sync"
	"time"
)

type CacheEntry struct {
	Value     interface{}
	ExpiresAt time.Time
}

type HotCache struct {
	mu      sync.RWMutex
	entries map[string]*CacheEntry
	ttl     time.Duration
	ticker  *time.Ticker
}

func NewHotCache(ttl time.Duration) *HotCache {
	hc := &HotCache{
		entries: make(map[string]*CacheEntry),
		ttl:     ttl,
		ticker:  time.NewTicker(ttl / 2),
	}
	go hc.evictLoop()
	return hc
}

func (hc *HotCache) Set(key string, value interface{}) {
	hc.mu.Lock()
	hc.entries[key] = &CacheEntry{Value: value, ExpiresAt: time.Now().Add(hc.ttl)}
	hc.mu.Unlock()
}

func (hc *HotCache) Get(key string) (interface{}, bool) {
	hc.mu.RLock()
	entry, ok := hc.entries[key]
	hc.mu.RUnlock()
	if !ok || time.Now().After(entry.ExpiresAt) {
		return nil, false
	}
	return entry.Value, true
}

func (hc *HotCache) Delete(key string) {
	hc.mu.Lock()
	delete(hc.entries, key)
	hc.mu.Unlock()
}

func (hc *HotCache) evictLoop() {
	for range hc.ticker.C {
		now := time.Now()
		hc.mu.Lock()
		for k, v := range hc.entries {
			if now.After(v.ExpiresAt) {
				delete(hc.entries, k)
			}
		}
		hc.mu.Unlock()
	}
}
