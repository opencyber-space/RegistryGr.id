package query

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"time"
)

type QueryRequest struct {
	AssetID  string   `json:"asset_id,omitempty"`
	Tags     []string `json:"tags,omitempty"`
	AuthorID string   `json:"author_id,omitempty"`
	Limit    int      `json:"limit,omitempty"`
}

type QueryResponse struct {
	Assets    []AssetResult `json:"assets"`
	MerkleProof []string    `json:"merkle_proof"`
	Signature string        `json:"signature"`
	Transcript string       `json:"transcript"`
}

type AssetResult struct {
	ID       string `json:"id"`
	Manifest string `json:"manifest"`
	Version  uint64 `json:"version"`
}

type AssetStore interface {
	GetAsset(id string) (interface{}, bool)
	QueryByTag(tag string) []interface{}
	ListAssets() []interface{}
}

type QueryAPI struct {
	store     AssetStore
	cache     Cache
	signingKey []byte
}

type Cache interface {
	Get(key string) (interface{}, bool)
	Set(key string, value interface{})
}

func NewQueryAPI(store AssetStore, cache Cache, signingKey []byte) *QueryAPI {
	return &QueryAPI{store: store, cache: cache, signingKey: signingKey}
}

func (q *QueryAPI) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	var req QueryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request", http.StatusBadRequest)
		return
	}
	resp := q.execute(req)
	resp.Signature = q.signResponse(resp)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (q *QueryAPI) execute(req QueryRequest) QueryResponse {
	cacheKey := buildCacheKey(req)
	if cached, ok := q.cache.Get(cacheKey); ok {
		if resp, ok := cached.(QueryResponse); ok {
			return resp
		}
	}
	var results []AssetResult
	if req.AssetID != "" {
		if asset, ok := q.store.GetAsset(req.AssetID); ok {
			results = append(results, toResult(asset))
		}
	}
	resp := QueryResponse{
		Assets:    results,
		Transcript: buildTranscript(req, results, time.Now()),
	}
	q.cache.Set(cacheKey, resp)
	return resp
}

func (q *QueryAPI) signResponse(resp QueryResponse) string {
	data, _ := json.Marshal(resp.Assets)
	data = append(data, q.signingKey...)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func buildCacheKey(req QueryRequest) string {
	data, _ := json.Marshal(req)
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func buildTranscript(req QueryRequest, results []AssetResult, ts time.Time) string {
	data, _ := json.Marshal(map[string]interface{}{
		"request": req, "result_count": len(results), "ts": ts.Unix(),
	})
	return string(data)
}

func toResult(asset interface{}) AssetResult {
	return AssetResult{}
}
