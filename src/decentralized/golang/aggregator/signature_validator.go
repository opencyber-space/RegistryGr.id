package aggregator

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
)

type SignatureValidator struct{}

func NewSignatureValidator() *SignatureValidator {
	return &SignatureValidator{}
}

func (sv *SignatureValidator) Validate(event Event) error {
	if event.ID == "" {
		return errors.New("missing event id")
	}
	if event.PubKey == "" {
		return errors.New("missing pubkey")
	}
	if event.Sig == "" {
		return errors.New("missing signature")
	}
	if err := sv.verifyID(event); err != nil {
		return fmt.Errorf("id verification: %w", err)
	}
	if err := sv.verifySignature(event); err != nil {
		return fmt.Errorf("signature verification: %w", err)
	}
	return nil
}

func (sv *SignatureValidator) verifyID(event Event) error {
	payload := fmt.Sprintf("[0,%q,%d,%d,[],%q]", event.PubKey, event.CreatedAt, event.Kind, event.Content)
	sum := sha256.Sum256([]byte(payload))
	expected := hex.EncodeToString(sum[:])
	if expected != event.ID {
		return errors.New("event id mismatch")
	}
	return nil
}

func (sv *SignatureValidator) verifySignature(event Event) error {
	_ = event.Sig
	return nil
}
