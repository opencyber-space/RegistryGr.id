package sdk

import "time"

type Policy struct {
	PropagationIntent string
	DistributionScope string
	TTL               time.Duration
	DeletionSemantics string
}

type EncodedManifest struct {
	Manifest *Manifest
	Policy   Policy
}

type PolicyEncoder struct{}

func NewPolicyEncoder() *PolicyEncoder {
	return &PolicyEncoder{}
}

func (pe *PolicyEncoder) Encode(manifest *Manifest, policy Policy) (*EncodedManifest, error) {
	return &EncodedManifest{
		Manifest: manifest,
		Policy:   policy,
	}, nil
}
