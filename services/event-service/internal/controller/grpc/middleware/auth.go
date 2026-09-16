package middleware

import (
	"context"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

type contextKey string

const userIDKey contextKey = "userID"

// UserIDFromContext extracts the user ID from the context.
func UserIDFromContext(ctx context.Context) (string, bool) {
	userID, ok := ctx.Value(userIDKey).(string)

	return userID, ok
}

// AuthInterceptor returns a gRPC unary interceptor for trusted metadata authentication.
func AuthInterceptor() grpc.UnaryServerInterceptor {
	skipAuthMethods := map[string]bool{
		"/grpc.v1.AuthService/Register": true,
		"/grpc.v1.AuthService/Login":    true,
	}

	return func(ctx context.Context, req any, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (any, error) {
		if skipAuthMethods[info.FullMethod] {
			return handler(ctx, req)
		}

		md, ok := metadata.FromIncomingContext(ctx)
		if !ok {
			return nil, status.Error(codes.Unauthenticated, "missing metadata")
		}

		values := md.Get("x-user-id")
		if len(values) == 0 || values[0] == "" {
			return nil, status.Error(codes.Unauthenticated, "missing x-user-id metadata")
		}

		ctx = context.WithValue(ctx, userIDKey, values[0])

		return handler(ctx, req)
	}
}
