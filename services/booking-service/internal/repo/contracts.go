package repo

import (
	"context"

	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
)

type (
	// BookingRepo - Thao tác DB cho Booking domain
	BookingRepo interface {
		CreateBookingWithTx(ctx context.Context, b *entity.Booking, items []entity.BookingItem, outbox *entity.OutboxEvent) error
		GetBookingByID(ctx context.Context, id string) (entity.Booking, error)
		UpdateBookingStatus(ctx context.Context, id string, status string) error
		CancelBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) (entity.Booking, error)
		ConfirmBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) (entity.Booking, error)
		FindAndLockExpiredBookings(ctx context.Context, limit int) ([]entity.Booking, error)
		ExpireBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) error
	}

	// OutboxRepo - Thao tác Outbox Events cho Transactional Outbox Pattern
	OutboxRepo interface {
		GetPendingOutboxEvents(ctx context.Context, limit int) ([]entity.OutboxEvent, error)
		MarkOutboxPublished(ctx context.Context, id string) error
		MarkOutboxFailed(ctx context.Context, id string, errMsg string) error
	}
)