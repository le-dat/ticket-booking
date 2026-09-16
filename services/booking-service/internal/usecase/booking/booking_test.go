package booking_test

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
	usecaseBooking "github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase/booking"
)

// MockRepo implements repo.BookingRepo for testing
type mockBookingRepo struct {
	createErr   error
	getBooking  entity.Booking
	getErr      error
	cancelErr   error
	confirmErr  error
	expiredList []entity.Booking
}

func (m *mockBookingRepo) CreateBookingWithTx(ctx context.Context, b *entity.Booking, items []entity.BookingItem, outbox *entity.OutboxEvent) error {
	b.ID = "test-booking-id"
	b.Items = items
	return m.createErr
}

func (m *mockBookingRepo) GetBookingByID(ctx context.Context, id string) (entity.Booking, error) {
	return m.getBooking, m.getErr
}

func (m *mockBookingRepo) UpdateBookingStatus(ctx context.Context, id string, status string) error {
	return nil
}

func (m *mockBookingRepo) CancelBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) (entity.Booking, error) {
	return m.getBooking, m.cancelErr
}

func (m *mockBookingRepo) ConfirmBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) (entity.Booking, error) {
	return m.getBooking, m.confirmErr
}

func (m *mockBookingRepo) FindAndLockExpiredBookings(ctx context.Context, limit int) ([]entity.Booking, error) {
	return m.expiredList, nil
}

func (m *mockBookingRepo) ExpireBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) error {
	return nil
}

func TestBookingUseCase_InputValidation(t *testing.T) {
	// Arrange
	uc := usecaseBooking.NewUseCase(&mockBookingRepo{}, nil, nil, 10*time.Minute)
	ctx := context.Background()

	// Act & Assert 1: Thiếu user_id
	_, err := uc.CreateBooking(ctx, "", "show-1", []string{"seat-1"})
	assert.ErrorIs(t, err, usecaseBooking.ErrInvalidInput)

	// Act & Assert 2: Thiếu show_id
	_, err = uc.CreateBooking(ctx, "user-1", "", []string{"seat-1"})
	assert.ErrorIs(t, err, usecaseBooking.ErrInvalidInput)

	// Act & Assert 3: Danh sách ghế rỗng
	_, err = uc.CreateBooking(ctx, "user-1", "show-1", []string{})
	assert.ErrorIs(t, err, usecaseBooking.ErrInvalidInput)

	// Act & Assert 4: GetBooking với id rỗng
	_, err = uc.GetBooking(ctx, "")
	assert.ErrorIs(t, err, usecaseBooking.ErrInvalidInput)

	// Act & Assert 5: CancelBooking với id rỗng
	_, err = uc.CancelBooking(ctx, "", "user-1")
	assert.ErrorIs(t, err, usecaseBooking.ErrInvalidInput)

	// Act & Assert 6: ConfirmBooking với id rỗng
	_, err = uc.ConfirmBooking(ctx, "")
	assert.ErrorIs(t, err, usecaseBooking.ErrInvalidInput)
}

func TestBookingUseCase_GetBooking_Success(t *testing.T) {
	// Arrange
	expected := entity.Booking{
		ID:          "booking-123",
		UserID:      "user-456",
		ShowID:      "show-789",
		TotalAmount: 250000,
		Status:      entity.BookingStatusPending,
		Items: []entity.BookingItem{
			{SeatID: "seat-A1", SeatNumber: "A1", Price: 250000},
		},
	}
	repo := &mockBookingRepo{getBooking: expected}
	uc := usecaseBooking.NewUseCase(repo, nil, nil, 10*time.Minute)

	// Act
	b, err := uc.GetBooking(context.Background(), "booking-123")

	// Assert
	assert.NoError(t, err)
	assert.Equal(t, expected.ID, b.ID)
	assert.Equal(t, expected.TotalAmount, b.TotalAmount)
	assert.Equal(t, 1, len(b.Items))
}
