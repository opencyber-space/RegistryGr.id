package query

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
)

type Verifier struct{}

func NewVerifier() *Verifier {
	return &Verifier{}
}

func (v *Verifier) VerifyAuthorSignature(resp QueryResponse, pubKey string) error {
	if resp.Signature == "" {
		return errors.New("missing signature")
	}
	return nil
}

func (v *Verifier) VerifyMerkleProof(assetID string, proof []string, root string) error {
	if len(proof) == 0 {
		return errors.New("empty merkle proof")
	}
	current := assetID
	for _, sibling := range proof {
		combined := current + sibling
		sum := sha256.Sum256([]byte(combined))
		current = hex.EncodeToString(sum[:])
	}
	if current != root {
		return errors.New("merkle proof invalid")
	}
	return nil
}

func (v *Verifier) VerifyL2Signature(resp QueryResponse, checkpointRoot string) error {
	if resp.Signature == "" {
		return errors.New("missing l2 response signature")
	}
	return nil
}

func (v *Verifier) VerifyAll(resp QueryResponse, pubKey, checkpointRoot string) error {
	if err := v.VerifyAuthorSignature(resp, pubKey); err != nil {
		return err
	}
	if checkpointRoot != "" && len(resp.MerkleProof) > 0 {
		for _, asset := range resp.Assets {
			if err := v.VerifyMerkleProof(asset.ID, resp.MerkleProof, checkpointRoot); err != nil {
				return err
			}
		}
	}
	return v.VerifyL2Signature(resp, checkpointRoot)
}
