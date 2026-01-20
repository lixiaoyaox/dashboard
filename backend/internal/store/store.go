package store

import (
  "context"
  "database/sql"
  "errors"
  "time"
)

type Metrics struct {
  Revenue   float64   `json:"revenue"`
  Growth    float64   `json:"growth"`
  Sentiment float64   `json:"sentiment"`
  Backlog   int       `json:"backlog"`
  CreatedAt time.Time `json:"created_at"`
}

type Insight struct {
  ID        int64     `json:"id"`
  Title     string    `json:"title"`
  Message   string    `json:"message"`
  Source    string    `json:"source"`
  CreatedAt time.Time `json:"created_at"`
}

type Store struct {
  db *sql.DB
}

func New(db *sql.DB) *Store {
  return &Store{db: db}
}

func (s *Store) LatestMetrics(ctx context.Context) (Metrics, error) {
  const query = `
    SELECT revenue, growth, sentiment, backlog, created_at
    FROM metrics_snapshot
    ORDER BY created_at DESC
    LIMIT 1
  `
  var metrics Metrics
  err := s.db.QueryRowContext(ctx, query).Scan(
    &metrics.Revenue,
    &metrics.Growth,
    &metrics.Sentiment,
    &metrics.Backlog,
    &metrics.CreatedAt,
  )
  if errors.Is(err, sql.ErrNoRows) {
    return Metrics{}, nil
  }
  return metrics, err
}

func (s *Store) InsertMetrics(ctx context.Context, metrics Metrics) error {
  return s.InsertMetricsAt(ctx, metrics)
}

func (s *Store) InsertMetricsAt(ctx context.Context, metrics Metrics) error {
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

func (s *Store) Trend(ctx context.Context, limit int) ([]Metrics, error) {
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

  var points []Metrics
  for rows.Next() {
    var metrics Metrics
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

func (s *Store) LatestInsights(ctx context.Context, limit int) ([]Insight, error) {
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

  var items []Insight
  for rows.Next() {
    var insight Insight
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

func (s *Store) InsertInsight(ctx context.Context, insight Insight) (Insight, error) {
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
    return Insight{}, err
  }
  id, err := result.LastInsertId()
  if err != nil {
    return Insight{}, err
  }
  insight.ID = id
  insight.CreatedAt = time.Now()
  return insight, nil
}

