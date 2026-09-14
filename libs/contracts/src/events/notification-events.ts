import { z } from 'zod';

export const TicketIssuedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  ticketId: z.string().uuid(),
  bookingId: z.string().uuid(),
  userId: z.string().uuid(),
  qrCodeUrl: z.string(),
  showId: z.string(),
  seatDetails: z.array(z.object({
    seatId: z.string(),
    rowName: z.string(),
    seatNumber: z.number(),
  })),
  timestamp: z.string().datetime(),
});

export type TicketIssuedEvent = z.infer<typeof TicketIssuedEventSchema>;
