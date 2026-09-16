package event

import (
	"context"
	"fmt"
	"time"

	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/repo"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
)

type UseCase struct {
	repo repo.EventRepo
}

var _ usecase.Event = (*UseCase)(nil)

func New(r repo.EventRepo) usecase.Event {
	return &UseCase{repo: r}
}

func (uc *UseCase) CreateVenue(ctx context.Context, name, address string, capacity int) (entity.Venue, error) {
	v := entity.Venue{
		Name:     name,
		Address:  address,
		Capacity: capacity,
	}
	err := uc.repo.CreateVenue(ctx, &v)
	return v, err
}

func (uc *UseCase) CreateEvent(ctx context.Context, venueID, title, description, bannerURL string) (entity.Event, error) {
	e := entity.Event{
		VenueID:     venueID,
		Title:       title,
		Description: description,
		BannerURL:   bannerURL,
		Status:      entity.EventStatusPublished,
	}
	err := uc.repo.CreateEvent(ctx, &e)
	return e, err
}

func (uc *UseCase) CreateShowWithSeats(ctx context.Context, eventID string, startTime, endTime time.Time, rows int, cols int, price float64) (entity.Show, error) {
	s := entity.Show{
		EventID:   eventID,
		StartTime: startTime,
		EndTime:   endTime,
		Status:    entity.ShowStatusOnSale,
	}
	if err := uc.repo.CreateShow(ctx, &s); err != nil {
		return s, err
	}

	var seats []entity.Seat
	for r := 0; r < rows; r++ {
		rowLetter := string(rune('A' + r))
		for c := 1; c <= cols; c++ {
			seatNum := fmt.Sprintf("%s%d", rowLetter, c)
			seats = append(seats, entity.Seat{
				ShowID:     s.ID,
				SeatNumber: seatNum,
				RowName:    rowLetter,
				ColIndex:   c,
				Price:      price,
				Status:     entity.SeatStatusAvailable,
			})
		}
	}

	if err := uc.repo.BatchCreateSeats(ctx, seats); err != nil {
		return s, fmt.Errorf("tạo suất chiếu thành công nhưng lỗi tạo ghế: %w", err)
	}

	return s, nil
}

func (uc *UseCase) ListEvents(ctx context.Context, limit, offset int) ([]entity.Event, error) {
	if limit <= 0 {
		limit = 10
	}
	return uc.repo.ListEvents(ctx, limit, offset)
}

func (uc *UseCase) GetEventDetail(ctx context.Context, eventID string) (entity.Event, []entity.Show, error) {
	e, err := uc.repo.GetEventByID(ctx, eventID)
	if err != nil {
		return e, nil, err
	}
	shows, err := uc.repo.GetShowsByEventID(ctx, eventID)
	return e, shows, err
}

func (uc *UseCase) GetShowSeats(ctx context.Context, showID string) ([]entity.Seat, error) {
	return uc.repo.GetSeatsByShowID(ctx, showID)
}

func (uc *UseCase) LockSeats(ctx context.Context, showID string, seatIDs []string, userID string) (bool, string, []entity.Seat, float64, error) {
	return uc.repo.LockSeats(ctx, showID, seatIDs, userID)
}

func (uc *UseCase) ReleaseSeats(ctx context.Context, showID string, seatIDs []string, userID string) (bool, string, error) {
	return uc.repo.ReleaseSeats(ctx, showID, seatIDs, userID)
}
