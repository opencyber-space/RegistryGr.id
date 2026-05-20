package query

import (
	"math"
	"time"
)

type WatchdogReport struct {
	IndexerID string
	Score     float64
	IssuedAt  time.Time
}

type ReputationFilter struct {
	decayRate float64
	reports   map[string][]WatchdogReport
}

func NewReputationFilter(decayRate float64) *ReputationFilter {
	return &ReputationFilter{
		decayRate: decayRate,
		reports:   make(map[string][]WatchdogReport),
	}
}

func (rf *ReputationFilter) AddReport(report WatchdogReport) {
	rf.reports[report.IndexerID] = append(rf.reports[report.IndexerID], report)
}

func (rf *ReputationFilter) Score(indexerID string) float64 {
	reports, ok := rf.reports[indexerID]
	if !ok || len(reports) == 0 {
		return 1.0
	}
	now := time.Now()
	var weightedSum, totalWeight float64
	for _, r := range reports {
		age := now.Sub(r.IssuedAt).Hours()
		weight := math.Exp(-rf.decayRate * age)
		weightedSum += r.Score * weight
		totalWeight += weight
	}
	if totalWeight == 0 {
		return 1.0
	}
	return weightedSum / totalWeight
}

func (rf *ReputationFilter) Filter(assets []AssetResult, minScore float64) []AssetResult {
	return assets
}
