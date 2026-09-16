// Package app configures and runs booking-service application.
package app

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/redis/go-redis/v9"
	"github.com/zentrix-app/zentrix-backend-go-temp/config"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi"
	grpcClient "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/grpc"
	persistBooking "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/persistent/booking"
	redisRepo "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/redis"
	bookingUc "github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase/booking"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/worker"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/httpserver"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/postgres"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/tracing"
)

// Run creates objects via constructors and runs the application.
func Run(cfg *config.Config) {
	l := logger.New(cfg.Log.Level)

	ctx := context.Background()

	// 1. Tracing
	if cfg.Tracing.Enabled {
		shutdownTracing, err := tracing.New(ctx, tracing.Config{
			Enabled:     cfg.Tracing.Enabled,
			ServiceName: cfg.App.Name,
			Version:     cfg.App.Version,
			Endpoint:    cfg.Tracing.OTLPEndpoint,
			Insecure:    cfg.Tracing.OTLPInsecure,
			SampleRate:  cfg.Tracing.SampleRate,
		})
		if err != nil {
			l.Fatal(fmt.Errorf("app - Run - tracing.New: %w", err))
		}
		defer func() {
			if err := shutdownTracing(ctx); err != nil {
				l.Error(fmt.Errorf("app - Run - shutdownTracing: %w", err))
			}
		}()
	}

	// 2. PostgreSQL Connection
	pg, err := postgres.New(cfg.PG.URL, postgres.MaxPoolSize(cfg.PG.PoolMax))
	if err != nil {
		l.Fatal(fmt.Errorf("app - Run - postgres.New: %w", err))
	}
	defer pg.Close()

	// 3. Redis Connection
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.Redis.Addr,
		Password: cfg.Redis.Password,
		DB:       cfg.Redis.DB,
	})
	defer rdb.Close()

	// 4. gRPC Client kết nối event-service
	eventClient, err := grpcClient.NewEventServiceClient(cfg.EventService.GRPCAddr)
	if err != nil {
		l.Fatal(fmt.Errorf("app - Run - grpcClient.NewEventServiceClient: %w", err))
	}
	defer eventClient.Close()

	// 5. Repositories & UseCase
	bookingRepo := persistBooking.NewBookingPostgresRepo(pg)
	seatLockManager := redisRepo.NewSeatLockManager(rdb)
	uc := bookingUc.NewUseCase(bookingRepo, seatLockManager, eventClient, cfg.Booking.HoldDuration)

	// 6. HTTP Server (Fiber)
	httpServer := httpserver.New(l, httpserver.Port(cfg.HTTP.Port), httpserver.Prefork(cfg.HTTP.UsePreforkMode))
	restapi.NewRouter(httpServer.App, cfg, uc, l)
	httpServer.Start()
	l.Info("Booking HTTP Server started on port %s", cfg.HTTP.Port)

	// 7. Background Workers (Outbox Worker, Expiry Engine, Payment Consumer)
	workerCtx, cancelWorkers := context.WithCancel(context.Background())
	defer cancelWorkers()

	// 7.1 Outbox Worker
	outboxWorker := worker.NewOutboxWorker(
		bookingRepo,
		cfg.Kafka.Brokers,
		cfg.Kafka.TopicBookingEvents,
		cfg.Kafka.OutboxBatchSize,
		cfg.Kafka.OutboxFlushInterval,
		l,
	)
	go outboxWorker.Start(workerCtx)

	// 7.2 Expiry Engine Poller
	expiryWorker := worker.NewExpiryWorker(
		uc,
		cfg.Booking.ExpiryPollInterval,
		50,
		l,
	)
	go expiryWorker.Start(workerCtx)

	// 7.3 Payment Consumer
	paymentConsumer := worker.NewPaymentConsumer(
		uc,
		cfg.Kafka.Brokers,
		cfg.Kafka.TopicPaymentEvents,
		cfg.Kafka.ConsumerGroupID,
		l,
	)
	go paymentConsumer.Start(workerCtx)

	// 8. Graceful Shutdown
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt, syscall.SIGTERM)

	select {
	case sig := <-interrupt:
		l.Info("app - Run - signal: %s", sig.String())
	case err := <-httpServer.Notify():
		l.Error(fmt.Errorf("app - Run - httpServer.Notify: %w", err))
	}

	cancelWorkers()

	if err := httpServer.Shutdown(); err != nil {
		l.Error(fmt.Errorf("app - Run - httpServer.Shutdown: %w", err))
	}
	l.Info("Booking Service shutdown successfully.")
}
