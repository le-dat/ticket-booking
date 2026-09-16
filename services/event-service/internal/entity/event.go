package entity

import "time"

const (
	EventStatusDraft     = "DRAFT"
	EventStatusPublished = "PUBLISHED"
	EventStatusCancelled = "CANCELLED"
)

type Event struct {
	ID          string    `json:"id"`
	VenueID     string    `json:"venue_id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	BannerURL   string    `json:"banner_url"`
	Status      string    `json:"status"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}