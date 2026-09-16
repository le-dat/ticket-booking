package middleware_test

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi/middleware"
)

func newTestApp(t *testing.T) *fiber.App {
	t.Helper()

	app := fiber.New()
	app.Use(middleware.Auth())
	app.Get("/test", func(c *fiber.Ctx) error {
		userID, ok := c.Locals("userID").(string)
		if !ok {
			return c.SendStatus(http.StatusUnauthorized)
		}

		return c.SendString(userID)
	})

	return app
}

func TestAuthMiddleware(t *testing.T) {
	t.Parallel()

	app := newTestApp(t)

	tests := []struct {
		name           string
		userIDHeader   string
		expectedStatus int
		expectedBody   string
	}{
		{
			name:           "missing X-User-ID header",
			userIDHeader:   "",
			expectedStatus: http.StatusUnauthorized,
		},
		{
			name:           "valid X-User-ID header",
			userIDHeader:   "user-id-123",
			expectedStatus: http.StatusOK,
			expectedBody:   "user-id-123",
		},
	}

	for _, tc := range tests {
		localTc := tc

		t.Run(localTc.name, func(t *testing.T) {
			t.Parallel()

			req := httptest.NewRequestWithContext(t.Context(), http.MethodGet, "/test", http.NoBody)
			if localTc.userIDHeader != "" {
				req.Header.Set("X-User-ID", localTc.userIDHeader)
			}

			resp, err := app.Test(req)
			require.NoError(t, err)

			defer resp.Body.Close()

			assert.Equal(t, localTc.expectedStatus, resp.StatusCode)

			if localTc.expectedBody != "" {
				body, readErr := io.ReadAll(resp.Body)
				require.NoError(t, readErr)
				assert.Equal(t, localTc.expectedBody, string(body))
			}
		})
	}
}
