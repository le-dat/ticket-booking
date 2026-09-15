import { Kafka, Producer } from 'kafkajs';

export class KafkaProducerHelper {
  private producer: Producer;

  constructor(brokers: string[], clientId: string) {
    const kafka = new Kafka({ clientId, brokers });
    // LÝ DO: idempotent: true giúp chống gửi lặp message (duplicate events) khi gặp lỗi mạng/retry
    this.producer = kafka.producer({
      idempotent: true,
      maxInFlightRequests: 1,
    });
  }

  async connect() {
    await this.producer.connect();
  }

  async disconnect() {
    await this.producer.disconnect();
  }

  async send<T extends object = Record<string, unknown>>(topic: string, payload: T, key?: string) {
    await this.producer.send({
      topic,
      messages: [{ key, value: JSON.stringify(payload) }],
    });
  }
}

