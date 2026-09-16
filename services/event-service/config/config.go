package config

import (
	"fmt"

	"github.com/caarlos0/env/v11"
	"github.com/joho/godotenv"
)

type (
	// Config -.
	Config struct {
		App     app
		HTTP    http
		Log     log
		PG      pg
		GRPC    grpc
		Metrics metrics
		Swagger swagger
		Tracing tracing
	}

	// App -.
	app struct {
		Name    string `env:"APP_NAME,required" envDefault:"event-service"`
		Version string `env:"APP_VERSION,required" envDefault:"1.0.0"`
	}

	// HTTP -.
	http struct {
		Port           string `env:"HTTP_PORT,required" envDefault:"3002"`
		UsePreforkMode bool   `env:"HTTP_USE_PREFORK_MODE" envDefault:"false"`
	}

	// Log -.
	log struct {
		Level string `env:"LOG_LEVEL,required" envDefault:"debug"`
	}

	// PG -.
	pg struct {
		PoolMax int    `env:"PG_POOL_MAX,required" envDefault:"25"`
		URL     string `env:"PG_URL,required"`
	}

	// GRPC -.
	grpc struct {
		Port string `env:"GRPC_PORT,required" envDefault:"50052"`
	}

	// Metrics -.
	metrics struct {
		Enabled bool `env:"METRICS_ENABLED" envDefault:"true"`
	}

	// Swagger -.
	swagger struct {
		Enabled bool `env:"SWAGGER_ENABLED" envDefault:"false"`
	}

	// Tracing -.
	tracing struct {
		Enabled      bool    `env:"TRACING_ENABLED" envDefault:"false"`
		OTLPEndpoint string  `env:"TRACING_OTLP_ENDPOINT" envDefault:"localhost:4317"`
		OTLPInsecure bool    `env:"TRACING_OTLP_INSECURE" envDefault:"true"`
		SampleRate   float64 `env:"TRACING_SAMPLE_RATE" envDefault:"0.1"`
	}
)

// NewConfig returns app config.
func NewConfig() (*Config, error) {
	_ = godotenv.Load()

	cfg := &Config{}
	if err := env.Parse(cfg); err != nil {
		return nil, fmt.Errorf("config error: %w", err)
	}

	return cfg, nil
}
