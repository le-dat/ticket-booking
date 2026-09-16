package redis

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

var (
	ErrSeatAlreadyLocked = errors.New("one or more seats are currently locked by another user")
)

// releaseLuaScript đảm bảo chỉ xoá lock nếu value trùng khớp với userID
const releaseLuaScript = `
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
`

type SeatLockManager struct {
	client *redis.Client
}

func NewSeatLockManager(client *redis.Client) *SeatLockManager {
	return &SeatLockManager{client: client}
}

func seatKey(showID, seatID string) string {
	return fmt.Sprintf("lock:show:%s:seat:%s", showID, seatID)
}

// AcquireSeatLocks khoá danh sách ghế. Nếu có bất kỳ ghế nào đã bị khoá, rollback toàn bộ ghế đã khoá trước đó
func (m *SeatLockManager) AcquireSeatLocks(ctx context.Context, showID string, seatIDs []string, userID string, ttl time.Duration) ([]string, error) {
	var lockedKeys []string

	for _, seatID := range seatIDs {
		key := seatKey(showID, seatID)
		ok, err := m.client.SetNX(ctx, key, userID, ttl).Result()
		if err != nil {
			m.rollbackLocks(ctx, lockedKeys, userID)
			return nil, fmt.Errorf("redis SetNX error on key %s: %w", key, err)
		}

		if !ok {
			// Ghế đã có người giữ -> Rollback các ghế vừa khoá thành công
			m.rollbackLocks(ctx, lockedKeys, userID)
			return nil, fmt.Errorf("%w: seat %s", ErrSeatAlreadyLocked, seatID)
		}

		lockedKeys = append(lockedKeys, key)
	}

	return lockedKeys, nil
}

// ReleaseSeatLocks giải phóng danh sách ghế an toàn
func (m *SeatLockManager) ReleaseSeatLocks(ctx context.Context, showID string, seatIDs []string, userID string) error {
	for _, seatID := range seatIDs {
		key := seatKey(showID, seatID)
		if userID == "" {
			// Force delete (dành cho Expiry Worker hoặc Payment Confirmation)
			_ = m.client.Del(ctx, key).Err()
		} else {
			_ = m.client.Eval(ctx, releaseLuaScript, []string{key}, userID).Err()
		}
	}
	return nil
}

func (m *SeatLockManager) rollbackLocks(ctx context.Context, keys []string, userID string) {
	for _, key := range keys {
		_ = m.client.Eval(ctx, releaseLuaScript, []string{key}, userID).Err()
	}
}
