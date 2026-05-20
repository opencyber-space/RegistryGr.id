package query

import (
	"context"
	"errors"
)

type L1RelayReader interface {
	Query(ctx context.Context, req QueryRequest) (QueryResponse, error)
}

type FallbackReader struct {
	l1Relays []L1RelayReader
}

func NewFallbackReader(l1Relays []L1RelayReader) *FallbackReader {
	return &FallbackReader{l1Relays: l1Relays}
}

func (fr *FallbackReader) Read(ctx context.Context, req QueryRequest) (QueryResponse, error) {
	var lastErr error
	for _, relay := range fr.l1Relays {
		resp, err := relay.Query(ctx, req)
		if err == nil {
			return resp, nil
		}
		lastErr = err
	}
	if lastErr != nil {
		return QueryResponse{}, lastErr
	}
	return QueryResponse{}, errors.New("no l1 relays available")
}
