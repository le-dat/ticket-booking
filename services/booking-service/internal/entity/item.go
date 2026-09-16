package entity

import "time"

type BookingItem struct {
	ID         string    `json:"id"`
	BookingID  string    `json:"booking_id"`
	SeatID     string    `json:"seat_id"`
	SeatNumber string    `json:"seat_number"`
	Price      float64   `json:"price"`
	CreatedAt  time.Time `json:"created_at"`
}
