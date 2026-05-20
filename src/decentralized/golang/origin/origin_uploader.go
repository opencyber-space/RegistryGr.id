package origin

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"
)

type OriginUploader struct {
	gatewayURL string
	client     *http.Client
	chunkSize  int
}

func NewOriginUploader(gatewayURL string) *OriginUploader {
	return &OriginUploader{
		gatewayURL: gatewayURL,
		client:     &http.Client{Timeout: 60 * time.Second},
		chunkSize:  4 * 1024 * 1024,
	}
}

func (u *OriginUploader) Upload(ctx context.Context, data []byte, assetID string) error {
	total := len(data)
	offset := 0
	for offset < total {
		end := offset + u.chunkSize
		if end > total {
			end = total
		}
		chunk := data[offset:end]
		if err := u.uploadChunk(ctx, assetID, int64(offset), int64(total-1), chunk); err != nil {
			return fmt.Errorf("upload chunk at offset %d: %w", offset, err)
		}
		offset = end
	}
	return u.commitUpload(ctx, assetID, data)
}

func (u *OriginUploader) uploadChunk(ctx context.Context, assetID string, start, end int64, data []byte) error {
	url := fmt.Sprintf("%s/upload/%s", u.gatewayURL, assetID)
	req, err := http.NewRequestWithContext(ctx, http.MethodPut, url, byteReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Range", fmt.Sprintf("bytes %d-%d/*", start, end))
	req.Header.Set("Content-Length", strconv.Itoa(len(data)))
	resp, err := u.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return errors.New("upload chunk failed")
	}
	return nil
}

func (u *OriginUploader) commitUpload(ctx context.Context, assetID string, data []byte) error {
	url := fmt.Sprintf("%s/upload/%s/commit", u.gatewayURL, assetID)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, nil)
	if err != nil {
		return err
	}
	resp, err := u.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return errors.New("commit upload failed")
	}
	return nil
}

type byteReaderImpl struct {
	data   []byte
	offset int
}

func byteReader(data []byte) io.Reader {
	return &byteReaderImpl{data: data}
}

func (b *byteReaderImpl) Read(p []byte) (int, error) {
	if b.offset >= len(b.data) {
		return 0, io.EOF
	}
	n := copy(p, b.data[b.offset:])
	b.offset += n
	return n, nil
}
