package sdk

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
)

type Hasher struct{}

func NewHasher() *Hasher {
	return &Hasher{}
}

func (h *Hasher) HashChunk(data []byte) []byte {
	sum := sha256.Sum256(data)
	return sum[:]
}

func (h *Hasher) ComputeMerkleRoot(chunks []Chunk) ([]byte, error) {
	if len(chunks) == 0 {
		return nil, errors.New("no chunks to hash")
	}
	hashes := make([][]byte, len(chunks))
	for i, ch := range chunks {
		hash := h.HashChunk(ch.Data)
		hashes[i] = hash
	}
	return h.buildMerkleRoot(hashes), nil
}

func (h *Hasher) buildMerkleRoot(hashes [][]byte) []byte {
	if len(hashes) == 1 {
		return hashes[0]
	}
	if len(hashes)%2 != 0 {
		hashes = append(hashes, hashes[len(hashes)-1])
	}
	var nextLevel [][]byte
	for i := 0; i < len(hashes); i += 2 {
		combined := append(hashes[i], hashes[i+1]...)
		sum := sha256.Sum256(combined)
		nextLevel = append(nextLevel, sum[:])
	}
	return h.buildMerkleRoot(nextLevel)
}

func (h *Hasher) MerkleRootHex(chunks []Chunk) (string, error) {
	root, err := h.ComputeMerkleRoot(chunks)
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(root), nil
}

func (h *Hasher) ChunkHashHex(data []byte) string {
	return hex.EncodeToString(h.HashChunk(data))
}
