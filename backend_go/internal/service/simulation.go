package service

import (
	"math/rand"
	"sync"
	"time"

	"mydashboard-backend/internal/models"
)

type Simulation struct {
	rng *rand.Rand
	mu  sync.Mutex
}

func NewSimulation() *Simulation {
	return &Simulation{
		rng: rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

func (s *Simulation) NextMetrics(previous models.Metrics) models.Metrics {
	s.mu.Lock()
	defer s.mu.Unlock()

	return models.Metrics{
		Revenue:   clamp(previous.Revenue+(s.rng.Float64()-0.35)*0.12, 3.9, 6.2),
		Growth:    clamp(previous.Growth+(s.rng.Float64()-0.45)*1.6, 10, 28),
		Sentiment: clamp(previous.Sentiment+(s.rng.Float64()-0.5)*2.4, 58, 90),
		Backlog:   int(clamp(float64(previous.Backlog)+(s.rng.Float64()-0.4)*6, 95, 180)),
		CreatedAt: time.Now(),
	}
}

func clamp(value, min, max float64) float64 {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
