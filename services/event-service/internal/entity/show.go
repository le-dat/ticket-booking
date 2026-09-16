package entity

import "time"

const (
	ShowStatusScheduled = "SCHEDULED"
	ShowStatusOnSale    = "ON_SALE"
	ShowStatusCompleted = "COMPLETED"
	ShowStatusCancelled = "CANCELLED"
)

type Show struct {
	ID        string    `json:"id"`
	EventID   string    `json:"event_id"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}