export interface PaymentProcessedEvent {
  event_type: string;
  booking_id: string;
  user_id: string;
  amount: number;
  status: string;
  gateway_transaction_id: string;
}
