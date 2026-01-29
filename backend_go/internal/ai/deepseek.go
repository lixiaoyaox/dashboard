package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"
)

type AIChatBot interface {
	Chat(ctx context.Context, systemPrompt, userPrompt string) (string, error)
}

type Logger interface {
	Printf(format string, args ...any)
}

type DeepSeekClient struct {
	baseURL    string
	apiKey     string
	model      string
	httpClient *http.Client
	logger     Logger
}

type deepSeekMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type deepSeekRequest struct {
	Model       string            `json:"model"`
	Messages    []deepSeekMessage `json:"messages"`
	MaxTokens   int               `json:"max_tokens,omitempty"`
	Temperature float64           `json:"temperature,omitempty"`
	Stream      bool              `json:"stream"`
}

type deepSeekResponse struct {
	Choices []struct {
		Message deepSeekMessage `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

func NewDeepSeekClient(baseURL, apiKey, model string) *DeepSeekClient {
	trimmed := strings.TrimRight(baseURL, "/")
	return &DeepSeekClient{
		baseURL: trimmed,
		apiKey:  apiKey,
		model:   model,
		httpClient: &http.Client{
			Timeout: 20 * time.Second,
		},
		logger: log.New(io.Discard, "", 0),
	}
}

func (c *DeepSeekClient) Chat(ctx context.Context, systemPrompt, userPrompt string) (string, error) {
	if c == nil {
		return "", errors.New("deepseek client not configured")
	}
	const maxAttempts = 3
	var lastErr error

	for attempt := 1; attempt <= maxAttempts; attempt++ {
		if err := ctx.Err(); err != nil {
			return "", err
		}

		endpoint := c.baseURL + "/chat/completions"
		payload := deepSeekRequest{
			Model: c.model,
			Messages: []deepSeekMessage{
				{Role: "system", Content: systemPrompt},
				{Role: "user", Content: userPrompt},
			},
			MaxTokens:   500,
			Temperature: 0.4,
			Stream:      false,
		}
		body, err := json.Marshal(payload)
		if err != nil {
			return "", err
		}

		c.logger.Printf("deepseek request attempt=%d system=%q user=%q", attempt, systemPrompt, userPrompt)
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
		if err != nil {
			return "", err
		}
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
		req.Header.Set("Content-Type", "application/json")

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
		} else {
			var decoded deepSeekResponse
			decodeErr := json.NewDecoder(resp.Body).Decode(&decoded)
			_ = resp.Body.Close()
			if decodeErr != nil {
				lastErr = decodeErr
			} else if resp.StatusCode >= 400 {
				if decoded.Error != nil && decoded.Error.Message != "" {
					lastErr = fmt.Errorf("deepseek error: %s", decoded.Error.Message)
				} else {
					lastErr = fmt.Errorf("deepseek error: status %d", resp.StatusCode)
				}
			} else if len(decoded.Choices) == 0 {
				lastErr = errors.New("deepseek returned no choices")
			} else {
				content := decoded.Choices[0].Message.Content
				c.logger.Printf("deepseek response attempt=%d content=%q", attempt, content)
				return content, nil
			}
		}

		if attempt < maxAttempts {
			sleep := time.Second * time.Duration(attempt)
			select {
			case <-time.After(sleep):
			case <-ctx.Done():
				return "", ctx.Err()
			}
		}
	}

	return "", lastErr
}

func (c *DeepSeekClient) WithLogger(logger Logger) *DeepSeekClient {
	if logger == nil {
		return c
	}
	c.logger = logger
	return c
}
