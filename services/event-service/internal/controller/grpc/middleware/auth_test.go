package middleware_test

import (
	"context"
	"testing"

	grpcmw "github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/grpc/middleware"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

type ctxCapture struct {
	ctx context.Context
}

func testHandler(ctx context.Context, req any) (any, error) {
	return &ctxCapture{ctx: ctx}, nil
}

func TestAuthInterceptor(t *testing.T) {
	t.Parallel()

	interceptor := grpcmw.AuthInterceptor()
	info := &grpc.UnaryServerInfo{FullMethod: "/grpc.v1.EventService/GetEvent"}

	t.Run("missing metadata", func(t *testing.T) {
		t.Parallel()
		_, err := interceptor(t.Context(), "req", info, testHandler)
		require.Error(t, err)
		assert.Equal(t, codes.Unauthenticated, status.Code(err))
	})

	t.Run("missing x-user-id metadata", func(t *testing.T) {
		t.Parallel()
		md := metadata.New(map[string]string{"other-key": "value"})
		ctx := metadata.NewIncomingContext(t.Context(), md)
		_, err := interceptor(ctx, "req", info, testHandler)
		require.Error(t, err)
		assert.Equal(t, codes.Unauthenticated, status.Code(err))
	})

	t.Run("valid x-user-id metadata", func(t *testing.T) {
		t.Parallel()
		md := metadata.Pairs("x-user-id", "user-id-123")
		ctx := metadata.NewIncomingContext(t.Context(), md)
		resp, err := interceptor(ctx, "req", info, testHandler)
		require.NoError(t, err)

		capture, ok := resp.(*ctxCapture)
		require.True(t, ok)

		userID, ok := grpcmw.UserIDFromContext(capture.ctx)
		require.True(t, ok)
		assert.Equal(t, "user-id-123", userID)
	})
}
