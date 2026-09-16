package worker

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"

	"github.com/segmentio/kafka-go"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

type PaymentEventMessage struct {
	EventType            string  `json:"event_type"`
	BookingID            string  `json:"booking_id"`
	UserID               string  `json:"user_id"`
	Amount               float64 `json:"amount"`
	Status               string  `json:"status"`
	GatewayTransactionID string  `json:"gateway_transaction_id"`
}

type PaymentConsumer struct {
	uc     usecase.Booking
	reader *kafka.Reader
	logger logger.Interface
}

func NewPaymentConsumer(
	uc usecase.Booking,
	brokers []string,
	topic string,
	groupID string,
	l logger.Interface,
) *PaymentConsumer {
	r := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        brokers,
		Topic:          topic,
		GroupID:        groupID,
		MinBytes:       10e3, // 10KB
		MaxBytes:       10e6, // 10MB
		CommitInterval: time.Second,
		StartOffset:    kafka.LastOffset,
	})

	return &PaymentConsumer{
		uc:     uc,
		reader: r,
		logger: l,
	}
}

// Start khởi chạy consumer lắng nghe sự kiện từ Kafka topic payment-events
func (c *PaymentConsumer) Start(ctx context.Context) {
	c.logger.Info("Payment Kafka Consumer started (listening on payment-events)...")

	for {
		select {
		case <-ctx.Done():
			c.logger.Info("Payment Kafka Consumer shutting down...")
			_ = c.reader.Close()
			return
		default:
			msg, err := c.reader.FetchMessage(ctx)
			if err != nil {
				if errors.Is(err, context.Canceled) || errors.Is(err, io.EOF) {
					return
				}
				c.logger.Error(fmt.Errorf("payment consumer fetch error: %w", err))
				time.Sleep(1 * time.Second)
				continue
			}

			c.processMessage(ctx, msg)
			if err := c.reader.CommitMessages(ctx, msg); err != nil {
				c.logger.Error(fmt.Errorf("payment consumer commit offset error: %w", err))
			}
		}
	}
}

func (c *PaymentConsumer) processMessage(ctx context.Context, msg kafka.Message) {
	var event PaymentEventMessage
	if err := json.Unmarshal(msg.Value, &event); err != nil {
		c.logger.Error(fmt.Errorf("payment consumer unmarshal error: %w", err))
		return
	}

	c.logger.Info("Payment Consumer: Received event '%s' for booking %s with status %s", event.EventType, event.BookingID, event.Status)

	if event.BookingID == "" {
		return
	}

	switch event.EventType {
	case "PaymentProcessed":
		if event.Status == "SUCCESS" || event.Status == "PAID" {
			_, err := c.uc.ConfirmBooking(ctx, event.BookingID)
			if err != nil {
				c.logger.Error(fmt.Errorf("payment consumer - failed to confirm booking %s: %w", event.BookingID, err))
			} else {
				c.logger.Info("Payment Consumer: Successfully CONFIRMED booking %s", event.BookingID)
			}
		} else if event.Status == "FAILED" {
			_, err := c.uc.CancelBooking(ctx, event.BookingID, event.UserID)
			if err != nil {
				c.logger.Error(fmt.Errorf("payment consumer - failed to cancel failed booking %s: %w", event.BookingID, err))
			}
		}
	}
}
