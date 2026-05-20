package nostr

const (
	KindAssetEvent          = 30000
	KindAuthorManifest      = 30001
	KindPropagationIntent   = 30002
	KindRevocation          = 5
	KindL2Checkpoint        = 30003
	KindWatchdogAuditReport = 30004
)

type EventSpace struct{}

func (es *EventSpace) IsAssetEvent(kind int) bool {
	return kind == KindAssetEvent
}

func (es *EventSpace) IsRevocation(kind int) bool {
	return kind == KindRevocation
}

func (es *EventSpace) IsCheckpoint(kind int) bool {
	return kind == KindL2Checkpoint
}

func (es *EventSpace) IsWatchdogReport(kind int) bool {
	return kind == KindWatchdogAuditReport
}
