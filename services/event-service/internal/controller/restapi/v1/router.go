package v1

import (
	"github.com/gofiber/fiber/v2"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

func NewRoutes(handler fiber.Router, uEvent usecase.Event, l logger.Interface) {
	newEventRoutes(handler, uEvent, l)
}
