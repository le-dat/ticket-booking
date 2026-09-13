import { Kafka, Consumer, EachMessagePayload } from 'kafkajs';

export class KafkaConsumerHelper {
  private consumer: Consumer;

  constructor(brokers: string[], groupId: string) {
    const kafka = new Kafka({ clientId: groupId, brokers });
    this.consumer = kafka.consumer({ groupId });
  }

  async connect() {
    await this.consumer.connect();
  }

  async subscribe(topic: string | string[]) {
    const topics = Array.isArray(topic) ? topic : [topic];
    for (const t of topics) {
      await this.consumer.subscribe({ topic: t, fromBeginning: false });
    }
  }

  async run(
    handler: (payload: EachMessagePayload) => Promise<void>,
    onError?: (error: unknown, payload: EachMessagePayload) => Promise<void> | void
  ) {
    await this.consumer.run({
      eachMessage: async (payload) => {
        try {
          await handler(payload);
        } catch (err) {
          // LÝ DO: Catch lỗi trong handler để tránh crash consumer loop hoặc bị lặp vô tận không kiểm soát
          if (onError) {
            await onError(err, payload);
          } else {
            console.error(
              `[KafkaConsumer] Error processing topic: ${payload.topic}, partition: ${payload.partition}, offset: ${payload.message.offset}:`,
              err
            );
          }
        }
      },
    });
  }

  async disconnect() {
    await this.consumer.disconnect();
  }
}

