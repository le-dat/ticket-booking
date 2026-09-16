package v1

import (
	"errors"
	"net/http"

	"github.com/gofiber/fiber/v2"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/controller/restapi/middleware"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/persistent/booking"
	redisRepo "github.com/zentrix-app/zentrix-backend-go-temp/internal/repo/redis"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	bookingUc "github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase/booking"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

type bookingRoutes struct {
	u usecase.Booking
	l logger.Interface
}

func newBookingRoutes(handler fiber.Router, u usecase.Booking, l logger.Interface) {
	r := &bookingRoutes{u: u, l: l}

	h := handler.Group("/bookings", middleware.Auth())
	{
		h.Post("/", r.createBooking)
		h.Get("/:id", r.getBooking)
		h.Post("/:id/cancel", r.cancelBooking)
	}
}

type createBookingRequest struct {
	ShowID  string   `json:"show_id"`
	SeatIDs []string `json:"seat_ids"`
}

func (r *bookingRoutes) createBooking(c *fiber.Ctx) error {
	userID, _ := c.Locals("userID").(string)
	if userID == "" {
		return c.Status(http.StatusUnauthorized).JSON(fiber.Map{
			"error": "Thiếu định danh người dùng (X-User-ID)",
		})
	}

	var req createBookingRequest
	if err := c.BodyParser(&req); err != nil {
		r.l.Error(err, "http - v1 - createBooking - BodyParser")
		return c.Status(http.StatusBadRequest).JSON(fiber.Map{
			"error": "Dữ liệu yêu cầu không hợp lệ",
		})
	}

	if req.ShowID == "" || len(req.SeatIDs) == 0 {
		return c.Status(http.StatusBadRequest).JSON(fiber.Map{
			"error": "Thiếu thông tin bắt buộc: show_id, seat_ids",
		})
	}

	b, err := r.u.CreateBooking(c.UserContext(), userID, req.ShowID, req.SeatIDs)
	if err != nil {
		r.l.Error(err, "http - v1 - createBooking")

		if errors.Is(err, redisRepo.ErrSeatAlreadyLocked) {
			return c.Status(http.StatusConflict).JSON(fiber.Map{
				"error": "Một hoặc nhiều ghế đã được giữ bởi người khác. Vui lòng chọn ghế khác!",
			})
		}
		if errors.Is(err, bookingUc.ErrSeatValidationFail) || errors.Is(err, bookingUc.ErrInvalidInput) {
			return c.Status(http.StatusBadRequest).JSON(fiber.Map{
				"error": err.Error(),
			})
		}

		return c.Status(http.StatusInternalServerError).JSON(fiber.Map{
			"error": "Lỗi hệ thống khi khởi tạo đặt vé: " + err.Error(),
		})
	}

	return c.Status(http.StatusCreated).JSON(b)
}

func (r *bookingRoutes) getBooking(c *fiber.Ctx) error {
	userID, _ := c.Locals("userID").(string)
	id := c.Params("id")
	if id == "" {
		return c.Status(http.StatusBadRequest).JSON(fiber.Map{
			"error": "Mã đơn hàng không hợp lệ",
		})
	}

	b, err := r.u.GetBooking(c.UserContext(), id)
	if err != nil {
		if errors.Is(err, booking.ErrBookingNotFound) {
			return c.Status(http.StatusNotFound).JSON(fiber.Map{
				"error": "Không tìm thấy đơn đặt vé",
			})
		}
		r.l.Error(err, "http - v1 - getBooking")
		return c.Status(http.StatusInternalServerError).JSON(fiber.Map{
			"error": "Lỗi hệ thống khi tra cứu đơn vé",
		})
	}

	// Đảm bảo chỉ chủ sở hữu mới xem được thông tin đơn
	if userID != "" && b.UserID != userID {
		return c.Status(http.StatusForbidden).JSON(fiber.Map{
			"error": "Bạn không có quyền truy cập đơn vé của người khác",
		})
	}

	return c.Status(http.StatusOK).JSON(b)
}

func (r *bookingRoutes) cancelBooking(c *fiber.Ctx) error {
	userID, _ := c.Locals("userID").(string)
	if userID == "" {
		return c.Status(http.StatusUnauthorized).JSON(fiber.Map{
			"error": "Thiếu định danh người dùng (X-User-ID)",
		})
	}

	id := c.Params("id")
	if id == "" {
		return c.Status(http.StatusBadRequest).JSON(fiber.Map{
			"error": "Mã đơn hàng không hợp lệ",
		})
	}

	// Kiểm tra quyền sở hữu trước khi hủy
	existing, err := r.u.GetBooking(c.UserContext(), id)
	if err != nil {
		if errors.Is(err, booking.ErrBookingNotFound) {
			return c.Status(http.StatusNotFound).JSON(fiber.Map{
				"error": "Không tìm thấy đơn đặt vé",
			})
		}
		return c.Status(http.StatusInternalServerError).JSON(fiber.Map{
			"error": "Lỗi hệ thống khi tra cứu đơn vé",
		})
	}
	if existing.UserID != userID {
		return c.Status(http.StatusForbidden).JSON(fiber.Map{
			"error": "Bạn không có quyền hủy đơn vé của người khác",
		})
	}

	b, err := r.u.CancelBooking(c.UserContext(), id, userID)
	if err != nil {
		r.l.Error(err, "http - v1 - cancelBooking")
		if errors.Is(err, booking.ErrBookingNotFound) {
			return c.Status(http.StatusNotFound).JSON(fiber.Map{
				"error": "Không tìm thấy đơn đặt vé",
			})
		}
		if errors.Is(err, booking.ErrBookingNotPending) {
			return c.Status(http.StatusBadRequest).JSON(fiber.Map{
				"error": "Chỉ có thể hủy đơn đang ở trạng thái chờ thanh toán (PENDING)",
			})
		}
		return c.Status(http.StatusInternalServerError).JSON(fiber.Map{
			"error": "Lỗi hệ thống khi hủy đơn vé",
		})
	}

	return c.Status(http.StatusOK).JSON(fiber.Map{
		"message": "Đã hủy đơn đặt vé thành công",
		"booking": b,
	})
}
