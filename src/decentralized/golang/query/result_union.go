package query

import "sort"

type ResultUnion struct{}

func NewResultUnion() *ResultUnion {
	return &ResultUnion{}
}

func (ru *ResultUnion) Merge(responses []QueryResponse) QueryResponse {
	seen := make(map[string]AssetResult)
	for _, resp := range responses {
		for _, asset := range resp.Assets {
			existing, ok := seen[asset.ID]
			if !ok || asset.Version > existing.Version {
				seen[asset.ID] = asset
			}
		}
	}
	merged := make([]AssetResult, 0, len(seen))
	for _, asset := range seen {
		merged = append(merged, asset)
	}
	sort.Slice(merged, func(i, j int) bool {
		return merged[i].Version > merged[j].Version
	})
	return QueryResponse{Assets: merged}
}
