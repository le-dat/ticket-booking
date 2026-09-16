// Package app configures and runs application.
package app

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/zentrix-app/zentrix-backend-go-temp/config"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/grpc"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi"
	persistEventRepo "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/persistent/event"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	eventUseCase "github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase/event"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/grpcserver"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/httpserver"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/postgres"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/tracing"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	pbgrpc "google.golang.org/grpc"
)

type useCases struct {
	event usecase.Event
}

type servers struct {
	grpc *grpcserver.Server
	http *httpserver.Server
}

func initUseCases(pg *postgres.Postgres) useCases {
	eventRepo := persistEventRepo.New(pg)

	return useCases{
		event: eventUseCase.New(eventRepo),
	}
}

func initServers(cfg *config.Config, uc useCases, l logger.Interface) servers {
	// gRPC Server
	grpcServer := grpcserver.New(
		l,
		grpcserver.Port(cfg.GRPC.Port),
		grpcserver.ServerOptions(
			pbgrpc.StatsHandler(otelgrpc.NewServerHandler()),
		),
	)
	grpc.NewRouter(grpcServer.App, uc.event, l)

	// HTTP Server
	httpServer := httpserver.New(l, httpserver.Port(cfg.HTTP.Port), httpserver.Prefork(cfg.HTTP.UsePreforkMode))
	restapi.NewRouter(httpServer.App, cfg, uc.event, l)

	return servers{
		grpc: grpcServer,
		http: httpServer,
	}
}

func (s *servers) startServers() {
	s.grpc.Start()
	s.http.Start()
}

func (s *servers) waitForShutdown(l logger.Interface) {
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt, syscall.SIGTERM)

	var err error

	select {
	case sig := <-interrupt:
		l.Info("app - Run - signal: %s", sig.String())
	case err = <-s.http.Notify():
		l.Error(fmt.Errorf("app - Run - httpServer.Notify: %w", err))
	case err = <-s.grpc.Notify():
		l.Error(fmt.Errorf("app - Run - grpcServer.Notify: %w", err))
	}

	s.shutdownServers(l)
}

func (s *servers) shutdownServers(l logger.Interface) {
	if err := s.http.Shutdown(); err != nil {
		l.Error(fmt.Errorf("app - Run - httpServer.Shutdown: %w", err))
	}

	if err := s.grpc.Shutdown(); err != nil {
		l.Error(fmt.Errorf("app - Run - grpcServer.Shutdown: %w", err))
	}
}

// Run creates objects via constructors.
func Run(cfg *config.Config) {
	l := logger.New(cfg.Log.Level)

	ctx := context.Background()

	// Tracing
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

	// Repository
	pg, err := postgres.New(cfg.PG.URL, postgres.MaxPoolSize(cfg.PG.PoolMax))
	if err != nil {
		l.Fatal(fmt.Errorf("app - Run - postgres.New: %w", err))
	}
	defer pg.Close()

	uc := initUseCases(pg)
	s := initServers(cfg, uc, l)
	s.startServers()
	s.waitForShutdown(l)
}
