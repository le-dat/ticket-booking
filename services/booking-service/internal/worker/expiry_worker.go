package worker

import (
	"context"
	"fmt"
	"time"

	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

type ExpiryWorker struct {
	uc           usecase.Booking
	pollInterval time.Duration
	batchLimit   int
	logger       logger.Interface
}

func NewExpiryWorker(
	uc usecase.Booking,
	pollInterval time.Duration,
	batchLimit int,
	l logger.Interface,
) *ExpiryWorker {
	if pollInterval <= 0 {
		pollInterval = 5 * time.Second
	}
	if batchLimit <= 0 {
		batchLimit = 50
	}
	return &ExpiryWorker{
		uc:           uc,
		pollInterval: pollInterval,
		batchLimit:   batchLimit,
		logger:       l,
	}
}

// Start khởi chạy worker nền quét và tự động huỷ các đơn PENDING đã quá hạn 10 phút
func (w *ExpiryWorker) Start(ctx context.Context) {
	w.logger.Info("Expiry Worker started (polling every %s for expired bookings)...", w.pollInterval.String())

	ticker := time.NewTicker(w.pollInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			w.logger.Info("Expiry Worker shutting down...")
			return
		case <-ticker.C:
			count, err := w.uc.ExpirePendingBookings(ctx, w.batchLimit)
			if err != nil {
				w.logger.Error(fmt.Errorf("expiry worker error: %w", err))
			} else if count > 0 {
				w.logger.Info("Expiry Worker: Automatically expired %d bookings and released seats", count)
			}
		}
	}
}
