package sdk

import (
	"context"
	"math"
	"time"
)

type SDKCore struct {
	chunker         *Chunker
	hasher          *Hasher
	manifestBuilder *ManifestBuilder
	policyEncoder   *PolicyEncoder
	signer          *Signer
	nostrPublisher  NostrPublisher
	originUploader  OriginUploader
	maxRetries      int
	backoffBase     time.Duration
}

func NewSDKCore(np NostrPublisher, ou OriginUploader) *SDKCore {
	return &SDKCore{
		chunker:         NewChunker(),
		hasher:          NewHasher(),
		manifestBuilder: NewManifestBuilder(),
		policyEncoder:   NewPolicyEncoder(),
		signer:          NewSigner(),
		nostrPublisher:  np,
		originUploader:  ou,
		maxRetries:      5,
		backoffBase:     time.Second,
	}
}

func (s *SDKCore) Upload(ctx context.Context, asset []byte, policy Policy, privKey []byte) error {
	state := &UploadState{
		AssetID:        deriveAssetID(asset),
		Steps:          []string{"chunk", "hash", "manifest", "encode", "sign", "publish", "upload"},
		CompletedSteps: make(map[string]bool),
	}

	steps := []struct {
		name string
		fn   func() error
	}{
		{"chunk", func() error { return s.runChunk(ctx, asset, state) }},
		{"hash", func() error { return s.runHash(ctx, state) }},
		{"manifest", func() error { return s.runManifest(ctx, state, policy) }},
		{"encode", func() error { return s.runPolicyEncode(ctx, state, policy) }},
		{"sign", func() error { return s.runSign(ctx, state, privKey) }},
		{"publish", func() error { return s.runPublish(ctx, state) }},
		{"upload", func() error { return s.runUpload(ctx, asset, state) }},
	}

	for _, step := range steps {
		if state.CompletedSteps[step.name] {
			continue
		}
		if err := s.withRetry(ctx, step.fn); err != nil {
			state.FailedStep = step.name
			return err
		}
		state.CompletedSteps[step.name] = true
	}
	return nil
}

func (s *SDKCore) withRetry(ctx context.Context, fn func() error) error {
	var lastErr error
	for i := 0; i < s.maxRetries; i++ {
		if err := fn(); err != nil {
			lastErr = err
			wait := time.Duration(math.Pow(2, float64(i))) * s.backoffBase
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(wait):
			}
			continue
		}
		return nil
	}
	return lastErr
}

func (s *SDKCore) runChunk(_ context.Context, asset []byte, state *UploadState) error {
	chunks, err := s.chunker.Split(asset)
	if err != nil {
		return err
	}
	state.chunks = chunks
	return nil
}

func (s *SDKCore) runHash(_ context.Context, state *UploadState) error {
	root, err := s.hasher.ComputeMerkleRoot(state.chunks)
	if err != nil {
		return err
	}
	state.merkleRoot = root
	return nil
}

func (s *SDKCore) runManifest(_ context.Context, state *UploadState, _ Policy) error {
	manifest, err := s.manifestBuilder.Build(state.chunks, state.merkleRoot)
	if err != nil {
		return err
	}
	state.manifest = manifest
	return nil
}

func (s *SDKCore) runPolicyEncode(_ context.Context, state *UploadState, policy Policy) error {
	encoded, err := s.policyEncoder.Encode(state.manifest, policy)
	if err != nil {
		return err
	}
	state.encodedManifest = encoded
	return nil
}

func (s *SDKCore) runSign(_ context.Context, state *UploadState, privKey []byte) error {
	signed, err := s.signer.Sign(state.encodedManifest, privKey)
	if err != nil {
		return err
	}
	state.signedEvents = signed
	return nil
}

func (s *SDKCore) runPublish(ctx context.Context, state *UploadState) error {
	return s.nostrPublisher.PublishAll(ctx, state.signedEvents)
}

func (s *SDKCore) runUpload(ctx context.Context, asset []byte, state *UploadState) error {
	return s.originUploader.Upload(ctx, asset, state.AssetID)
}
