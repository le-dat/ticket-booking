// Package usecase implements application business logic. Each logic group in own file.
package usecase

import (
	"context"
	"time"

	"github.com/zentrix-app/zentrix-backend-go-temp/internal/entity"
)

//go:generate mockgen -source=contracts.go -destination=./mocks_usecase_test.go -package=usecase_test

type (
	// Event - Usecase nghiệp vụ cho Event Service
	Event interface {
		CreateVenue(ctx context.Context, name, address string, capacity int) (entity.Venue, error)
		CreateEvent(ctx context.Context, venueID, title, description, bannerURL string) (entity.Event, error)
		CreateShowWithSeats(ctx context.Context, eventID string, startTime, endTime time.Time, rows int, cols int, price float64) (entity.Show, error)
		ListEvents(ctx context.Context, limit, offset int) ([]entity.Event, error)
		GetEventDetail(ctx context.Context, eventID string) (entity.Event, []entity.Show, error)
		GetShowSeats(ctx context.Context, showID string) ([]entity.Seat, error)
		LockSeats(ctx context.Context, showID string, seatIDs []string, userID string) (bool, string, error)
	}
)
