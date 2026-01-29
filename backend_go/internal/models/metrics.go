package models

import "time"

type Metrics struct {
	Revenue   float64   `json:"revenue"`
	Growth    float64   `json:"growth"`
	Sentiment float64   `json:"sentiment"`
	Backlog   int       `json:"backlog"`
	CreatedAt time.Time `json:"created_at"`
}
