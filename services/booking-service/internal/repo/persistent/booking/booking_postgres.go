package booking

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/postgres"
)

var (
	ErrBookingNotFound     = errors.New("booking not found")
	ErrBookingNotPending   = errors.New("booking is not pending")
	ErrBookingAlreadyPaid  = errors.New("booking is already paid")
)

type BookingPostgresRepo struct {
	*postgres.Postgres
}

func NewBookingPostgresRepo(pg *postgres.Postgres) *BookingPostgresRepo {
	return &BookingPostgresRepo{pg}
}

// CreateBookingWithTx lưu Booking, các items và Outbox Event trong 1 transaction ACID
func (r *BookingPostgresRepo) CreateBookingWithTx(
	ctx context.Context,
	b *entity.Booking,
	items []entity.BookingItem,
	outbox *entity.OutboxEvent,
) error {
	tx, err := r.Pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("BookingPostgresRepo - CreateBookingWithTx - Begin: %w", err)
	}
	defer tx.Rollback(ctx)

	if b.ID == "" {
		b.ID = uuid.New().String()
	}
	now := time.Now()
	b.CreatedAt = now
	b.UpdatedAt = now

	// 1. Insert Booking
	queryBooking := `
		INSERT INTO bookings (id, user_id, show_id, total_amount, status, expires_at, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`
	_, err = tx.Exec(ctx, queryBooking, b.ID, b.UserID, b.ShowID, b.TotalAmount, b.Status, b.ExpiresAt, b.CreatedAt, b.UpdatedAt)
	if err != nil {
		return fmt.Errorf("BookingPostgresRepo - CreateBookingWithTx - insert booking: %w", err)
	}

	// 2. Insert BookingItems
	queryItem := `
		INSERT INTO booking_items (id, booking_id, seat_id, seat_number, price, created_at)
		VALUES ($1, $2, $3, $4, $5, $6)
	`
	for i := range items {
		if items[i].ID == "" {
			items[i].ID = uuid.New().String()
		}
		items[i].BookingID = b.ID
		items[i].CreatedAt = now

		_, err = tx.Exec(ctx, queryItem, items[i].ID, items[i].BookingID, items[i].SeatID, items[i].SeatNumber, items[i].Price, items[i].CreatedAt)
		if err != nil {
			return fmt.Errorf("BookingPostgresRepo - CreateBookingWithTx - insert item %s: %w", items[i].SeatID, err)
		}
	}
	b.Items = items

	// 3. Insert Outbox Event
	if outbox != nil {
		if outbox.ID == "" {
			outbox.ID = uuid.New().String()
		}
		outbox.AggregateID = b.ID
		outbox.CreatedAt = now
		outbox.UpdatedAt = now

		queryOutbox := `
			INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload, status, retry_count, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		`
		_, err = tx.Exec(ctx, queryOutbox, outbox.ID, outbox.AggregateType, outbox.AggregateID, outbox.EventType, outbox.Payload, outbox.Status, outbox.RetryCount, outbox.CreatedAt, outbox.UpdatedAt)
		if err != nil {
			return fmt.Errorf("BookingPostgresRepo - CreateBookingWithTx - insert outbox: %w", err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("BookingPostgresRepo - CreateBookingWithTx - Commit: %w", err)
	}

	return nil
}

// GetBookingByID lấy thông tin Booking kèm danh sách ghế items
func (r *BookingPostgresRepo) GetBookingByID(ctx context.Context, id string) (entity.Booking, error) {
	var b entity.Booking
	queryBooking := `
		SELECT id, user_id, show_id, total_amount, status, expires_at, created_at, updated_at
		FROM bookings
		WHERE id = $1
	`
	row := r.Pool.QueryRow(ctx, queryBooking, id)
	err := row.Scan(&b.ID, &b.UserID, &b.ShowID, &b.TotalAmount, &b.Status, &b.ExpiresAt, &b.CreatedAt, &b.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return b, ErrBookingNotFound
		}
		return b, fmt.Errorf("BookingPostgresRepo - GetBookingByID - scan booking: %w", err)
	}

	queryItems := `
		SELECT id, booking_id, seat_id, seat_number, price, created_at
		FROM booking_items
		WHERE booking_id = $1
	`
	rows, err := r.Pool.Query(ctx, queryItems, id)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - GetBookingByID - query items: %w", err)
	}
	defer rows.Close()

	var items []entity.BookingItem
	for rows.Next() {
		var item entity.BookingItem
		if err := rows.Scan(&item.ID, &item.BookingID, &item.SeatID, &item.SeatNumber, &item.Price, &item.CreatedAt); err != nil {
			return b, fmt.Errorf("BookingPostgresRepo - GetBookingByID - scan item: %w", err)
		}
		items = append(items, item)
	}
	b.Items = items

	return b, nil
}

