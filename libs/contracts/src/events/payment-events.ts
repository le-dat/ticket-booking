import { z } from 'zod';

export const PaymentCompletedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  paymentId: z.string().uuid(),
  orderId: z.string().uuid(),
  amountInCents: z.number().int().positive(),
  timestamp: z.string().datetime(),
});

export type PaymentCompletedEvent = z.infer<typeof PaymentCompletedEventSchema>;

export const PaymentFailedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  orderId: z.string().uuid(),
  reason: z.string(),
  timestamp: z.string().datetime(),
});

export type PaymentFailedEvent = z.infer<typeof PaymentFailedEventSchema>;
