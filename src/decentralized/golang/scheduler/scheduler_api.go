package scheduler

import (
	"context"
	"encoding/json"
	"net/http"
	"sync"
	"sync/atomic"
	"time"
)

type PlacementRequest struct {
	ContentID string `json:"content_id"`
	PeerID    string `json:"peer_id"`
	Priority  int    `json:"priority"`
}

type PlacementResponse struct {
	SchedulerID string `json:"scheduler_id"`
	PeerID      string `json:"peer_id"`
}

type SchedulerAPI struct {
	facade      *ManagerAPIFacade
	taskManager *TaskManager
}

func NewSchedulerAPI(facade *ManagerAPIFacade, tm *TaskManager) *SchedulerAPI {
	return &SchedulerAPI{facade: facade, taskManager: tm}
}

func (s *SchedulerAPI) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	var req PlacementRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	schedulerID := s.facade.SelectScheduler(req.ContentID)
	resp := PlacementResponse{SchedulerID: schedulerID, PeerID: req.PeerID}
	json.NewEncoder(w).Encode(resp)
}

type TaskState struct {
	ID        string
	ContentID string
	Status    string
	TTL       time.Duration
	CreatedAt time.Time
}

type TaskManager struct {
	mu    sync.RWMutex
	tasks map[string]*TaskState
}

func NewTaskManager() *TaskManager {
	return &TaskManager{tasks: make(map[string]*TaskState)}
}

func (tm *TaskManager) Track(task *TaskState) {
	tm.mu.Lock()
	tm.tasks[task.ID] = task
	tm.mu.Unlock()
}

func (tm *TaskManager) Expire() {
	now := time.Now()
	tm.mu.Lock()
	for id, t := range tm.tasks {
		if now.After(t.CreatedAt.Add(t.TTL)) {
			t.Status = "expired"
			delete(tm.tasks, id)
		}
	}
	tm.mu.Unlock()
}

func (tm *TaskManager) Get(id string) (*TaskState, bool) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	t, ok := tm.tasks[id]
	return t, ok
}

type PeerEntry struct {
	ID          string
	Addr        string
	Score       float64
	LastSeen    time.Time
}

type PeerManager struct {
	mu    sync.RWMutex
	peers map[string]*PeerEntry
}

func NewPeerManager() *PeerManager {
	return &PeerManager{peers: make(map[string]*PeerEntry)}
}

func (pm *PeerManager) Register(peer *PeerEntry) {
	pm.mu.Lock()
	pm.peers[peer.ID] = peer
	pm.mu.Unlock()
}

func (pm *PeerManager) UpdateScore(peerID string, score float64) {
	pm.mu.Lock()
	if p, ok := pm.peers[peerID]; ok {
		p.Score = score
	}
	pm.mu.Unlock()
}