// UpdateBookingStatus cập nhật trạng thái đơn
func (r *BookingPostgresRepo) UpdateBookingStatus(ctx context.Context, id string, status string) error {
	query := `UPDATE bookings SET status = $1, updated_at = NOW() WHERE id = $2`
	res, err := r.Pool.Exec(ctx, query, status, id)
	if err != nil {
		return fmt.Errorf("BookingPostgresRepo - UpdateBookingStatus: %w", err)
	}
	if res.RowsAffected() == 0 {
		return ErrBookingNotFound
	}
	return nil
}

// CancelBookingWithTx huỷ đơn nếu còn PENDING và ghi outbox event
func (r *BookingPostgresRepo) CancelBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) (entity.Booking, error) {
	var b entity.Booking
	tx, err := r.Pool.Begin(ctx)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - Begin: %w", err)
	}
	defer tx.Rollback(ctx)

	querySelect := `
		SELECT id, user_id, show_id, total_amount, status, expires_at, created_at, updated_at
		FROM bookings
		WHERE id = $1
		FOR UPDATE
	`
	err = tx.QueryRow(ctx, querySelect, id).Scan(&b.ID, &b.UserID, &b.ShowID, &b.TotalAmount, &b.Status, &b.ExpiresAt, &b.CreatedAt, &b.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return b, ErrBookingNotFound
		}
		return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - lock booking: %w", err)
	}

	if b.Status != entity.BookingStatusPending {
		return b, ErrBookingNotPending
	}

	queryUpdate := `UPDATE bookings SET status = $1, updated_at = NOW() WHERE id = $2`
	_, err = tx.Exec(ctx, queryUpdate, entity.BookingStatusCancelled, id)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - update status: %w", err)
	}
	b.Status = entity.BookingStatusCancelled

	// Query items
	queryItems := `SELECT id, booking_id, seat_id, seat_number, price, created_at FROM booking_items WHERE booking_id = $1`
	rows, err := tx.Query(ctx, queryItems, id)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - query items: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var item entity.BookingItem
		if err := rows.Scan(&item.ID, &item.BookingID, &item.SeatID, &item.SeatNumber, &item.Price, &item.CreatedAt); err != nil {
			return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - scan item: %w", err)
		}
		b.Items = append(b.Items, item)
	}

	if outbox != nil {
		if outbox.ID == "" {
			outbox.ID = uuid.New().String()
		}
		outbox.AggregateID = b.ID
		now := time.Now()
		outbox.CreatedAt = now
		outbox.UpdatedAt = now

		queryOutbox := `
			INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload, status, retry_count, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		`
		_, err = tx.Exec(ctx, queryOutbox, outbox.ID, outbox.AggregateType, outbox.AggregateID, outbox.EventType, outbox.Payload, outbox.Status, outbox.RetryCount, outbox.CreatedAt, outbox.UpdatedAt)
		if err != nil {
			return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - insert outbox: %w", err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - CancelBookingWithTx - Commit: %w", err)
	}

	return b, nil
}

