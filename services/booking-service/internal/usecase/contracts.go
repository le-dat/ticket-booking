package usecase

import (
	"context"

	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
)

type (
	// Booking - Usecase nghiệp vụ chính cho đơn hàng & giữ vé
	Booking interface {
		CreateBooking(ctx context.Context, userID, showID string, seatIDs []string) (entity.Booking, error)
		GetBooking(ctx context.Context, bookingID string) (entity.Booking, error)
		CancelBooking(ctx context.Context, bookingID, userID string) (entity.Booking, error)
		ConfirmBooking(ctx context.Context, bookingID string) (entity.Booking, error)
		ExpirePendingBookings(ctx context.Context, limit int) (int, error)
	}
)
