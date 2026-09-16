package entity

import "time"

const (
	BookingStatusPending   = "PENDING"
	BookingStatusConfirmed = "CONFIRMED"
	BookingStatusCancelled = "CANCELLED"
	BookingStatusExpired   = "EXPIRED"
)

type Booking struct {
	ID          string        `json:"id"`
	UserID      string        `json:"user_id"`
	ShowID      string        `json:"show_id"`
	TotalAmount float64       `json:"total_amount"`
	Status      string        `json:"status"`
	ExpiresAt   time.Time     `json:"expires_at"`
	Items       []BookingItem `json:"items,omitempty"`
	CreatedAt   time.Time     `json:"created_at"`
	UpdatedAt   time.Time     `json:"updated_at"`
}