// ConfirmBookingWithTx cập nhật CONFIRMED cho đơn hàng khi thanh toán thành công
func (r *BookingPostgresRepo) ConfirmBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) (entity.Booking, error) {
	var b entity.Booking
	tx, err := r.Pool.Begin(ctx)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - Begin: %w", err)
	}
	defer tx.Rollback(ctx)

	querySelect := `
		SELECT id, user_id, show_id, total_amount, status, expires_at, created_at, updated_at
		FROM bookings
		WHERE id = $1
		FOR UPDATE
	`
	err = tx.QueryRow(ctx, querySelect, id).Scan(&b.ID, &b.UserID, &b.ShowID, &b.TotalAmount, &b.Status, &b.ExpiresAt, &b.CreatedAt, &b.UpdatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return b, ErrBookingNotFound
		}
		return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - lock booking: %w", err)
	}

	if b.Status == entity.BookingStatusConfirmed {
		// Idempotent: đã xác nhận từ trước
		_ = tx.Commit(ctx)
		return b, nil
	}

	if b.Status != entity.BookingStatusPending {
		return b, fmt.Errorf("%w: current status is %s", ErrBookingNotPending, b.Status)
	}

	queryUpdate := `UPDATE bookings SET status = $1, updated_at = NOW() WHERE id = $2`
	_, err = tx.Exec(ctx, queryUpdate, entity.BookingStatusConfirmed, id)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - update status: %w", err)
	}
	b.Status = entity.BookingStatusConfirmed

	// Query items
	queryItems := `SELECT id, booking_id, seat_id, seat_number, price, created_at FROM booking_items WHERE booking_id = $1`
	rows, err := tx.Query(ctx, queryItems, id)
	if err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - query items: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var item entity.BookingItem
		if err := rows.Scan(&item.ID, &item.BookingID, &item.SeatID, &item.SeatNumber, &item.Price, &item.CreatedAt); err != nil {
			return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - scan item: %w", err)
		}
		b.Items = append(b.Items, item)
	}

	if outbox != nil {
		if outbox.ID == "" {
			outbox.ID = uuid.New().String()
		}
		outbox.AggregateID = b.ID
		now := time.Now()
		outbox.CreatedAt = now
		outbox.UpdatedAt = now

		queryOutbox := `
			INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload, status, retry_count, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		`
		_, err = tx.Exec(ctx, queryOutbox, outbox.ID, outbox.AggregateType, outbox.AggregateID, outbox.EventType, outbox.Payload, outbox.Status, outbox.RetryCount, outbox.CreatedAt, outbox.UpdatedAt)
		if err != nil {
			return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - insert outbox: %w", err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return b, fmt.Errorf("BookingPostgresRepo - ConfirmBookingWithTx - Commit: %w", err)
	}

	return b, nil
}

// FindAndLockExpiredBookings quét các đơn PENDING đã quá hạn, khoá bằng SKIP LOCKED để tránh đụng độ
func (r *BookingPostgresRepo) FindAndLockExpiredBookings(ctx context.Context, limit int) ([]entity.Booking, error) {
	if limit <= 0 {
		limit = 50
	}

	query := `
		SELECT id, user_id, show_id, total_amount, status, expires_at, created_at, updated_at
		FROM bookings
		WHERE status = 'PENDING' AND expires_at < NOW()
		ORDER BY expires_at ASC
		LIMIT $1
	`
	rows, err := r.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("BookingPostgresRepo - FindAndLockExpiredBookings - query: %w", err)
	}
	defer rows.Close()

	var bookings []entity.Booking
	for rows.Next() {
		var b entity.Booking
		if err := rows.Scan(&b.ID, &b.UserID, &b.ShowID, &b.TotalAmount, &b.Status, &b.ExpiresAt, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("BookingPostgresRepo - FindAndLockExpiredBookings - scan: %w", err)
		}
		bookings = append(bookings, b)
	}

	// Fetch items for each booking
	for i := range bookings {
		queryItems := `SELECT id, booking_id, seat_id, seat_number, price, created_at FROM booking_items WHERE booking_id = $1`
		itemRows, err := r.Pool.Query(ctx, queryItems, bookings[i].ID)
		if err != nil {
			return nil, fmt.Errorf("BookingPostgresRepo - FindAndLockExpiredBookings - items for %s: %w", bookings[i].ID, err)
		}
		for itemRows.Next() {
			var it entity.BookingItem
			if err := itemRows.Scan(&it.ID, &it.BookingID, &it.SeatID, &it.SeatNumber, &it.Price, &it.CreatedAt); err == nil {
				bookings[i].Items = append(bookings[i].Items, it)
			}
		}
		itemRows.Close()
	}

	return bookings, nil
}

