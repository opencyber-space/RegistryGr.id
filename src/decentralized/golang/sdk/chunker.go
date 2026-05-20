package sdk

import (
	"io"
)

const defaultChunkSize = 4 * 1024 * 1024

type Chunk struct {
	Index  int
	Offset int64
	Length int
	Data   []byte
}

type Chunker struct {
	chunkSize int
}

func NewChunker() *Chunker {
	return &Chunker{chunkSize: defaultChunkSize}
}

func (c *Chunker) Split(data []byte) ([]Chunk, error) {
	var chunks []Chunk
	total := len(data)
	index := 0
	offset := 0
	for offset < total {
		end := offset + c.chunkSize
		if end > total {
			end = total
		}
		chunk := Chunk{
			Index:  index,
			Offset: int64(offset),
			Length: end - offset,
			Data:   data[offset:end],
		}
		chunks = append(chunks, chunk)
		offset = end
		index++
	}
	return chunks, nil
}

func (c *Chunker) SplitReader(r io.Reader) ([]Chunk, error) {
	var chunks []Chunk
	buf := make([]byte, c.chunkSize)
	index := 0
	var offset int64
	for {
		n, err := io.ReadFull(r, buf)
		if n > 0 {
			data := make([]byte, n)
			copy(data, buf[:n])
			chunks = append(chunks, Chunk{
				Index:  index,
				Offset: offset,
				Length: n,
				Data:   data,
			})
			offset += int64(n)
			index++
		}
		if err == io.EOF || err == io.ErrUnexpectedEOF {
			break
		}
		if err != nil {
			return nil, err
		}
	}
	return chunks, nil
}

func (c *Chunker) AlignedRanges(chunks []Chunk) [][2]int64 {
	ranges := make([][2]int64, len(chunks))
	for i, ch := range chunks {
		ranges[i] = [2]int64{ch.Offset, ch.Offset + int64(ch.Length) - 1}
	}
	return ranges
}
