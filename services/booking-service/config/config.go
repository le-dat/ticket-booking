package config

import (
	"fmt"
	"time"

	"github.com/caarlos0/env/v11"
	"github.com/joho/godotenv"
)

type (
	// Config -.
	Config struct {
		App          App
		HTTP         HTTP
		Log          Log
		PG           PG
		Redis        Redis
		Kafka        Kafka
		EventService EventService
		Booking      Booking
		Metrics      Metrics
		Swagger      Swagger
		Tracing      Tracing
	}

	// App -.
	App struct {
		Name    string `env:"APP_NAME,required" envDefault:"booking-service"`
		Version string `env:"APP_VERSION,required" envDefault:"1.0.0"`
	}

	// HTTP -.
	HTTP struct {
		Port           string `env:"HTTP_PORT,required" envDefault:"3003"`
		UsePreforkMode bool   `env:"HTTP_USE_PREFORK_MODE" envDefault:"false"`
	}

	// Log -.
	Log struct {
		Level string `env:"LOG_LEVEL,required" envDefault:"debug"`
	}

	// PG -.
	PG struct {
		PoolMax int    `env:"PG_POOL_MAX,required" envDefault:"25"`
		URL     string `env:"PG_URL,required"`
	}

	// Redis -.
	Redis struct {
		Addr     string `env:"REDIS_ADDR" envDefault:"localhost:6379"`
		Password string `env:"REDIS_PASSWORD" envDefault:"redis_secret_123"`
		DB       int    `env:"REDIS_DB" envDefault:"0"`
	}

	// Kafka -.
	Kafka struct {
		Brokers             []string      `env:"KAFKA_BROKERS" envDefault:"localhost:29092"`
		TopicBookingEvents  string        `env:"KAFKA_TOPIC_BOOKING_EVENTS" envDefault:"booking-events"`
		TopicPaymentEvents  string        `env:"KAFKA_TOPIC_PAYMENT_EVENTS" envDefault:"payment-events"`
		ConsumerGroupID     string        `env:"KAFKA_CONSUMER_GROUP_ID" envDefault:"booking-service-group"`
		OutboxBatchSize     int           `env:"KAFKA_OUTBOX_BATCH_SIZE" envDefault:"20"`
		OutboxFlushInterval time.Duration `env:"KAFKA_OUTBOX_FLUSH_INTERVAL" envDefault:"1s"`
	}

	// EventService gRPC -.
	EventService struct {
		GRPCAddr string `env:"EVENT_SERVICE_GRPC_ADDR" envDefault:"localhost:50052"`
	}

	// Booking business configuration -.
	Booking struct {
		HoldDuration       time.Duration `env:"BOOKING_HOLD_DURATION" envDefault:"10m"`
		ExpiryPollInterval time.Duration `env:"BOOKING_EXPIRY_POLL_INTERVAL" envDefault:"5s"`
	}

	// Metrics -.
	Metrics struct {
		Enabled bool `env:"METRICS_ENABLED" envDefault:"true"`
	}

	// Swagger -.
	Swagger struct {
		Enabled bool `env:"SWAGGER_ENABLED" envDefault:"false"`
	}

	// Tracing -.
	Tracing struct {
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