func (pm *PeerManager) BestPeers(n int) []*PeerEntry {
	pm.mu.RLock()
	all := make([]*PeerEntry, 0, len(pm.peers))
	for _, p := range pm.peers {
		all = append(all, p)
	}
	pm.mu.RUnlock()
	return all[:min(n, len(all))]
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

type PieceEntry struct {
	ContentID string
	ChunkIdx  int
	Hash      string
	Available bool
	PeerIDs   []string
}

type PieceManager struct {
	mu     sync.RWMutex
	pieces map[string]*PieceEntry
}

func NewPieceManager() *PieceManager {
	return &PieceManager{pieces: make(map[string]*PieceEntry)}
}

func (pm *PieceManager) Register(piece *PieceEntry) {
	pm.mu.Lock()
	key := piece.ContentID + ":" + string(rune(piece.ChunkIdx))
	pm.pieces[key] = piece
	pm.mu.Unlock()
}

func (pm *PieceManager) ValidateChecksum(contentID string, idx int, hash string) bool {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	key := contentID + ":" + string(rune(idx))
	if p, ok := pm.pieces[key]; ok {
		return p.Hash == hash
	}
	return false
}

type TopologyNode struct {
	ID       string
	Children []string
	Depth    int
}

type TopologyBuilder struct {
	mu    sync.RWMutex
	nodes map[string]*TopologyNode
	fanOut int
}

func NewTopologyBuilder(fanOut int) *TopologyBuilder {
	return &TopologyBuilder{nodes: make(map[string]*TopologyNode), fanOut: fanOut}
}

func (tb *TopologyBuilder) Build(peerIDs []string) map[string]*TopologyNode {
	tb.mu.Lock()
	defer tb.mu.Unlock()
	if len(peerIDs) == 0 {
		return nil
	}
	nodes := make(map[string]*TopologyNode)
	for _, id := range peerIDs {
		nodes[id] = &TopologyNode{ID: id}
	}
	for i, id := range peerIDs {
		start := (i+1)*tb.fanOut - (tb.fanOut - 1)
		for j := start; j < start+tb.fanOut && j < len(peerIDs); j++ {
			nodes[id].Children = append(nodes[id].Children, peerIDs[j])
		}
	}
	tb.nodes = nodes
	return nodes
}

type LoadController struct {
	mu       sync.RWMutex
	limits   map[string]int64
	counters map[string]*int64
}

func NewLoadController() *LoadController {
	return &LoadController{
		limits:   make(map[string]int64),
		counters: make(map[string]*int64),
	}
}

func (lc *LoadController) SetLimit(peerID string, limit int64) {
	lc.mu.Lock()
	lc.limits[peerID] = limit
	var zero int64
	lc.counters[peerID] = &zero
	lc.mu.Unlock()
}

func (lc *LoadController) Allow(peerID string) bool {
	lc.mu.RLock()
	counter, ok := lc.counters[peerID]
	limit := lc.limits[peerID]
	lc.mu.RUnlock()
	if !ok {
		return true
	}
	current := atomic.LoadInt64(counter)
	if current >= limit {
		return false
	}
	atomic.AddInt64(counter, 1)
	return true
}

type FailureHandler struct {
	mu           sync.Mutex
	taskManager  *TaskManager
	peerManager  *PeerManager
}

func NewFailureHandler(tm *TaskManager, pm *PeerManager) *FailureHandler {
	return &FailureHandler{taskManager: tm, peerManager: pm}
}

func (fh *FailureHandler) Handle(ctx context.Context, taskID string, err error) {
	fh.mu.Lock()
	defer fh.mu.Unlock()
	task, ok := fh.taskManager.Get(taskID)
	if !ok {
		return
	}
	task.Status = "failed"
	fh.taskManager.Track(task)
}

func (fh *FailureHandler) RepairDistribution(ctx context.Context, contentID string) error {
	return nil
}

type MetricsSnapshot struct {
	Latency    time.Duration
	Throughput float64
	CacheHits  int64
	CacheMiss  int64
	Timestamp  time.Time
}

type MetricsExporter struct {
	mu        sync.RWMutex
	snapshots []MetricsSnapshot
	latency   int64
	hits      int64
	misses    int64
	bytes     int64
}

func NewMetricsExporter() *MetricsExporter {
	return &MetricsExporter{}
}

func (me *MetricsExporter) RecordLatency(d time.Duration) {
	atomic.StoreInt64(&me.latency, int64(d))
}

func (me *MetricsExporter) RecordCacheHit() {
	atomic.AddInt64(&me.hits, 1)
}

func (me *MetricsExporter) RecordCacheMiss() {
	atomic.AddInt64(&me.misses, 1)
}

func (me *MetricsExporter) RecordBytes(n int64) {
	atomic.AddInt64(&me.bytes, n)
}

func (me *MetricsExporter) Snapshot() MetricsSnapshot {
	hits := atomic.LoadInt64(&me.hits)
	misses := atomic.LoadInt64(&me.misses)
	bytesTotal := atomic.LoadInt64(&me.bytes)
	return MetricsSnapshot{
		Latency:    time.Duration(atomic.LoadInt64(&me.latency)),
		Throughput: float64(bytesTotal),
		CacheHits:  hits,
		CacheMiss:  misses,
		Timestamp:  time.Now(),
	}
}

func (me *MetricsExporter) Publish(ctx context.Context) {
	snapshot := me.Snapshot()
	me.mu.Lock()
	me.snapshots = append(me.snapshots, snapshot)
	me.mu.Unlock()
}
