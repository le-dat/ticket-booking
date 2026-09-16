export default () => ({
  port: parseInt(process.env.PORT || '3005', 10),
  kafka: {
    brokers: (process.env.KAFKA_BROKERS || 'localhost:9092')
      .split(',')
      .map((b) => b.trim()),
    clientId: process.env.KAFKA_CLIENT_ID || 'notification-service',
    groupId: process.env.KAFKA_GROUP_ID || 'notification-consumer-group',
    paymentEventsTopic:
      process.env.KAFKA_TOPIC_PAYMENT_EVENTS || 'payment-events',
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
  },
  cors: {
    origins: (
      process.env.CORS_ORIGINS || 'http://localhost:3000,http://localhost:8000'
    )
      .split(',')
      .map((origin) => origin.trim()),
  },
});
