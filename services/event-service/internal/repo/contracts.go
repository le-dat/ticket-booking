// Package repo implements application outer layer logic. Each logic group in own file.
package repo

import (
	"context"

	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
)

//go:generate mockgen -source=contracts.go -destination=../usecase/mocks_repo_test.go -package=usecase_test

type (
	// EventRepo - Cấu trúc thao tác Database cho Event Service
	EventRepo interface {
		// Venue
		CreateVenue(ctx context.Context, venue *entity.Venue) error
		GetVenueByID(ctx context.Context, id string) (entity.Venue, error)
		
		// Event
		CreateEvent(ctx context.Context, event *entity.Event) error
		GetEventByID(ctx context.Context, id string) (entity.Event, error)
		ListEvents(ctx context.Context, limit, offset int) ([]entity.Event, error)
		
		// Show
		CreateShow(ctx context.Context, show *entity.Show) error
		GetShowByID(ctx context.Context, id string) (entity.Show, error)
		GetShowsByEventID(ctx context.Context, eventID string) ([]entity.Show, error)

		// Seat
		BatchCreateSeats(ctx context.Context, seats []entity.Seat) error
		GetSeatsByShowID(ctx context.Context, showID string) ([]entity.Seat, error)
		LockSeats(ctx context.Context, showID string, seatIDs []string, userID string) (bool, string, []entity.Seat, float64, error)
		ReleaseSeats(ctx context.Context, showID string, seatIDs []string, userID string) (bool, string, error)
	}
)