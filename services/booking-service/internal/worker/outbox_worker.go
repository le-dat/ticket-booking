package worker

import (
	"context"
	"fmt"
	"time"

	"github.com/segmentio/kafka-go"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/repo"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

type OutboxWorker struct {
	repo          repo.OutboxRepo
	writer        *kafka.Writer
	logger        logger.Interface
	batchSize     int
	flushInterval time.Duration
}

func NewOutboxWorker(
	r repo.OutboxRepo,
	brokers []string,
	topic string,
	batchSize int,
	flushInterval time.Duration,
	l logger.Interface,
) *OutboxWorker {
	if batchSize <= 0 {
		batchSize = 20
	}
	if flushInterval <= 0 {
		flushInterval = 1 * time.Second
	}

	w := &kafka.Writer{
		Addr:         kafka.TCP(brokers...),
		Topic:        topic,
		Balancer:     &kafka.LeastBytes{},
		RequiredAcks: kafka.RequireOne,
		Async:        false,
	}

	return &OutboxWorker{
		repo:          r,
		writer:        w,
		logger:        l,
		batchSize:     batchSize,
		flushInterval: flushInterval,
	}
}

// Start khởi chạy worker chạy ngầm định kỳ quét outbox_events và đẩy lên Kafka
func (w *OutboxWorker) Start(ctx context.Context) {
	w.logger.Info("Outbox Worker started (polling outbox_events -> Kafka)...")

	ticker := time.NewTicker(w.flushInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			w.logger.Info("Outbox Worker shutting down...")
			_ = w.writer.Close()
			return
		case <-ticker.C:
			w.processPendingEvents(ctx)
		}
	}
}

func (w *OutboxWorker) processPendingEvents(ctx context.Context) {
	events, err := w.repo.GetPendingOutboxEvents(ctx, w.batchSize)
	if err != nil {
		w.logger.Error(fmt.Errorf("outbox worker - query events: %w", err))
		return
	}

	for _, ev := range events {
		msg := kafka.Message{
			Key:   []byte(ev.AggregateID),
			Value: ev.Payload,
			Time:  time.Now(),
		}

		err := w.writer.WriteMessages(ctx, msg)
		if err != nil {
			w.logger.Error(fmt.Errorf("outbox worker - publish event %s failed: %w", ev.ID, err))
			_ = w.repo.MarkOutboxFailed(ctx, ev.ID, err.Error())
			continue
		}

		_ = w.repo.MarkOutboxPublished(ctx, ev.ID)
		w.logger.Info("Outbox Worker: Published event %s (%s) for booking %s to Kafka", ev.ID, ev.EventType, ev.AggregateID)
	}
}
