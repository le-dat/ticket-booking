package entity

import "time"

const (
	SeatStatusAvailable = "AVAILABLE"
	SeatStatusHeld      = "HELD"
	SeatStatusBooked    = "BOOKED"
)

type Seat struct {
	ID            string     `json:"id"`
	ShowID        string     `json:"show_id"`
	SeatNumber    string     `json:"seat_number"`
	RowName       string     `json:"row_name"`
	ColIndex      int        `json:"col_index"`
	Price         float64    `json:"price"`
	Status        string     `json:"status"`
	HeldByUserID  *string    `json:"held_by_user_id,omitempty"`
	HoldExpiresAt *time.Time `json:"hold_expires_at,omitempty"`
	Version       int        `json:"version"`
	CreatedAt     time.Time  `json:"created_at"`
	UpdatedAt     time.Time  `json:"updated_at"`
}