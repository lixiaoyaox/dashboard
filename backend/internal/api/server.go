package api

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"math/rand"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"mydashboard-backend/internal/store"
)

type Server struct {
	store *store.Store
	rng   *rand.Rand
}

type MetricsResponse struct {
	Data      store.Metrics `json:"data"`
	Timestamp time.Time     `json:"timestamp"`
}

type TrendPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Revenue   float64   `json:"revenue"`
}

type TrendResponse struct {
	Data []TrendPoint `json:"data"`
}

type InsightsResponse struct {
	Data []store.Insight `json:"data"`
}

type InsightRequest struct {
	MetricKey string `json:"metricKey"`
}

func NewServer(store *store.Store) *Server {
	return &Server{
		store: store,
		rng:   rand.New(rand.NewSource(time.Now().UnixNano())),
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

func (s *Server) handleLatestMetrics(w http.ResponseWriter, r *http.Request) {
	metrics, err := s.store.LatestMetrics(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if metrics.CreatedAt.IsZero() {
		metrics = defaultMetrics()
		if err := s.store.InsertMetricsAt(r.Context(), metrics); err != nil {
			log.Printf("seed metrics failed: %v", err)
		}
	}
	resp := MetricsResponse{Data: metrics, Timestamp: time.Now()}
	writeJSON(w, http.StatusOK, resp)
}

func (s *Server) handleTrend(w http.ResponseWriter, r *http.Request) {
	window := parseQueryInt(r, "window", 12)
	if window < 3 {
		window = 3
	}
	points, err := s.store.Trend(r.Context(), window)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if len(points) == 0 {
		points = seedTrendMetrics()
		for _, point := range points {
			if err := s.store.InsertMetricsAt(r.Context(), point); err != nil {
				log.Printf("seed trend failed: %v", err)
				break
			}
		}
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

func (s *Server) handleLatestInsights(w http.ResponseWriter, r *http.Request) {
	limit := parseQueryInt(r, "limit", 6)
	if limit < 1 {
		limit = 6
	}
	items, err := s.store.LatestInsights(r.Context(), limit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if len(items) == 0 {
		seed, err := s.store.InsertInsight(r.Context(), store.Insight{
			Title:   "高管简报",
			Message: "全球表现高于计划，继续将市场投入对齐高动能区域。",
			Source:  "auto",
		})
		if err != nil {
			log.Printf("seed insight failed: %v", err)
			items = []store.Insight{
				{
					Title:     "高管简报",
					Message:   "全球表现高于计划，继续将市场投入对齐高动能区域。",
					Source:    "auto",
					CreatedAt: time.Now(),
				},
			}
		} else {
			items = []store.Insight{seed}
		}
	}
	writeJSON(w, http.StatusOK, InsightsResponse{Data: items})
}

func (s *Server) handleCreateInsight(w http.ResponseWriter, r *http.Request) {
	var payload InsightRequest
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}

	metrics, err := s.store.LatestMetrics(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if metrics.CreatedAt.IsZero() {
		metrics = defaultMetrics()
	}

	title, message := buildMetricInsight(payload.MetricKey, metrics)
	insight, err := s.store.InsertInsight(r.Context(), store.Insight{
		Title:   title,
		Message: message,
		Source:  "metric",
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}

	writeJSON(w, http.StatusOK, map[string]store.Insight{"data": insight})
}

func (s *Server) handleSimulateMetrics(w http.ResponseWriter, r *http.Request) {
	metrics, err := s.store.LatestMetrics(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	if metrics.CreatedAt.IsZero() {
		metrics = defaultMetrics()
	}
	next := simulateMetrics(s.rng, metrics)
	if err := s.store.InsertMetrics(r.Context(), next); err != nil {
		writeError(w, http.StatusInternalServerError, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]store.Metrics{"data": next})
}

func (s *Server) StartSimulation(ctx context.Context, metricEvery, insightEvery time.Duration) {
	metricsTicker := time.NewTicker(metricEvery)
	insightTicker := time.NewTicker(insightEvery)
	defer metricsTicker.Stop()
	defer insightTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-metricsTicker.C:
			metrics, err := s.store.LatestMetrics(ctx)
			if err != nil {
				continue
			}
			if metrics.CreatedAt.IsZero() {
				metrics = defaultMetrics()
			}
			next := simulateMetrics(s.rng, metrics)
			if err := s.store.InsertMetrics(ctx, next); err != nil {
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
			message := buildAutoInsight(metrics)
			if _, err := s.store.InsertInsight(ctx, store.Insight{
				Title:   "AI 战略顾问",
				Message: message,
				Source:  "auto",
			}); err != nil {
				log.Printf("simulate insight failed: %v", err)
			}
		}
	}
}

func corsMiddleware(allowedOrigins string) func(http.Handler) http.Handler {
	origins := strings.FieldsFunc(allowedOrigins, func(r rune) bool { return r == ',' })
	allowAll := allowedOrigins == "" || allowedOrigins == "*"
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if allowAll {
				w.Header().Set("Access-Control-Allow-Origin", "*")
			} else if origin != "" {
				for _, allowed := range origins {
					if strings.EqualFold(strings.TrimSpace(allowed), origin) {
						w.Header().Set("Access-Control-Allow-Origin", origin)
						break
					}
				}
			}
			w.Header().Set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func parseQueryInt(r *http.Request, key string, fallback int) int {
	value := r.URL.Query().Get(key)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}     

func writeError(w http.ResponseWriter, status int, err error) {
	if err == nil {
		err = errors.New("unknown error")
	}
	writeJSON(w, status, map[string]string{"error": err.Error()})
}

func defaultMetrics() store.Metrics {
	return store.Metrics{
		Revenue:   4.82,
		Growth:    18.6,
		Sentiment: 72,
		Backlog:   128,
		CreatedAt: time.Now(),
	}
}

func seedTrendMetrics() []store.Metrics {
	base := defaultMetrics()
	var points []store.Metrics
	for i := 0; i < 12; i++ {
		value := 55 + float64(i)*1.8 + (float64(i)/1.8)*2.0
		points = append(points, store.Metrics{
			Revenue:   value / 10,
			Growth:    base.Growth,
			Sentiment: base.Sentiment,
			Backlog:   base.Backlog,
			CreatedAt: time.Now().Add(time.Duration(i-12) * time.Minute),
		})
	}
	return points
}

func simulateMetrics(rng *rand.Rand, previous store.Metrics) store.Metrics {
	next := store.Metrics{
		Revenue:   clamp(previous.Revenue+(rng.Float64()-0.35)*0.12, 3.9, 6.2),
		Growth:    clamp(previous.Growth+(rng.Float64()-0.45)*1.6, 10, 28),
		Sentiment: clamp(previous.Sentiment+(rng.Float64()-0.5)*2.4, 58, 90),
		Backlog:   int(clamp(float64(previous.Backlog)+(rng.Float64()-0.4)*6, 95, 180)),
		CreatedAt: time.Now(),
	}
	return next
}

func buildMetricInsight(key string, metrics store.Metrics) (string, string) {
	switch strings.ToLower(key) {
	case "revenue":
		return "全球营收聚焦", "营收增速维持在当前高位，建议核心区域保持高端定价，拉美用组合包稳住份额。"
	case "growth":
		return "用户增长聚焦", "用户增长保持稳定，建议将获客预算倾向亚太，并在成熟市场加倍投入推荐裂变。"
	case "sentiment":
		return "情绪指数聚焦", "情绪指数稳定向好，EMEA 需提前布局公关以冲刺 75% 正面阈值。"
	case "backlog":
		return "未交付订单聚焦", "订单积压仍需关注，建议提升物流吞吐，降低高端 SKU 流失风险。"
	default:
		return "战略提示", "请在关键指标上保持资源集中度。"
	}
}

func buildAutoInsight(metrics store.Metrics) string {
	strength := "稳定"
	if metrics.Sentiment > 74 {
		strength = "强劲"
	} else if metrics.Sentiment < 66 {
		strength = "脆弱"
	}
	revenuePulse := "平稳"
	if metrics.Revenue > 5.1 {
		revenuePulse = "加速"
	} else if metrics.Revenue < 4.6 {
		revenuePulse = "走弱"
	}
	backlogRisk := "可控"
	if metrics.Backlog > 150 {
		backlogRisk = "上行"
	} else if metrics.Backlog < 120 {
		backlogRisk = "较低"
	}
	return "需求动能" + revenuePulse + "，舆情" + strength + "。积压风险" + backlogRisk + "，建议将履约能力倾向高毛利区域。"
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