// ExpireBookingWithTx chuyển trạng thái đơn sang EXPIRED và ghi Outbox event
func (r *BookingPostgresRepo) ExpireBookingWithTx(ctx context.Context, id string, outbox *entity.OutboxEvent) error {
	tx, err := r.Pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("BookingPostgresRepo - ExpireBookingWithTx - Begin: %w", err)
	}
	defer tx.Rollback(ctx)

	queryUpdate := `UPDATE bookings SET status = $1, updated_at = NOW() WHERE id = $2 AND status = 'PENDING'`
	res, err := tx.Exec(ctx, queryUpdate, entity.BookingStatusExpired, id)
	if err != nil {
		return fmt.Errorf("BookingPostgresRepo - ExpireBookingWithTx - update: %w", err)
	}
	if res.RowsAffected() == 0 {
		// Đơn hàng có thể đã được confirm hoặc cancel trước đó
		return nil
	}

	if outbox != nil {
		if outbox.ID == "" {
			outbox.ID = uuid.New().String()
		}
		outbox.AggregateID = id
		now := time.Now()
		outbox.CreatedAt = now
		outbox.UpdatedAt = now

		queryOutbox := `
			INSERT INTO outbox_events (id, aggregate_type, aggregate_id, event_type, payload, status, retry_count, created_at, updated_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		`
		_, err = tx.Exec(ctx, queryOutbox, outbox.ID, outbox.AggregateType, outbox.AggregateID, outbox.EventType, outbox.Payload, outbox.Status, outbox.RetryCount, outbox.CreatedAt, outbox.UpdatedAt)
		if err != nil {
			return fmt.Errorf("BookingPostgresRepo - ExpireBookingWithTx - insert outbox: %w", err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("BookingPostgresRepo - ExpireBookingWithTx - Commit: %w", err)
	}

	return nil
}

// GetPendingOutboxEvents lấy danh sách các outbox event chưa được gửi
func (r *BookingPostgresRepo) GetPendingOutboxEvents(ctx context.Context, limit int) ([]entity.OutboxEvent, error) {
	if limit <= 0 {
		limit = 20
	}

	query := `
		SELECT id, aggregate_type, aggregate_id, event_type, payload, status, retry_count, error_message, created_at, updated_at
		FROM outbox_events
		WHERE status = 'PENDING'
		ORDER BY created_at ASC
		LIMIT $1
	`
	rows, err := r.Pool.Query(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("BookingPostgresRepo - GetPendingOutboxEvents: %w", err)
	}
	defer rows.Close()

	var events []entity.OutboxEvent
	for rows.Next() {
		var ev entity.OutboxEvent
		if err := rows.Scan(&ev.ID, &ev.AggregateType, &ev.AggregateID, &ev.EventType, &ev.Payload, &ev.Status, &ev.RetryCount, &ev.ErrorMessage, &ev.CreatedAt, &ev.UpdatedAt); err != nil {
			return nil, fmt.Errorf("BookingPostgresRepo - GetPendingOutboxEvents - scan: %w", err)
		}
		events = append(events, ev)
	}

	return events, nil
}

// MarkOutboxPublished đánh dấu event đã gửi thành công
func (r *BookingPostgresRepo) MarkOutboxPublished(ctx context.Context, id string) error {
	query := `UPDATE outbox_events SET status = 'PUBLISHED', updated_at = NOW() WHERE id = $1`
	_, err := r.Pool.Exec(ctx, query, id)
	return err
}

// MarkOutboxFailed đánh dấu event gửi thất bại và tăng retry_count
func (r *BookingPostgresRepo) MarkOutboxFailed(ctx context.Context, id string, errMsg string) error {
	query := `
		UPDATE outbox_events
		SET status = CASE WHEN retry_count >= 5 THEN 'FAILED' ELSE 'PENDING' END,
		    retry_count = retry_count + 1,
		    error_message = $2,
		    updated_at = NOW()
		WHERE id = $1
	`
	_, err := r.Pool.Exec(ctx, query, id, errMsg)
	return err
}
