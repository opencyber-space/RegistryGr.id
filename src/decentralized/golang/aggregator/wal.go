package aggregator

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
)

type WALEntry struct {
	Seq   uint64
	Event Event
}

type WriteAheadLog struct {
	mu   sync.Mutex
	file *os.File
	seq  uint64
}

func NewWriteAheadLog(path string) (*WriteAheadLog, error) {
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		return nil, fmt.Errorf("open wal: %w", err)
	}
	return &WriteAheadLog{file: f}, nil
}

func (w *WriteAheadLog) Log(event Event) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.seq++
	entry := WALEntry{Seq: w.seq, Event: event}
	data, _ := json.Marshal(entry)
	data = append(data, '\n')
	w.file.Write(data)
}

func (w *WriteAheadLog) Replay() ([]WALEntry, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.file.Seek(0, 0)
	var entries []WALEntry
	dec := json.NewDecoder(w.file)
	for dec.More() {
		var entry WALEntry
		if err := dec.Decode(&entry); err != nil {
			break
		}
		entries = append(entries, entry)
	}
	return entries, nil
}

func (w *WriteAheadLog) Close() {
	w.file.Close()
}
