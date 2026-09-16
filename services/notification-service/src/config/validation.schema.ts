import * as Joi from 'joi';

export const validationSchema = Joi.object({
  PORT: Joi.number().default(3005),
  KAFKA_BROKERS: Joi.string().required(),
  KAFKA_CLIENT_ID: Joi.string().default('notification-service'),
  KAFKA_GROUP_ID: Joi.string().default('notification-consumer-group'),
  KAFKA_TOPIC_PAYMENT_EVENTS: Joi.string().default('payment-events'),
  REDIS_URL: Joi.string().required(),
  CORS_ORIGINS: Joi.string().default(
    'http://localhost:3000,http://localhost:8000',
  ),
});
