package origin

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

type ObjectGateway struct {
	mu      sync.RWMutex
	objects map[string][]byte
	meta    *MetadataDatabase
}

func NewObjectGateway(meta *MetadataDatabase) *ObjectGateway {
	return &ObjectGateway{
		objects: make(map[string][]byte),
		meta:    meta,
	}
}

func (g *ObjectGateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/"), "/")
	if len(parts) < 2 {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	assetID := parts[1]
	g.mu.RLock()
	data, ok := g.objects[assetID]
	g.mu.RUnlock()
	if !ok {
		http.NotFound(w, r)
		return
	}
	rangeHeader := r.Header.Get("Range")
	if rangeHeader == "" {
		w.Header().Set("Content-Length", strconv.Itoa(len(data)))
		w.Write(data)
		return
	}
	start, end, err := parseRange(rangeHeader, len(data))
	if err != nil {
		http.Error(w, "invalid range", http.StatusRequestedRangeNotSatisfiable)
		return
	}
	w.Header().Set("Content-Range", fmt.Sprintf("bytes %d-%d/%d", start, end, len(data)))
	w.Header().Set("Content-Length", strconv.Itoa(end-start+1))
	w.WriteHeader(http.StatusPartialContent)
	w.Write(data[start : end+1])
}

func parseRange(header string, size int) (int, int, error) {
	header = strings.TrimPrefix(header, "bytes=")
	parts := strings.Split(header, "-")
	if len(parts) != 2 {
		return 0, 0, fmt.Errorf("invalid range")
	}
	start, err := strconv.Atoi(parts[0])
	if err != nil {
		return 0, 0, err
	}
	var end int
	if parts[1] == "" {
		end = size - 1
	} else {
		end, err = strconv.Atoi(parts[1])
		if err != nil {
			return 0, 0, err
		}
	}
	return start, end, nil
}

func (g *ObjectGateway) Store(assetID string, data []byte) {
	g.mu.Lock()
	g.objects[assetID] = data
	g.mu.Unlock()
	g.meta.Record(assetID, data)
}
