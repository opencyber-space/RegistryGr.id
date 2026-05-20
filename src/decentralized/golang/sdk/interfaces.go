package sdk

import "context"

type NostrPublisher interface {
	PublishAll(ctx context.Context, events []SignedEvent) error
}

type OriginUploader interface {
	Upload(ctx context.Context, data []byte, assetID string) error
}
