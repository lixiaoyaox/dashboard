package api

import (
	"encoding/json"
	"net/http"
)

func (s *Server) handleLatestInsights(w http.ResponseWriter, r *http.Request) {
	limit := parseQueryInt(r, "limit", 6)
	if limit < 1 {
		limit = 6
	}
	items, err := s.insights.Latest(r.Context(), limit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	writeJSON(w, http.StatusOK, InsightsResponse{Data: items})
}

func (s *Server) handleCreateInsight(w http.ResponseWriter, r *http.Request) {
	var payload InsightRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	insight, err := s.insights.Create(r.Context(), payload.MetricKey)
	if err != nil {
		writeError(w, http.StatusBadGateway, err)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"data": insight})
}
