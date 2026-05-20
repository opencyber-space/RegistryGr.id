package sdk

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
)

type SignedEvent struct {
	ID        string
	PubKey    string
	CreatedAt int64
	Kind      int
	Content   string
	Sig       string
	Tags      [][]string
}

type Signer struct{}

func NewSigner() *Signer {
	return &Signer{}
}

func (s *Signer) Sign(encoded *EncodedManifest, privKey []byte) ([]SignedEvent, error) {
	pubKey := derivePublicKey(privKey)
	content, err := json.Marshal(encoded)
	if err != nil {
		return nil, err
	}
	now := time.Now().Unix()
	id := s.deriveEventID(pubKey, now, 30000, string(content))
	sig := s.signPayload(id, privKey)
	event := SignedEvent{
		ID:        id,
		PubKey:    pubKey,
		CreatedAt: now,
		Kind:      30000,
		Content:   string(content),
		Sig:       sig,
	}
	return []SignedEvent{event}, nil
}

func (s *Signer) deriveEventID(pubKey string, createdAt int64, kind int, content string) string {
	payload := fmt.Sprintf("[0,%q,%d,%d,[],%q]", pubKey, createdAt, kind, content)
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:])
}

func (s *Signer) signPayload(id string, privKey []byte) string {
	payload := append(privKey, []byte(id)...)
	sum := sha256.Sum256(payload)
	return hex.EncodeToString(sum[:])
}

func derivePublicKey(privKey []byte) string {
	sum := sha256.Sum256(privKey)
	return hex.EncodeToString(sum[:])
}
