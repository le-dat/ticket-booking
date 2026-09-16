package grpc

import (
	"context"
	"fmt"
	"time"

	pb "github.com/zentrix-app/zentrix-backend-go-temp/docs/proto/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type EventServiceClient struct {
	conn   *grpc.ClientConn
	client pb.EventServiceClient
}

func NewEventServiceClient(addr string) (*EventServiceClient, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		// Fallback không block nếu Event Service chưa khởi động ngay
		conn, err = grpc.Dial(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
		if err != nil {
			return nil, fmt.Errorf("EventServiceClient - connect error: %w", err)
		}
	}

	return &EventServiceClient{
		conn:   conn,
		client: pb.NewEventServiceClient(conn),
	}, nil
}

func (c *EventServiceClient) ValidateAndLockSeats(ctx context.Context, showID string, seatIDs []string, userID string) (*pb.ValidateSeatsResponse, error) {
	req := &pb.ValidateSeatsRequest{
		ShowId:  showID,
		SeatIds: seatIDs,
		UserId:  userID,
	}

	resp, err := c.client.ValidateAndLockSeats(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("EventServiceClient - ValidateAndLockSeats: %w", err)
	}

	return resp, nil
}

func (c *EventServiceClient) ReleaseSeats(ctx context.Context, showID string, seatIDs []string, userID string) error {
	req := &pb.ReleaseSeatsRequest{
		ShowId:  showID,
		SeatIds: seatIDs,
		UserId:  userID,
	}

	_, err := c.client.ReleaseSeats(ctx, req)
	if err != nil {
		return fmt.Errorf("EventServiceClient - ReleaseSeats: %w", err)
	}

	return nil
}

func (c *EventServiceClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}
