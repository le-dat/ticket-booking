package v1

import (
	"context"

	pb "github.com/zentrix-app/zentrix-backend-go-temp/docs/proto/v1"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
	pbgrpc "google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type EventGRPCHandler struct {
	pb.UnimplementedEventServiceServer
	u usecase.Event
	l logger.Interface
}

func NewEventGRPCHandler(server *pbgrpc.Server, u usecase.Event, l logger.Interface) {
	pb.RegisterEventServiceServer(server, &EventGRPCHandler{u: u, l: l})
}

func (h *EventGRPCHandler) GetShowSeatStatus(ctx context.Context, req *pb.GetShowSeatStatusRequest) (*pb.GetShowSeatStatusResponse, error) {
	seats, err := h.u.GetShowSeats(ctx, req.GetShowId())
	if err != nil {
		return nil, status.Errorf(codes.Internal, "Lỗi lấy danh sách ghế: %v", err)
	}

	protoSeats := make([]*pb.SeatInfo, 0, len(seats))
	for _, s := range seats {
		protoSeats = append(protoSeats, &pb.SeatInfo{
			SeatId:       s.ID,
			RowName:      s.RowName,
			SeatNumber:   int32(s.ColIndex),
			SeatType:     "STANDARD",
			PriceInCents: int64(s.Price * 100),
			Status:       s.Status,
		})
	}

	return &pb.GetShowSeatStatusResponse{
		ShowId:    req.GetShowId(),
		EventName: "Event",
		ShowTime:  0,
		Seats:     protoSeats,
	}, nil
}

func (h *EventGRPCHandler) ValidateAndLockSeats(ctx context.Context, req *pb.ValidateSeatsRequest) (*pb.ValidateSeatsResponse, error) {
	ok, msg, seats, totalPrice, err := h.u.LockSeats(ctx, req.GetShowId(), req.GetSeatIds(), req.GetUserId())
	if err != nil {
		return nil, status.Errorf(codes.Internal, "Lỗi xử lý lock ghế: %v", err)
	}

	if !ok {
		return &pb.ValidateSeatsResponse{
			IsValid:      false,
			ErrorMessage: msg,
		}, nil
	}

	protoSeats := make([]*pb.SeatInfo, 0, len(seats))
	for _, s := range seats {
		protoSeats = append(protoSeats, &pb.SeatInfo{
			SeatId:       s.ID,
			RowName:      s.RowName,
			SeatNumber:   int32(s.ColIndex),
			SeatType:     "STANDARD",
			PriceInCents: int64(s.Price * 100),
			Status:       s.Status,
		})
	}

	return &pb.ValidateSeatsResponse{
		IsValid:           true,
		ErrorMessage:      msg,
		TotalPriceInCents: int64(totalPrice * 100),
		Seats:             protoSeats,
	}, nil
}

func (h *EventGRPCHandler) ReleaseSeats(ctx context.Context, req *pb.ReleaseSeatsRequest) (*pb.ReleaseSeatsResponse, error) {
	ok, msg, err := h.u.ReleaseSeats(ctx, req.GetShowId(), req.GetSeatIds(), req.GetUserId())
	if err != nil {
		return nil, status.Errorf(codes.Internal, "Lỗi xử lý giải phóng ghế: %v", err)
	}

	return &pb.ReleaseSeatsResponse{
		Success: ok,
		Message: msg,
	}, nil
}

