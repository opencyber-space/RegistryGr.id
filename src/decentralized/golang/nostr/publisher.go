package nostr

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"
)

type SignedEvent struct {
	ID        string     `json:"id"`
	PubKey    string     `json:"pubkey"`
	CreatedAt int64      `json:"created_at"`
	Kind      int        `json:"kind"`
	Content   string     `json:"content"`
	Sig       string     `json:"sig"`
	Tags      [][]string `json:"tags"`
}

type Publisher struct {
	relayURLs      []string
	minAcceptance  int
	client         *http.Client
	maxRetries     int
}

func NewPublisher(relayURLs []string, minAcceptance int) *Publisher {
	return &Publisher{
		relayURLs:     relayURLs,
		minAcceptance: minAcceptance,
		client:        &http.Client{Timeout: 10 * time.Second},
		maxRetries:    3,
	}
}

func (p *Publisher) PublishAll(ctx context.Context, events []SignedEvent) error {
	for _, event := range events {
		if err := p.publishOne(ctx, event); err != nil {
			return fmt.Errorf("publish event %s: %w", event.ID, err)
		}
	}
	return nil
}

func (p *Publisher) publishOne(ctx context.Context, event SignedEvent) error {
	var mu sync.Mutex
	accepted := 0
	var wg sync.WaitGroup

	for _, url := range p.relayURLs {
		wg.Add(1)
		go func(relayURL string) {
			defer wg.Done()
			if err := p.sendToRelay(ctx, relayURL, event); err == nil {
				mu.Lock()
				accepted++
				mu.Unlock()
			}
		}(url)
	}

	wg.Wait()
	if accepted < p.minAcceptance {
		return fmt.Errorf("only %d relays accepted event, need %d", accepted, p.minAcceptance)
	}
	return nil
}

func (p *Publisher) sendToRelay(ctx context.Context, relayURL string, event SignedEvent) error {
	payload, err := json.Marshal([]interface{}{"EVENT", event})
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, relayURL, strings.NewReader(string(payload)))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := p.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return errors.New("relay rejected event")
	}
	return nil
}

func (p *Publisher) PublishRevocation(ctx context.Context, eventID string, privKey []byte) error {
	revocation := SignedEvent{
		Kind:    5,
		Tags:    [][]string{{"e", eventID}},
		Content: "revoked",
	}
	return p.publishOne(ctx, revocation)
}
