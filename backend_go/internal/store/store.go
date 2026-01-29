package store

import (
  "context"
  "database/sql"
  "errors"
  "time"
  
  "mydashboard-backend/internal/models"
)

type Store struct {
  db *sql.DB
}

func New(db *sql.DB) *Store {
  return &Store{db: db}
}

func (s *Store) LatestMetrics(ctx context.Context) (models.Metrics, error) {
  const query = `
    SELECT revenue, growth, sentiment, backlog, created_at
    FROM metrics_snapshot
    ORDER BY created_at DESC
    LIMIT 1
  `
  var metrics models.Metrics
  err := s.db.QueryRowContext(ctx, query).Scan(
    &metrics.Revenue,
    &metrics.Growth,
    &metrics.Sentiment,
    &metrics.Backlog,
    &metrics.CreatedAt,
  )
  if errors.Is(err, sql.ErrNoRows) {
    return models.Metrics{}, nil
  }
  return metrics, err
}

func (s *Store) InsertMetrics(ctx context.Context, metrics models.Metrics) error {
  return s.InsertMetricsAt(ctx, metrics)
}

func (s *Store) InsertMetricsAt(ctx context.Context, metrics models.Metrics) error {
  const query = `
    INSERT INTO metrics_snapshot (revenue, growth, sentiment, backlog, created_at)
    VALUES (?, ?, ?, ?, ?)
  `
  _, err := s.db.ExecContext(ctx, query,
    metrics.Revenue,
    metrics.Growth,
    metrics.Sentiment,
    metrics.Backlog,
    metrics.CreatedAt,
  )
  return err
}

func (s *Store) Trend(ctx context.Context, limit int) ([]models.Metrics, error) {
  const query = `
    SELECT revenue, growth, sentiment, backlog, created_at
    FROM metrics_snapshot
    ORDER BY created_at DESC
    LIMIT ?
  `
  rows, err := s.db.QueryContext(ctx, query, limit)
  if err != nil {
    return nil, err
  }
  defer rows.Close()

  var points []models.Metrics
  for rows.Next() {
    var metrics models.Metrics
    if err := rows.Scan(
      &metrics.Revenue,
      &metrics.Growth,
      &metrics.Sentiment,
      &metrics.Backlog,
      &metrics.CreatedAt,
    ); err != nil {
      return nil, err
    }
    points = append(points, metrics)
  }
  if err := rows.Err(); err != nil {
    return nil, err
  }

  for i, j := 0, len(points)-1; i < j; i, j = i+1, j-1 {
    points[i], points[j] = points[j], points[i]
  }

  return points, nil
}

func (s *Store) LatestInsights(ctx context.Context, limit int) ([]models.Insight, error) {
  const query = `
    SELECT id, title, message, source, created_at
    FROM insights
    ORDER BY created_at DESC
    LIMIT ?
  `
  rows, err := s.db.QueryContext(ctx, query, limit)
  if err != nil {
    return nil, err
  }
  defer rows.Close()

  var items []models.Insight
  for rows.Next() {
    var insight models.Insight
    if err := rows.Scan(
      &insight.ID,
      &insight.Title,
      &insight.Message,
      &insight.Source,
      &insight.CreatedAt,
    ); err != nil {
      return nil, err
    }
    items = append(items, insight)
  }
  if err := rows.Err(); err != nil {
    return nil, err
  }

  return items, nil
}

func (s *Store) InsertInsight(ctx context.Context, insight models.Insight) (models.Insight, error) {
  const query = `
    INSERT INTO insights (title, message, source)
    VALUES (?, ?, ?)
  `
  result, err := s.db.ExecContext(ctx, query,
    insight.Title,
    insight.Message,
    insight.Source,
  )
  if err != nil {
    return models.Insight{}, err
  }
  id, err := result.LastInsertId()
  if err != nil {
    return models.Insight{}, err
  }
  insight.ID = id
  insight.CreatedAt = time.Now()
  return insight, nil
}

