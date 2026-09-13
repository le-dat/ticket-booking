import { z } from 'zod'; // LÝ DO: Dùng Zod để validate dữ liệu runtime từ Kafka (tránh nhận sai kiểu gây crash app)

// Schema validate từng mặt hàng trong Event
export const OrderItemSchema = z.object({
  skuId: z.string(), // Mã SKU sản phẩm
  quantity: z.number().int().positive(), // LÝ DO: Số lượng bắt buộc là số nguyên dương (> 0)
  priceInCents: z.number().int().nonnegative(), // LÝ DO: Giá tiền là số nguyên >= 0
});

// Schema validate Event OrderCreated khi được bắn vào Kafka topic `order-events`
export const OrderCreatedEventSchema = z.object({
  eventId: z.string().uuid(), // LÝ DO: Idempotency Key (UUID) để Consumer kiểm tra chống xử lý lặp tin nhắn
  correlationId: z.string().uuid(), // LÝ DO: Trace ID dùng để lọc log trên toàn bộ hệ thống từ Gateway -> Worker
  orderId: z.string().uuid(), // ID của đơn hàng vừa tạo trong order_db
  userId: z.string().uuid(), // ID của người mua
  totalAmountInCents: z.number().int().positive(), // Tổng tiền đơn hàng
  items: z.array(OrderItemSchema), // Mảng các sản phẩm
  timestamp: z.string().datetime(), // Thời điểm tạo event dạng ISO string
});

// LÝ DO: Tự động trích xuất TypeScript Type từ Zod Schema mà không cần viết lại interface thủ công
export type OrderCreatedEvent = z.infer<typeof OrderCreatedEventSchema>;

export const OrderCancelledEventSchema = z.object({
  eventId: z.string().uuid(),
  correlationId: z.string().uuid(),
  orderId: z.string().uuid(),
  userId: z.string().uuid(),
  reason: z.string(),
  timestamp: z.string().datetime(),
});

export type OrderCancelledEvent = z.infer<typeof OrderCancelledEventSchema>;
