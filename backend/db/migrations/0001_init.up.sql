CREATE TABLE IF NOT EXISTS metrics_snapshot (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  revenue DECIMAL(6,2) NOT NULL,
  growth DECIMAL(5,2) NOT NULL,
  sentiment DECIMAL(5,2) NOT NULL,
  backlog INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_metrics_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS insights (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  source VARCHAR(16) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_insights_created_at (created_at)
);
