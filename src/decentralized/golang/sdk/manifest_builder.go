package sdk

import (
	"encoding/hex"
	"sync/atomic"
	"time"
)

var globalVersion uint64

type AssetEntry struct {
	Index    int
	Offset   int64
	Length   int
	Hash     string
}

type Manifest struct {
	AssetID    string
	Version    uint64
	MerkleRoot string
	Assets     []AssetEntry
	CreatedAt  time.Time
}

type ManifestBuilder struct {
	hasher *Hasher
}

func NewManifestBuilder() *ManifestBuilder {
	return &ManifestBuilder{hasher: NewHasher()}
}

func (mb *ManifestBuilder) Build(chunks []Chunk, merkleRoot []byte) (*Manifest, error) {
	entries := make([]AssetEntry, len(chunks))
	for i, ch := range chunks {
		entries[i] = AssetEntry{
			Index:  ch.Index,
			Offset: ch.Offset,
			Length: ch.Length,
			Hash:   mb.hasher.ChunkHashHex(ch.Data),
		}
	}
	version := atomic.AddUint64(&globalVersion, 1)
	return &Manifest{
		Version:    version,
		MerkleRoot: hex.EncodeToString(merkleRoot),
		Assets:     entries,
		CreatedAt:  time.Now().UTC(),
	}, nil
}
