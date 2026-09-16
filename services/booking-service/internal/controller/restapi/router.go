package restapi

import (
	"net/http"

	"github.com/ansrivas/fiberprometheus/v2"
	"github.com/gofiber/contrib/otelfiber/v2"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/swagger"
	"github.com/zentrix-app/zentrix-backend-go-temp/config"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi/middleware"
	v1 "github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi/v1"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

// NewRouter cấu hình middleware và định tuyến REST API cho Booking Service
func NewRouter(app *fiber.App, cfg *config.Config, u usecase.Booking, l logger.Interface) {
	// Options
	app.Use(middleware.Logger(l))
	app.Use(middleware.Recovery(l))

	// Prometheus metrics
	if cfg.Metrics.Enabled {
		prometheus := fiberprometheus.New("booking-service")
		prometheus.RegisterAt(app, "/metrics")
		app.Use(prometheus.Middleware)
	}

	// Swagger
	if cfg.Swagger.Enabled {
		app.Get("/swagger/*", swagger.HandlerDefault)
	}

	// Health check
	app.Get("/healthz", func(ctx *fiber.Ctx) error {
		return ctx.Status(http.StatusOK).JSON(fiber.Map{
			"status":  "ok",
			"service": "booking-service",
		})
	})

	// Routers v1 (Supports both direct /v1 and Kong Gateway /api/v1 prefixes)
	for _, prefix := range []string{"/v1", "/api/v1"} {
		apiGroup := app.Group(prefix)
		if cfg.Tracing.Enabled {
			apiGroup.Use(otelfiber.Middleware())
		}

		v1.NewRoutes(apiGroup, u, l)
	}
}
