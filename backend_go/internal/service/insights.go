package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strconv"
	"strings"

	"mydashboard-backend/internal/ai"
	"mydashboard-backend/internal/models"
	"mydashboard-backend/internal/store"
)

type InsightsService struct {
	store *store.Store
	ai    ai.AIChatBot
}

func NewInsightsService(store *store.Store, bot ai.AIChatBot) *InsightsService {
	return &InsightsService{
		store: store,
		ai:    bot,
	}
}

func (s *InsightsService) Latest(ctx context.Context, limit int) ([]models.Insight, error) {
	items, err := s.store.LatestInsights(ctx, limit)
	if err != nil {
		return nil, err
	}
	if len(items) == 0 {
		metrics, err := s.store.LatestMetrics(ctx)
		if err != nil {
			return nil, err
		}
		if metrics.CreatedAt.IsZero() {
			metrics = defaultMetrics()
		}
		seed, err := s.generateInsight(ctx, metrics, "overview", "auto")
		if err != nil {
			return nil, err
		}
		items = []models.Insight{seed}
	}
	return items, nil
}

func (s *InsightsService) Create(ctx context.Context, metricKey string) (models.Insight, error) {
	metrics, err := s.store.LatestMetrics(ctx)
	if err != nil {
		return models.Insight{}, err
	}
	if metrics.CreatedAt.IsZero() {
		metrics = defaultMetrics()
	}
	return s.generateInsight(ctx, metrics, metricKey, "metric")
}

func (s *InsightsService) GenerateAuto(ctx context.Context, metrics models.Metrics) (models.Insight, error) {
	return s.generateInsight(ctx, metrics, "overview", "auto")
}

func (s *InsightsService) generateInsight(ctx context.Context, metrics models.Metrics, focusKey string, source string) (models.Insight, error) {
	if s.ai == nil {
		return models.Insight{}, errors.New("ai client not configured")
	}
	trend, err := s.store.Trend(ctx, 12)
	if err != nil {
		return models.Insight{}, err
	}
	systemPrompt, userPrompt := buildDeepSeekPrompt(metrics, trend, focusKey)
	message, err := s.ai.Chat(ctx, systemPrompt, userPrompt)
	if err != nil {
		return models.Insight{}, err
	}
	message = normalizeInsight(message, 300)
	return s.store.InsertInsight(ctx, models.Insight{
		Title:   "AI 战略顾问",
		Message: message,
		Source:  source,
	})
}

func buildDeepSeekPrompt(metrics models.Metrics, trend []models.Metrics, focusKey string) (string, string) {
	systemPrompt := "你是企业战略分析师。基于提供的数据做真实、克制的分析，不编造背景或外部事实。必须输出严格JSON：{\"analysis\":\"...\",\"suggestions\":[\"...\",\"...\"]}。analysis 为连续中文正文，不要标题、分段、列表、符号或Markdown。suggestions 为 2-4 条行动建议短句。总长度不超过300字。"

	focus := focusKey
	if focus == "" {
		focus = "overview"
	}

	trendSummary := "趋势数据不足"
	if len(trend) >= 2 {
		first := trend[0]
		last := trend[len(trend)-1]
		trendSummary = "趋势起止：" +
			first.CreatedAt.Format("15:04") + " -> " + last.CreatedAt.Format("15:04") +
			"，营收 " + formatDelta(first.Revenue, last.Revenue, "B") +
			"，增长 " + formatDelta(first.Growth, last.Growth, "%") +
			"，情绪 " + formatDelta(first.Sentiment, last.Sentiment, "%") +
			"，积压 " + formatDelta(float64(first.Backlog), float64(last.Backlog), "K")
	}

	userPrompt := "公司实时指标：营收 " +
		formatFloat(metrics.Revenue, 2) + "B，增长 " + formatFloat(metrics.Growth, 1) +
		"%，情绪 " + formatFloat(metrics.Sentiment, 0) + "%，积压 " +
		strconv.Itoa(metrics.Backlog) + "K。更新时间：" + metrics.CreatedAt.Format("15:04") +
		"。关注点：" + focus + "。" + trendSummary +
		"。请给出真实分析与行动建议。"

	return systemPrompt, userPrompt
}

func formatDelta(start, end float64, unit string) string {
	delta := end - start
	prefix := "+"
	if delta < 0 {
		prefix = ""
	}
	return prefix + formatFloat(delta, 2) + unit
}

func formatFloat(value float64, decimals int) string {
	format := "%." + strconv.Itoa(decimals) + "f"
	return fmt.Sprintf(format, value)
}

func normalizeInsight(message string, maxRunes int) string {
	trimmed := strings.TrimSpace(message)
	trimmed = tryFormatInsightJSON(trimmed)
	trimmed = stripMarkdown(trimmed)
	trimmed = strings.ReplaceAll(trimmed, "\n", " ")
	trimmed = strings.Join(strings.Fields(trimmed), " ")
	runes := []rune(trimmed)
	if len(runes) > maxRunes {
		return string(runes[:maxRunes])
	}
	return trimmed
}

func stripMarkdown(value string) string {
	replacer := strings.NewReplacer(
		"#", "",
		"*", "",
		"`", "",
		"_", "",
		">", "",
		"- ", "",
		"+ ", "",
		"•", "",
		"|", " ",
		"[", "",
		"]", "",
		"(", "",
		")", "",
	)
	return replacer.Replace(value)
}

type insightJSON struct {
	Analysis    string   `json:"analysis"`
	Suggestions []string `json:"suggestions"`
}

func tryFormatInsightJSON(value string) string {
	raw := strings.TrimSpace(value)
	if raw == "" {
		return raw
	}
	if strings.HasPrefix(raw, "```") {
		raw = strings.TrimPrefix(raw, "```json")
		raw = strings.TrimPrefix(raw, "```")
		raw = strings.TrimSuffix(raw, "```")
		raw = strings.TrimSpace(raw)
	}
	start := strings.Index(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start == -1 || end == -1 || end <= start {
		return value
	}
	raw = raw[start : end+1]

	var parsed insightJSON
	if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
		return value
	}
	analysis := strings.TrimSpace(parsed.Analysis)
	var suggestions []string
	for _, s := range parsed.Suggestions {
		s = strings.TrimSpace(s)
		if s != "" {
			suggestions = append(suggestions, s)
		}
		if len(suggestions) >= 4 {
			break
		}
	}
	if analysis == "" && len(suggestions) == 0 {
		return value
	}
	if len(suggestions) == 0 {
		return analysis
	}
	return analysis + " 建议：" + strings.Join(suggestions, "；")
}
