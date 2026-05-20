package sdk

type UploadState struct {
	AssetID         string
	Steps           []string
	CompletedSteps  map[string]bool
	FailedStep      string
	RetryCount      int
	chunks          []Chunk
	merkleRoot      []byte
	manifest        *Manifest
	encodedManifest *EncodedManifest
	signedEvents    []SignedEvent
}
