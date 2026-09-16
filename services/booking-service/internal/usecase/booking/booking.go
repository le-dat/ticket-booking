package booking

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/repo"
	grpcClient "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/grpc"
	redisRepo "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/redis"
)

var (
	ErrInvalidInput       = errors.New("invalid booking request parameters")
	ErrSeatValidationFail = errors.New("seat validation or reservation failed")
)

type UseCase struct {
	repo         repo.BookingRepo
	redisLock    *redisRepo.SeatLockManager
	eventClient  *grpcClient.EventServiceClient
	holdDuration time.Duration
}

func NewUseCase(
	r repo.BookingRepo,
	rl *redisRepo.SeatLockManager,
	ec *grpcClient.EventServiceClient,
	holdDuration time.Duration,
) *UseCase {
	if holdDuration <= 0 {
		holdDuration = 10 * time.Minute
	}
	return &UseCase{
		repo:         r,
		redisLock:    rl,
		eventClient:  ec,
		holdDuration: holdDuration,
	}
}

// CreateBooking thực hiện quy trình 3 tầng: Redis Lock -> gRPC Event Validation -> DB Transaction & Outbox Event
func (uc *UseCase) CreateBooking(ctx context.Context, userID, showID string, seatIDs []string) (entity.Booking, error) {
	if userID == "" || showID == "" || len(seatIDs) == 0 {
		return entity.Booking{}, fmt.Errorf("%w: user_id, show_id and seat_ids are required", ErrInvalidInput)
	}

	// Tầng 1: Redis Distributed Lock cho toàn bộ ghế yêu cầu
	_, err := uc.redisLock.AcquireSeatLocks(ctx, showID, seatIDs, userID, uc.holdDuration)
	if err != nil {
		return entity.Booking{}, fmt.Errorf("redis lock failed: %w", err)
	}

	// Tầng 2: Gọi gRPC sang event-service để kiểm tra và khoá ghế trong DB của event-service
	resp, err := uc.eventClient.ValidateAndLockSeats(ctx, showID, seatIDs, userID)
	if err != nil {
		// Rollback Redis Lock nếu gRPC lỗi mạng
		_ = uc.redisLock.ReleaseSeatLocks(ctx, showID, seatIDs, userID)
		return entity.Booking{}, fmt.Errorf("event-service gRPC error: %w", err)
	}

	if !resp.GetIsValid() {
		// Rollback Redis Lock nếu ghế không hợp lệ hoặc đã có người giữ
		_ = uc.redisLock.ReleaseSeatLocks(ctx, showID, seatIDs, userID)
		return entity.Booking{}, fmt.Errorf("%w: %s", ErrSeatValidationFail, resp.GetErrorMessage())
	}

	// Tầng 3: Tạo Booking, BookingItems và Outbox Event trong Database
	bookingID := uuid.New().String()
	totalAmount := float64(resp.GetTotalPriceInCents()) / 100.0

	var items []entity.BookingItem
	for _, s := range resp.GetSeats() {
		items = append(items, entity.BookingItem{
			ID:         uuid.New().String(),
			BookingID:  bookingID,
			SeatID:     s.GetSeatId(),
			SeatNumber: fmt.Sprintf("%s%d", s.GetRowName(), s.GetSeatNumber()),
			Price:      float64(s.GetPriceInCents()) / 100.0,
		})
	}

	expiresAt := time.Now().Add(uc.holdDuration)
	b := entity.Booking{
		ID:          bookingID,
		UserID:      userID,
		ShowID:      showID,
		TotalAmount: totalAmount,
		Status:      entity.BookingStatusPending,
		ExpiresAt:   expiresAt,
		Items:       items,
	}

	// Chuẩn bị payload Outbox Event đồng bộ cho Kafka topic booking-events
	payloadMap := map[string]any{
		"event_type":   entity.EventTypeBookingCreated,
		"booking_id":   b.ID,
		"user_id":      b.UserID,
		"show_id":      b.ShowID,
		"total_amount": b.TotalAmount,
		"status":       b.Status,
		"expires_at":   b.ExpiresAt.Format(time.RFC3339),
		"seat_ids":     seatIDs,
	}
	payloadBytes, _ := json.Marshal(payloadMap)

	outbox := entity.OutboxEvent{
		AggregateType: "Booking",
		AggregateID:   b.ID,
		EventType:     entity.EventTypeBookingCreated,
		Payload:       payloadBytes,
		Status:        entity.OutboxStatusPending,
	}

	if err := uc.repo.CreateBookingWithTx(ctx, &b, items, &outbox); err != nil {
		// Saga Rollback: Nhả ghế trong event-service và Redis lock nếu DB bị fail
		_ = uc.eventClient.ReleaseSeats(ctx, showID, seatIDs, userID)
		_ = uc.redisLock.ReleaseSeatLocks(ctx, showID, seatIDs, userID)
		return entity.Booking{}, fmt.Errorf("failed to persist booking transaction: %w", err)
	}

	return b, nil
}

