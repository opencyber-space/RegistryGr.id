package scheduler

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"sort"
	"sync"
	"time"
)

type ConsistentHashEngine struct {
	mu      sync.RWMutex
	ring    []ringNode
	vnodes  int
}

type ringNode struct {
	hash        uint64
	schedulerID string
}

func NewConsistentHashEngine(vnodes int) *ConsistentHashEngine {
	return &ConsistentHashEngine{vnodes: vnodes}
}

func (c *ConsistentHashEngine) AddScheduler(id string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for i := 0; i < c.vnodes; i++ {
		key := []byte(id + string(rune(i)))
		sum := sha256.Sum256(key)
		hash := binary.BigEndian.Uint64(sum[:8])
		c.ring = append(c.ring, ringNode{hash: hash, schedulerID: id})
	}
	sort.Slice(c.ring, func(i, j int) bool { return c.ring[i].hash < c.ring[j].hash })
}

func (c *ConsistentHashEngine) Assign(contentID string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if len(c.ring) == 0 {
		return ""
	}
	sum := sha256.Sum256([]byte(contentID))
	hash := binary.BigEndian.Uint64(sum[:8])
	idx := sort.Search(len(c.ring), func(i int) bool { return c.ring[i].hash >= hash })
	if idx >= len(c.ring) {
		idx = 0
	}
	return c.ring[idx].schedulerID
}

type HealthStatus struct {
	SchedulerID string
	Alive       bool
	RTT         time.Duration
	CheckedAt   time.Time
}

type SchedulerHealthMonitor struct {
	mu       sync.RWMutex
	statuses map[string]*HealthStatus
	probers  []SchedulerProber
	interval time.Duration
}

type SchedulerProber interface {
	Probe(ctx context.Context, id string) (time.Duration, error)
	ID() string
}

func NewSchedulerHealthMonitor(probers []SchedulerProber, interval time.Duration) *SchedulerHealthMonitor {
	return &SchedulerHealthMonitor{
		statuses: make(map[string]*HealthStatus),
		probers:  probers,
		interval: interval,
	}
}

func (m *SchedulerHealthMonitor) Run(ctx context.Context) {
	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			for _, p := range m.probers {
				rtt, err := p.Probe(ctx, p.ID())
				status := &HealthStatus{
					SchedulerID: p.ID(),
					Alive:       err == nil,
					RTT:         rtt,
					CheckedAt:   time.Now(),
				}
				m.mu.Lock()
				m.statuses[p.ID()] = status
				m.mu.Unlock()
			}
		}
	}
}

func (m *SchedulerHealthMonitor) IsAlive(id string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	s, ok := m.statuses[id]
	return ok && s.Alive
}

type DecisionCache struct {
	mu      sync.RWMutex
	entries map[string]*decisionEntry
	ttl     time.Duration
}

type decisionEntry struct {
	schedulerID string
	expiresAt   time.Time
}

func NewDecisionCache(ttl time.Duration) *DecisionCache {
	return &DecisionCache{
		entries: make(map[string]*decisionEntry),
		ttl:     ttl,
	}
}

func (dc *DecisionCache) Set(contentID, schedulerID string) {
	dc.mu.Lock()
	dc.entries[contentID] = &decisionEntry{
		schedulerID: schedulerID,
		expiresAt:   time.Now().Add(dc.ttl),
	}
	dc.mu.Unlock()
}

func (dc *DecisionCache) Get(contentID string) (string, bool) {
	dc.mu.RLock()
	entry, ok := dc.entries[contentID]
	dc.mu.RUnlock()
	if !ok || time.Now().After(entry.expiresAt) {
		return "", false
	}
	return entry.schedulerID, true
}

type Bridge struct {
	mu          sync.RWMutex
	globalState map[string]interface{}
}

func NewBridge() *Bridge {
	return &Bridge{globalState: make(map[string]interface{})}
}

func (b *Bridge) UpdateGlobalState(key string, value interface{}) {
	b.mu.Lock()
	b.globalState[key] = value
	b.mu.Unlock()
}

func (b *Bridge) GetState(key string) (interface{}, bool) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	v, ok := b.globalState[key]
	return v, ok
}

type ManagerAPIFacade struct {
	hashEngine    *ConsistentHashEngine
	decisionCache *DecisionCache
	healthMonitor *SchedulerHealthMonitor
	bridge        *Bridge
}

func NewManagerAPIFacade(he *ConsistentHashEngine, dc *DecisionCache, hm *SchedulerHealthMonitor, b *Bridge) *ManagerAPIFacade {
	return &ManagerAPIFacade{
		hashEngine:    he,
		decisionCache: dc,
		healthMonitor: hm,
		bridge:        b,
	}
}

func (m *ManagerAPIFacade) SelectScheduler(contentID string) string {
	if cached, ok := m.decisionCache.Get(contentID); ok {
		if m.healthMonitor.IsAlive(cached) {
			return cached
		}
	}
	selected := m.hashEngine.Assign(contentID)
	m.decisionCache.Set(contentID, selected)
	return selected
}

func (m *ManagerAPIFacade) Preheat(ctx context.Context, contentID string) error {
	return nil
}

func (m *ManagerAPIFacade) Keepalive(schedulerID string) {
}

type PolicyEngine struct {
	mu sync.RWMutex
}

func NewPolicyEngine() *PolicyEngine {
	return &PolicyEngine{}
}

type TaskSpec struct {
	ContentID   string
	SchedulerID string
	Intent      string
	Scope       string
	TTL         time.Duration
}

func (pe *PolicyEngine) Evaluate(spec TaskSpec) (bool, error) {
	if spec.TTL <= 0 {
		return false, nil
	}
	if spec.Intent == "" {
		return false, nil
	}
	return true, nil
}

type Task struct {
	ID          string
	ContentID   string
	SchedulerID string
	Status      string
	CreatedAt   time.Time
	ExpiresAt   time.Time
}

type TaskOrchestrator struct {
	mu      sync.RWMutex
	tasks   map[string]*Task
	preheat map[string]struct{}
}

func NewTaskOrchestrator() *TaskOrchestrator {
	return &TaskOrchestrator{
		tasks:   make(map[string]*Task),
		preheat: make(map[string]struct{}),
	}
}

func (to *TaskOrchestrator) CreateTask(task *Task) {
	to.mu.Lock()
	to.tasks[task.ID] = task
	to.mu.Unlock()
}

func (to *TaskOrchestrator) InvalidateTask(id string) {
	to.mu.Lock()
	if t, ok := to.tasks[id]; ok {
		t.Status = "invalidated"
	}
	to.mu.Unlock()
}

func (to *TaskOrchestrator) ReconcilePreheat(contentID string) {
	to.mu.Lock()
	to.preheat[contentID] = struct{}{}
	to.mu.Unlock()
}

func (to *TaskOrchestrator) ReconcileEviction(contentID string) {
	to.mu.Lock()
	delete(to.preheat, contentID)
	to.mu.Unlock()
}
