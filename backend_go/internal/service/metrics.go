package service

import (
	"context"
	"log"
	"time"

	"mydashboard-backend/internal/models"
	"mydashboard-backend/internal/store"
)

type MetricsService struct {
	store     *store.Store
	simulator *Simulation
}

func NewMetricsService(store *store.Store, simulator *Simulation) *MetricsService {
	return &MetricsService{
		store:     store,
		simulator: simulator,
	}
}

func (s *MetricsService) Latest(ctx context.Context) (models.Metrics, error) {
	metrics, err := s.store.LatestMetrics(ctx)
	if err != nil {
		return models.Metrics{}, err
	}
	if metrics.CreatedAt.IsZero() {
		metrics = defaultMetrics()
		if err := s.store.InsertMetricsAt(ctx, metrics); err != nil {
			log.Printf("seed metrics failed: %v", err)
		}
	}
	return metrics, nil
}

func (s *MetricsService) Trend(ctx context.Context, window int) ([]models.Metrics, error) {
	points, err := s.store.Trend(ctx, window)
	if err != nil {
		return nil, err
	}
	if len(points) == 0 {
		points = seedTrendMetrics()
		for _, point := range points {
			if err := s.store.InsertMetricsAt(ctx, point); err != nil {
				log.Printf("seed trend failed: %v", err)
				break
			}
		}
	}
	return points, nil
}

func (s *MetricsService) Simulate(ctx context.Context) (models.Metrics, error) {
	metrics, err := s.store.LatestMetrics(ctx)
	if err != nil {
		return models.Metrics{}, err
	}
	if metrics.CreatedAt.IsZero() {
		metrics = defaultMetrics()
	}
	next := s.simulator.NextMetrics(metrics)
	if err := s.store.InsertMetrics(ctx, next); err != nil {
		return models.Metrics{}, err
	}
	return next, nil
}

func (s *MetricsService) StartSimulation(ctx context.Context, metricEvery, insightEvery time.Duration, insights *InsightsService) {
	metricsTicker := time.NewTicker(metricEvery)
	insightTicker := time.NewTicker(insightEvery)
	defer metricsTicker.Stop()
	defer insightTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-metricsTicker.C:
			if _, err := s.Simulate(ctx); err != nil {
				log.Printf("simulate metrics failed: %v", err)
			}
		case <-insightTicker.C:
			metrics, err := s.store.LatestMetrics(ctx)
			if err != nil {
				continue
			}
			if metrics.CreatedAt.IsZero() {
				metrics = defaultMetrics()
			}
			if _, err := insights.GenerateAuto(ctx, metrics); err != nil {
				log.Printf("simulate insight failed: %v", err)
			}
		}
	}
}

func defaultMetrics() models.Metrics {
	return models.Metrics{
		Revenue:   4.82,
		Growth:    18.6,
		Sentiment: 72,
		Backlog:   128,
		CreatedAt: time.Now(),
	}
}

func seedTrendMetrics() []models.Metrics {
	base := defaultMetrics()
	var points []models.Metrics
	for i := 0; i < 12; i++ {
		value := 55 + float64(i)*1.8 + (float64(i)/1.8)*2.0
		points = append(points, models.Metrics{
			Revenue:   value / 10,
			Growth:    base.Growth,
			Sentiment: base.Sentiment,
			Backlog:   base.Backlog,
			CreatedAt: time.Now().Add(time.Duration(i-12) * time.Minute),
		})
	}
	return points
}