// GetBooking tra cứu thông tin đơn hàng
func (uc *UseCase) GetBooking(ctx context.Context, bookingID string) (entity.Booking, error) {
	if bookingID == "" {
		return entity.Booking{}, fmt.Errorf("%w: booking_id is required", ErrInvalidInput)
	}
	return uc.repo.GetBookingByID(ctx, bookingID)
}

// CancelBooking huỷ đơn hàng khi còn trong trạng thái PENDING và kích hoạt Saga compensation
func (uc *UseCase) CancelBooking(ctx context.Context, bookingID, userID string) (entity.Booking, error) {
	if bookingID == "" {
		return entity.Booking{}, fmt.Errorf("%w: booking_id is required", ErrInvalidInput)
	}

	payloadMap := map[string]any{
		"event_type": entity.EventTypeBookingCancelled,
		"booking_id": bookingID,
		"user_id":    userID,
	}
	payloadBytes, _ := json.Marshal(payloadMap)

	outbox := entity.OutboxEvent{
		AggregateType: "Booking",
		AggregateID:   bookingID,
		EventType:     entity.EventTypeBookingCancelled,
		Payload:       payloadBytes,
		Status:        entity.OutboxStatusPending,
	}

	b, err := uc.repo.CancelBookingWithTx(ctx, bookingID, &outbox)
	if err != nil {
		return entity.Booking{}, err
	}

	// Saga Compensation: Giải phóng ghế bên event-service và Redis
	seatIDs := make([]string, 0, len(b.Items))
	for _, item := range b.Items {
		seatIDs = append(seatIDs, item.SeatID)
	}

	_ = uc.eventClient.ReleaseSeats(ctx, b.ShowID, seatIDs, userID)
	_ = uc.redisLock.ReleaseSeatLocks(ctx, b.ShowID, seatIDs, userID)

	return b, nil
}

// ConfirmBooking xác nhận đơn hàng khi nhận thông báo thanh toán thành công
func (uc *UseCase) ConfirmBooking(ctx context.Context, bookingID string) (entity.Booking, error) {
	if bookingID == "" {
		return entity.Booking{}, fmt.Errorf("%w: booking_id is required", ErrInvalidInput)
	}

	payloadMap := map[string]any{
		"event_type": entity.EventTypeBookingConfirmed,
		"booking_id": bookingID,
	}
	payloadBytes, _ := json.Marshal(payloadMap)

	outbox := entity.OutboxEvent{
		AggregateType: "Booking",
		AggregateID:   bookingID,
		EventType:     entity.EventTypeBookingConfirmed,
		Payload:       payloadBytes,
		Status:        entity.OutboxStatusPending,
	}

	b, err := uc.repo.ConfirmBookingWithTx(ctx, bookingID, &outbox)
	if err != nil {
		return entity.Booking{}, err
	}

	// Giải phóng Redis lock vì ghế đã chính thức được chốt thành công
	seatIDs := make([]string, 0, len(b.Items))
	for _, item := range b.Items {
		seatIDs = append(seatIDs, item.SeatID)
	}
	_ = uc.redisLock.ReleaseSeatLocks(ctx, b.ShowID, seatIDs, "")

	return b, nil
}

// ExpirePendingBookings quét và xử lý hàng loạt các đơn hàng quá hạn 10 phút
func (uc *UseCase) ExpirePendingBookings(ctx context.Context, limit int) (int, error) {
	expiredBookings, err := uc.repo.FindAndLockExpiredBookings(ctx, limit)
	if err != nil {
		return 0, fmt.Errorf("ExpirePendingBookings - query: %w", err)
	}

	count := 0
	for _, b := range expiredBookings {
		payloadMap := map[string]any{
			"event_type": entity.EventTypeBookingExpired,
			"booking_id": b.ID,
			"user_id":    b.UserID,
		}
		payloadBytes, _ := json.Marshal(payloadMap)

		outbox := entity.OutboxEvent{
			AggregateType: "Booking",
			AggregateID:   b.ID,
			EventType:     entity.EventTypeBookingExpired,
			Payload:       payloadBytes,
			Status:        entity.OutboxStatusPending,
		}

		if err := uc.repo.ExpireBookingWithTx(ctx, b.ID, &outbox); err != nil {
			continue
		}

		// Giải phóng ghế trong event-service và Redis
		seatIDs := make([]string, 0, len(b.Items))
		for _, item := range b.Items {
			seatIDs = append(seatIDs, item.SeatID)
		}
		_ = uc.eventClient.ReleaseSeats(ctx, b.ShowID, seatIDs, "")
		_ = uc.redisLock.ReleaseSeatLocks(ctx, b.ShowID, seatIDs, "")

		count++
	}

	return count, nil
}
