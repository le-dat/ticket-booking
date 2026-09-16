package grpc

import (
	v1 "github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/grpc/v1"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
	pbgrpc "google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

// NewRouter -.
func NewRouter(app *pbgrpc.Server, u usecase.Event, l logger.Interface) {
	v1.NewEventGRPCHandler(app, u, l)
	reflection.Register(app)
}
