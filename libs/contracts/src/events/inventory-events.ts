import { z } from 'zod';

export const InventoryReservedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  orderId: z.string().uuid(),
  items: z.array(
    z.object({
      skuId: z.string(),
      quantity: z.number().int().positive(),
    })
  ),
  timestamp: z.string().datetime(),
});

export type InventoryReservedEvent = z.infer<typeof InventoryReservedEventSchema>;

export const InventoryFailedEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  orderId: z.string().uuid(),
  reason: z.string(),
  timestamp: z.string().datetime(),
});

export type InventoryFailedEvent = z.infer<typeof InventoryFailedEventSchema>;
