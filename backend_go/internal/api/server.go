package api

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"mydashboard-backend/internal/models"
	"mydashboard-backend/internal/service"
)

type Server struct {
	metrics  *service.MetricsService
	insights *service.InsightsService
}

type MetricsResponse struct {
	Data      models.Metrics `json:"data"`
	Timestamp time.Time      `json:"timestamp"`
}

type TrendPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Revenue   float64   `json:"revenue"`
}

type TrendResponse struct {
	Data []TrendPoint `json:"data"`
}

type InsightsResponse struct {
	Data []models.Insight `json:"data"`
}

type InsightRequest struct {
	MetricKey string `json:"metricKey"`
}

func NewServer(metrics *service.MetricsService, insights *service.InsightsService) *Server {
	return &Server{
		metrics:  metrics,
		insights: insights,
	}
}

func (s *Server) Routes(allowedOrigins string) http.Handler {
	router := chi.NewRouter()
	router.Use(middleware.RequestID)
	router.Use(middleware.RealIP)
	router.Use(middleware.Recoverer)
	router.Use(middleware.Logger)
	router.Use(corsMiddleware(allowedOrigins))

	router.Get("/healthz", s.handleHealth)
	router.Route("/api", func(r chi.Router) {
		r.Get("/metrics/latest", s.handleLatestMetrics)
		r.Get("/metrics/trend", s.handleTrend)
		r.Get("/insights/latest", s.handleLatestInsights)
		r.Post("/insights", s.handleCreateInsight)
		r.Post("/metrics/simulate", s.handleSimulateMetrics)
	})

	return router
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) StartSimulation(ctx context.Context, metricEvery, insightEvery time.Duration) {
	if s.metrics == nil || s.insights == nil {
		log.Printf("simulation skipped: services not configured")
		return
	}
	s.metrics.StartSimulation(ctx, metricEvery, insightEvery, s.insights)
}
