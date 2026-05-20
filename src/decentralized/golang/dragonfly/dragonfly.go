package dragonfly

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

type Chunk struct {
	ContentID string
	Index     int
	Data      []byte
	Hash      string
}

type OriginFetcher struct {
	gatewayURL string
	client     *http.Client
}

func NewOriginFetcher(gatewayURL string) *OriginFetcher {
	return &OriginFetcher{
		gatewayURL: gatewayURL,
		client:     &http.Client{Timeout: 30 * time.Second},
	}
}

func (f *OriginFetcher) FetchRange(ctx context.Context, assetID string, start, end int64) ([]byte, error) {
	url := fmt.Sprintf("%s/object/%s", f.gatewayURL, assetID)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Range", fmt.Sprintf("bytes=%d-%d", start, end))
	resp, err := f.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(resp.Body)
}

type DiskCache struct {
	mu      sync.RWMutex
	store   map[string][]byte
	maxSize int64
	used    int64
}

func NewDiskCache(maxSize int64) *DiskCache {
	return &DiskCache{store: make(map[string][]byte), maxSize: maxSize}
}

func (dc *DiskCache) Store(key string, data []byte) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	if dc.used+int64(len(data)) > dc.maxSize {
		dc.evict(int64(len(data)))
	}
	dc.store[key] = data
	dc.used += int64(len(data))
}

func (dc *DiskCache) Get(key string) ([]byte, bool) {
	dc.mu.RLock()
	defer dc.mu.RUnlock()
	d, ok := dc.store[key]
	return d, ok
}

func (dc *DiskCache) Evict(key string) {
	dc.mu.Lock()
	if d, ok := dc.store[key]; ok {
		dc.used -= int64(len(d))
		delete(dc.store, key)
	}
	dc.mu.Unlock()
}

func (dc *DiskCache) evict(needed int64) {
	for k, v := range dc.store {
		delete(dc.store, k)
		dc.used -= int64(len(v))
		if dc.maxSize-dc.used >= needed {
			break
		}
	}
}

type PieceServer struct {
	cache *DiskCache
	mux   *http.ServeMux
}

func NewPieceServer(cache *DiskCache) *PieceServer {
	ps := &PieceServer{cache: cache, mux: http.NewServeMux()}
	ps.mux.HandleFunc("/piece/", ps.handlePiece)
	return ps
}

func (ps *PieceServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	ps.mux.ServeHTTP(w, r)
}

func (ps *PieceServer) handlePiece(w http.ResponseWriter, r *http.Request) {
	key := r.URL.Path[len("/piece/"):]
	data, ok := ps.cache.Get(key)
	if !ok {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Length", fmt.Sprintf("%d", len(data)))
	w.Write(data)
}

type CacheGarbageCollector struct {
	cache    *DiskCache
	interval time.Duration
	policy   GCPolicy
}

type GCPolicy struct {
	MaxAge    time.Duration
	MaxSize   int64
	MinFree   int64
}

func NewCacheGarbageCollector(cache *DiskCache, interval time.Duration, policy GCPolicy) *CacheGarbageCollector {
	return &CacheGarbageCollector{cache: cache, interval: interval, policy: policy}
}

func (gc *CacheGarbageCollector) Run(ctx context.Context) {
	ticker := time.NewTicker(gc.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			gc.collect()
		}
	}
}

func (gc *CacheGarbageCollector) collect() {
	gc.cache.mu.Lock()
	defer gc.cache.mu.Unlock()
	if gc.cache.used < gc.policy.MaxSize {
		return
	}
	excess := gc.cache.used - gc.policy.MaxSize + gc.policy.MinFree
	for k, v := range gc.cache.store {
		if excess <= 0 {
			break
		}
		delete(gc.cache.store, k)
		excess -= int64(len(v))
		gc.cache.used -= int64(len(v))
	}
}

type IntegrityVerifier struct{}

func NewIntegrityVerifier() *IntegrityVerifier {
	return &IntegrityVerifier{}
}

func (iv *IntegrityVerifier) Verify(chunk Chunk) error {
	sum := sha256.Sum256(chunk.Data)
	actual := hex.EncodeToString(sum[:])
	if actual != chunk.Hash {
		return errors.New("chunk hash mismatch")
	}
	return nil
}

type LocalCache struct {
	mu    sync.RWMutex
	store map[string]Chunk
}

func NewLocalCache() *LocalCache {
	return &LocalCache{store: make(map[string]Chunk)}
}

func (lc *LocalCache) Write(chunk Chunk) {
	lc.mu.Lock()
	lc.store[chunkKey(chunk)] = chunk
	lc.mu.Unlock()
}

func (lc *LocalCache) Read(contentID string, index int) (Chunk, bool) {
	lc.mu.RLock()
	defer lc.mu.RUnlock()
	c, ok := lc.store[contentID+":"+fmt.Sprintf("%d", index)]
	return c, ok
}

func chunkKey(c Chunk) string {
	return c.ContentID + ":" + fmt.Sprintf("%d", c.Index)
}

type PeerSource interface {
	FetchChunk(ctx context.Context, contentID string, index int) (Chunk, error)
}

type PieceDownloader struct {
	peers      []PeerSource
	verifier   *IntegrityVerifier
	localCache *LocalCache
}

func NewPieceDownloader(peers []PeerSource, verifier *IntegrityVerifier, lc *LocalCache) *PieceDownloader {
	return &PieceDownloader{peers: peers, verifier: verifier, localCache: lc}
}

func (pd *PieceDownloader) Download(ctx context.Context, contentID string, index int) (Chunk, error) {
	if chunk, ok := pd.localCache.Read(contentID, index); ok {
		return chunk, nil
	}
	for _, peer := range pd.peers {
		chunk, err := peer.FetchChunk(ctx, contentID, index)
		if err != nil {
			continue
		}
		if err := pd.verifier.Verify(chunk); err != nil {
			continue
		}
		pd.localCache.Write(chunk)
		return chunk, nil
	}
	return Chunk{}, errors.New("no peer could serve chunk")
}

type PieceUploader struct {
	peers []PeerSink
}

type PeerSink interface {
	SendChunk(ctx context.Context, chunk Chunk) error
	ID() string
}

func NewPieceUploader(peers []PeerSink) *PieceUploader {
	return &PieceUploader{peers: peers}
}

func (pu *PieceUploader) Redistribute(ctx context.Context, chunk Chunk) {
	for _, peer := range pu.peers {
		go func(p PeerSink) {
			p.SendChunk(ctx, chunk)
		}(peer)
	}
}

type RetryEngine struct {
	downloader *PieceDownloader
	maxRetries int
	backoff    time.Duration
}

func NewRetryEngine(dl *PieceDownloader, maxRetries int, backoff time.Duration) *RetryEngine {
	return &RetryEngine{downloader: dl, maxRetries: maxRetries, backoff: backoff}
}

func (re *RetryEngine) Download(ctx context.Context, contentID string, index int) (Chunk, error) {
	var lastErr error
	for i := 0; i < re.maxRetries; i++ {
		chunk, err := re.downloader.Download(ctx, contentID, index)
		if err == nil {
			return chunk, nil
		}
		lastErr = err
		select {
		case <-ctx.Done():
			return Chunk{}, ctx.Err()
		case <-time.After(re.backoff * time.Duration(i+1)):
		}
	}
	return Chunk{}, fmt.Errorf("max retries exceeded: %w", lastErr)
}
