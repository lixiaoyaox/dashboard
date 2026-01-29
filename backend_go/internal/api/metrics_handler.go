package api

import (
	"net/http"
	"time"
)

func (s *Server) handleLatestMetrics(w http.ResponseWriter, r *http.Request) {
	metrics, err := s.metrics.Latest(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	resp := MetricsResponse{Data: metrics, Timestamp: time.Now()}
	writeJSON(w, http.StatusOK, resp)
}

func (s *Server) handleTrend(w http.ResponseWriter, r *http.Request) {
	window := parseQueryInt(r, "window", 12)
	if window < 3 {
		window = 3
	}
	points, err := s.metrics.Trend(r.Context(), window)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	trend := make([]TrendPoint, 0, len(points))
	for _, point := range points {
		trend = append(trend, TrendPoint{
			Timestamp: point.CreatedAt,
			Revenue:   point.Revenue,
		})
	}
	writeJSON(w, http.StatusOK, TrendResponse{Data: trend})
}

func (s *Server) handleSimulateMetrics(w http.ResponseWriter, r *http.Request) {
	next, err := s.metrics.Simulate(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"data": next})
}
