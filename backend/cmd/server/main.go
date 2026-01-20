package main

import (
  "context"
  "database/sql"
  "log"
  "net/http"
  "os"
  "os/signal"
  "strconv"
  "syscall"
  "time"

  _ "github.com/go-sql-driver/mysql"

  "mydashboard-backend/internal/api"
  "mydashboard-backend/internal/store"
)

func main() {
  cfg := loadConfig()
//读取环境变量
  db, err := sql.Open("mysql", cfg.dsn)
  if err != nil {
    log.Fatalf("db open failed: %v", err)
  }
  db.SetConnMaxLifetime(5 * time.Minute)
  db.SetMaxOpenConns(10)
  db.SetMaxIdleConns(5)

  if err := db.Ping(); err != nil {
    log.Fatalf("db ping failed: %v", err)
  }

  apiServer := api.NewServer(store.New(db))
  httpServer := &http.Server{
    Addr:              cfg.addr,
    Handler:           apiServer.Routes(cfg.allowedOrigins),
    ReadHeaderTimeout: 5 * time.Second,
  }

  ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
  defer stop()//不知道怎么停下来的

  if cfg.enableSimulation {
    go apiServer.StartSimulation(ctx, cfg.metricsEvery, cfg.insightsEvery)
  }

  go func() {
    log.Printf("API listening on %s", cfg.addr)
    if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
      log.Fatalf("server error: %v", err)
    }
  }()

  <-ctx.Done()
  shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
  defer cancel()
  if err := httpServer.Shutdown(shutdownCtx); err != nil {
    log.Printf("shutdown error: %v", err)
  }
}

type config struct {
  addr             string
  dsn              string
  allowedOrigins   string
  enableSimulation bool
  metricsEvery     time.Duration
  insightsEvery    time.Duration
}

func loadConfig() config {
  port := getEnv("APP_PORT", "8080")
  addr := ":" + port

  host := getEnv("DB_HOST", "127.0.0.1")
  dbPort := getEnv("DB_PORT", "3306")
  user := getEnv("DB_USER", "root")
  pass := getEnv("DB_PASS", "123456")
  name := getEnv("DB_NAME", "dashboard")
  dsn := user + ":" + pass + "@tcp(" + host + ":" + dbPort + ")/" + name + "?parseTime=true&charset=utf8mb4&loc=Local"

  enableSimulation := getEnv("ENABLE_SIMULATION", "true") == "true"
  metricsEvery := parseDurationEnv("SIM_METRICS_EVERY", 1*time.Second)
  insightsEvery := parseDurationEnv("SIM_INSIGHTS_EVERY", 5*time.Second)
  allowedOrigins := getEnv("ALLOWED_ORIGINS", "*")

  return config{
    addr:             addr,
    dsn:              dsn,
    allowedOrigins:   allowedOrigins,
    enableSimulation: enableSimulation,
    metricsEvery:     metricsEvery,
    insightsEvery:    insightsEvery,
  }
}

func getEnv(key, fallback string) string {
  if value, ok := os.LookupEnv(key); ok {
    return value
  }
  return fallback
}

func parseDurationEnv(key string, fallback time.Duration) time.Duration {
  value := getEnv(key, "")
  if value == "" {
    return fallback
  }
  parsed, err := time.ParseDuration(value)
  if err == nil {
    return parsed
  }
  if seconds, err := strconv.Atoi(value); err == nil {
    return time.Duration(seconds) * time.Second
  }
  return fallback
}

