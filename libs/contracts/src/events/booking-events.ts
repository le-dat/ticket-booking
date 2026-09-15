import { z } from 'zod';

export const BookedSeatItemSchema = z.object({
  seatId: z.string(),
  rowName: z.string(),
  seatNumber: z.number().int().positive(),
  priceInCents: z.number().int().nonnegative(),
});

export const BookingCreatedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  bookingId: z.string().uuid(),
  showId: z.string(),
  userId: z.string().uuid(),
  totalAmountInCents: z.number().int().positive(),
  expiresAt: z.string().datetime(),
  seats: z.array(BookedSeatItemSchema),
  timestamp: z.string().datetime(),
});

export type BookingCreatedEvent = z.infer<typeof BookingCreatedEventSchema>;

export const BookingConfirmedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  bookingId: z.string().uuid(),
  showId: z.string(),
  userId: z.string().uuid(),
  paymentTransactionId: z.string(),
  timestamp: z.string().datetime(),
});

export type BookingConfirmedEvent = z.infer<typeof BookingConfirmedEventSchema>;

export const BookingCancelledEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  bookingId: z.string().uuid(),
  showId: z.string(),
  userId: z.string().uuid(),
  reason: z.string(),
  timestamp: z.string().datetime(),
});

export type BookingCancelledEvent = z.infer<typeof BookingCancelledEventSchema>;
