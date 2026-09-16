package middleware

import (
	"net/http"

	"github.com/gofiber/fiber/v2"
)

type errorResponse struct {
	Error string `json:"error"`
}

// Auth returns a trusted header authentication middleware for Fiber (gateway pattern).
func Auth() fiber.Handler {
	return func(ctx *fiber.Ctx) error {
		userID := ctx.Get("X-User-ID")
		if userID == "" {
			return ctx.Status(http.StatusUnauthorized).JSON(errorResponse{Error: "missing user identification header"})
		}

		ctx.Locals("userID", userID)

		return ctx.Next()
	}
}
