package v1

import (
	"github.com/gofiber/fiber/v2"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

func NewRoutes(handler fiber.Router, uBooking usecase.Booking, l logger.Interface) {
	newBookingRoutes(handler, uBooking, l)
}