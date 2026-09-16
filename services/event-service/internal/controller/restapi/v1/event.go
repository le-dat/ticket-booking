package v1

import (
	"strconv"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/usecase"
	"github.com/zentrix-app/zentrix-backend-go-temp/pkg/logger"
)

type eventRoutes struct {
	u usecase.Event
	l logger.Interface
}

func newEventRoutes(handler fiber.Router, u usecase.Event, l logger.Interface) {
	r := &eventRoutes{u: u, l: l}

	handler.Get("/events", r.listEvents)
	handler.Get("/events/:id", r.getEventDetail)
	handler.Get("/shows/:id/seats", r.getShowSeats)
	
	// Admin routes
	handler.Post("/venues", r.createVenue)
	handler.Post("/events", r.createEvent)
	handler.Post("/events/:id/shows", r.createShow)
}

func (r *eventRoutes) listEvents(c *fiber.Ctx) error {
	limit, _ := strconv.Atoi(c.Query("limit", "10"))
	offset, _ := strconv.Atoi(c.Query("offset", "0"))

	events, err := r.u.ListEvents(c.Context(), limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(fiber.Map{"data": events})
}

func (r *eventRoutes) getEventDetail(c *fiber.Ctx) error {
	eventID := c.Params("id")
	event, shows, err := r.u.GetEventDetail(c.Context(), eventID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{"error": "Không tìm thấy sự kiện"})
	}
	return c.JSON(fiber.Map{"event": event, "shows": shows})
}

func (r *eventRoutes) getShowSeats(c *fiber.Ctx) error {
	showID := c.Params("id")
	seats, err := r.u.GetShowSeats(c.Context(), showID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(fiber.Map{"seats": seats})
}

type createVenueRequest struct {
	Name     string `json:"name"`
	Address  string `json:"address"`
	Capacity int    `json:"capacity"`
}

func (r *eventRoutes) createVenue(c *fiber.Ctx) error {
	var req createVenueRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request"})
	}
	venue, err := r.u.CreateVenue(c.Context(), req.Name, req.Address, req.Capacity)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.Status(fiber.StatusCreated).JSON(venue)
}

type createEventRequest struct {
	VenueID     string `json:"venue_id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	BannerURL   string `json:"banner_url"`
}

func (r *eventRoutes) createEvent(c *fiber.Ctx) error {
	var req createEventRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request"})
	}
	event, err := r.u.CreateEvent(c.Context(), req.VenueID, req.Title, req.Description, req.BannerURL)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.Status(fiber.StatusCreated).JSON(event)
}

type createShowRequest struct {
	StartTime string  `json:"start_time"`
	EndTime   string  `json:"end_time"`
	Rows      int     `json:"rows"`
	Cols      int     `json:"cols"`
	Price     float64 `json:"price"`
}

func (r *eventRoutes) createShow(c *fiber.Ctx) error {
	eventID := c.Params("id")
	var req createShowRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request"})
	}

	start, _ := time.Parse(time.RFC3339, req.StartTime)
	end, _ := time.Parse(time.RFC3339, req.EndTime)

	show, err := r.u.CreateShowWithSeats(c.Context(), eventID, start, end, req.Rows, req.Cols, req.Price)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": err.Error()})
	}
	return c.Status(fiber.StatusCreated).JSON(show)
}