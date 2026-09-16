package restapi

import (
	"net/http"

	"github.com/ansrivas/fiberprometheus/v2"
	"github.com/zentrix-app/zentrix-backend-go-temp/config"
	_ "github.com/zentrix-app/zentrix-backend-go-temp/docs" // Swagger docs.
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi/middleware"
	v1 "github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi/v1"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
	"github.com/gofiber/contrib/otelfiber/v2"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/swagger"
)

// NewRouter -.
func NewRouter(app *fiber.App, cfg *config.Config, eventUC usecase.Event, l logger.Interface) {
	// Options
	app.Use(middleware.Logger(l))
	app.Use(middleware.Recovery(l))

	// Prometheus metrics
	if cfg.Metrics.Enabled {
		prometheus := fiberprometheus.New("event-service")
		prometheus.RegisterAt(app, "/metrics")
		app.Use(prometheus.Middleware)
	}

	// Swagger
	if cfg.Swagger.Enabled {
		app.Get("/swagger/*", swagger.HandlerDefault)
	}

	// K8s probe
	app.Get("/healthz", func(ctx *fiber.Ctx) error { return ctx.SendStatus(http.StatusOK) })

	// Routers
	apiV1Group := app.Group("/v1")
	{
		if cfg.Tracing.Enabled {
			apiV1Group.Use(otelfiber.Middleware())
		}

		v1.NewRoutes(apiV1Group, eventUC, l)
	}
}
