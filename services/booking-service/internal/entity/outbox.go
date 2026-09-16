package entity

import "time"

const (
	OutboxStatusPending   = "PENDING"
	OutboxStatusPublished = "PUBLISHED"
	OutboxStatusFailed    = "FAILED"

	EventTypeBookingCreated   = "BookingCreated"
	EventTypeBookingCancelled = "BookingCancelled"
	EventTypeBookingConfirmed = "BookingConfirmed"
	EventTypeBookingExpired   = "BookingExpired"
)

type OutboxEvent struct {
	ID            string    `json:"id"`
	AggregateType string    `json:"aggregate_type"`
	AggregateID   string    `json:"aggregate_id"`
	EventType     string    `json:"event_type"`
	Payload       []byte    `json:"payload"`
	Status        string    `json:"status"`
	RetryCount    int       `json:"retry_count"`
	ErrorMessage  *string   `json:"error_message,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}
