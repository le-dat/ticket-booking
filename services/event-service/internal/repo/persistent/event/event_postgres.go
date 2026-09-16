package event

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/repo"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/postgres"
)

type Repo struct {
	*postgres.Postgres
}

var _ repo.EventRepo = (*Repo)(nil)

func New(pg *postgres.Postgres) repo.EventRepo {
	return &Repo{pg}
}

func (r *Repo) CreateVenue(ctx context.Context, v *entity.Venue) error {
	query := `INSERT INTO venues (name, address, capacity) VALUES ($1, $2, $3) RETURNING id, created_at, updated_at`
	return r.Pool.QueryRow(ctx, query, v.Name, v.Address, v.Capacity).Scan(&v.ID, &v.CreatedAt, &v.UpdatedAt)
}

func (r *Repo) GetVenueByID(ctx context.Context, id string) (entity.Venue, error) {
	query := `SELECT id, name, address, capacity, created_at, updated_at FROM venues WHERE id = $1`
	var v entity.Venue
	err := r.Pool.QueryRow(ctx, query, id).Scan(&v.ID, &v.Name, &v.Address, &v.Capacity, &v.CreatedAt, &v.UpdatedAt)
	return v, err
}

func (r *Repo) CreateEvent(ctx context.Context, e *entity.Event) error {
	query := `INSERT INTO events (venue_id, title, description, banner_url, status) VALUES ($1, $2, $3, $4, $5) RETURNING id, created_at, updated_at`
	return r.Pool.QueryRow(ctx, query, e.VenueID, e.Title, e.Description, e.BannerURL, e.Status).Scan(&e.ID, &e.CreatedAt, &e.UpdatedAt)
}

func (r *Repo) GetEventByID(ctx context.Context, id string) (entity.Event, error) {
	query := `SELECT id, venue_id, title, description, banner_url, status, created_at, updated_at FROM events WHERE id = $1`
	var e entity.Event
	err := r.Pool.QueryRow(ctx, query, id).Scan(&e.ID, &e.VenueID, &e.Title, &e.Description, &e.BannerURL, &e.Status, &e.CreatedAt, &e.UpdatedAt)
	return e, err
}

func (r *Repo) ListEvents(ctx context.Context, limit, offset int) ([]entity.Event, error) {
	query := `SELECT id, venue_id, title, description, banner_url, status, created_at, updated_at FROM events ORDER BY created_at DESC LIMIT $1 OFFSET $2`
	rows, err := r.Pool.Query(ctx, query, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []entity.Event
	for rows.Next() {
		var e entity.Event
		if err := rows.Scan(&e.ID, &e.VenueID, &e.Title, &e.Description, &e.BannerURL, &e.Status, &e.CreatedAt, &e.UpdatedAt); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, nil
}

func (r *Repo) CreateShow(ctx context.Context, s *entity.Show) error {
	query := `INSERT INTO shows (event_id, start_time, end_time, status) VALUES ($1, $2, $3, $4) RETURNING id, created_at, updated_at`
	return r.Pool.QueryRow(ctx, query, s.EventID, s.StartTime, s.EndTime, s.Status).Scan(&s.ID, &s.CreatedAt, &s.UpdatedAt)
}

func (r *Repo) GetShowByID(ctx context.Context, id string) (entity.Show, error) {
	query := `SELECT id, event_id, start_time, end_time, status, created_at, updated_at FROM shows WHERE id = $1`
	var s entity.Show
	err := r.Pool.QueryRow(ctx, query, id).Scan(&s.ID, &s.EventID, &s.StartTime, &s.EndTime, &s.Status, &s.CreatedAt, &s.UpdatedAt)
	return s, err
}

func (r *Repo) GetShowsByEventID(ctx context.Context, eventID string) ([]entity.Show, error) {
	query := `SELECT id, event_id, start_time, end_time, status, created_at, updated_at FROM shows WHERE event_id = $1 ORDER BY start_time ASC`
	rows, err := r.Pool.Query(ctx, query, eventID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var shows []entity.Show
	for rows.Next() {
		var s entity.Show
		if err := rows.Scan(&s.ID, &s.EventID, &s.StartTime, &s.EndTime, &s.Status, &s.CreatedAt, &s.UpdatedAt); err != nil {
			return nil, err
		}
		shows = append(shows, s)
	}
	return shows, nil
}

func (r *Repo) BatchCreateSeats(ctx context.Context, seats []entity.Seat) error {
	batch := &pgx.Batch{}
	query := `INSERT INTO seats (show_id, seat_number, row_name, col_index, price, status) VALUES ($1, $2, $3, $4, $5, $6)`

	for _, s := range seats {
		batch.Queue(query, s.ShowID, s.SeatNumber, s.RowName, s.ColIndex, s.Price, s.Status)
	}

	br := r.Pool.SendBatch(ctx, batch)
	defer br.Close()

	for i := 0; i < len(seats); i++ {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("batch insert seat index %d failed: %w", i, err)
		}
	}
	return nil
}

func (r *Repo) GetSeatsByShowID(ctx context.Context, showID string) ([]entity.Seat, error) {
	query := `SELECT id, show_id, seat_number, row_name, col_index, price, status, held_by_user_id, hold_expires_at, version, created_at, updated_at 
	          FROM seats WHERE show_id = $1 ORDER BY row_name, col_index`
	rows, err := r.Pool.Query(ctx, query, showID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var seats []entity.Seat
	for rows.Next() {
		var s entity.Seat
		if err := rows.Scan(&s.ID, &s.ShowID, &s.SeatNumber, &s.RowName, &s.ColIndex, &s.Price, &s.Status, &s.HeldByUserID, &s.HoldExpiresAt, &s.Version, &s.CreatedAt, &s.UpdatedAt); err != nil {
			return nil, err
		}
		seats = append(seats, s)
	}
	return seats, nil
}

func (r *Repo) LockSeats(ctx context.Context, showID string, seatIDs []string, userID string) (bool, string, error) {
	tx, err := r.Pool.Begin(ctx)
	if err != nil {
		return false, "Không thể khởi tạo transaction", err
	}
	defer tx.Rollback(ctx)

	queryCheck := `SELECT id, status FROM seats WHERE show_id = $1 AND id = ANY($2) FOR UPDATE`
	rows, err := tx.Query(ctx, queryCheck, showID, seatIDs)
	if err != nil {
		return false, "Lỗi truy vấn trạng thái ghế", err
	}
	defer rows.Close()

	count := 0
	for rows.Next() {
		var id, status string
		if err := rows.Scan(&id, &status); err != nil {
			return false, "Lỗi scan dữ liệu ghế", err
		}
		if status != entity.SeatStatusAvailable {
			return false, fmt.Sprintf("Ghế %s không còn sẵn có (trạng thái: %s)", id, status), nil
		}
		count++
	}

	if count != len(seatIDs) {
		return false, "Một số danh mục ghế không tồn tại", nil
	}

	holdExpiry := time.Now().Add(10 * time.Minute)
	queryUpdate := `UPDATE seats SET status = $1, held_by_user_id = $2, hold_expires_at = $3, updated_at = NOW() 
	               WHERE show_id = $4 AND id = ANY($5)`
	_, err = tx.Exec(ctx, queryUpdate, entity.SeatStatusHeld, userID, holdExpiry, showID, seatIDs)
	if err != nil {
		return false, "Lỗi cập nhật trạng thái giữ ghế", err
	}

	if err := tx.Commit(ctx); err != nil {
		return false, "Lỗi commit transaction giữ ghế", err
	}

	return true, "Giữ ghế thành công trong 10 phút", nil
}
