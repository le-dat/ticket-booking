import {
  Injectable,
  Logger,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Consumer, Kafka } from 'kafkajs';
import { EventsGateway } from '../gateway/events.gateway';
import { QrCodeService } from '../qrcode/qrcode.service';
import { PaymentProcessedEvent } from './dto/payment-processed-event.dto';

@Injectable()
export class KafkaConsumerService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(KafkaConsumerService.name);
  private kafka: Kafka;
  private consumer: Consumer;
  private isConnected = false;

  constructor(
    private readonly configService: ConfigService,
    private readonly eventsGateway: EventsGateway,
    private readonly qrCodeService: QrCodeService,
  ) {}

  async onModuleInit(): Promise<void> {
    const brokers = this.configService.get<string[]>('kafka.brokers', [
      'localhost:9092',
    ]);
    const clientId = this.configService.get<string>(
      'kafka.clientId',
      'notification-service',
    );
    const groupId = this.configService.get<string>(
      'kafka.groupId',
      'notification-consumer-group',
    );
    const topic = this.configService.get<string>(
      'kafka.paymentEventsTopic',
      'payment-events',
    );

    this.kafka = new Kafka({
      clientId,
      brokers,
      retry: {
        initialRetryTime: 300,
        retries: 5,
      },
    });

    this.consumer = this.kafka.consumer({ groupId });

    try {
      this.logger.log(`Connecting to Kafka brokers: ${brokers.join(', ')}...`);
      await this.consumer.connect();
      this.isConnected = true;
      this.logger.log('Connected to Kafka successfully.');

      await this.consumer.subscribe({ topic, fromBeginning: false });
      this.logger.log(`Subscribed to topic '${topic}' with group '${groupId}'`);

      await this.consumer.run({
        eachMessage: async ({ topic, partition, message }) => {
          await this.processMessage(topic, partition, message);
        },
      });
    } catch (error) {
      this.isConnected = false;
      this.logger.error(
        `Failed to start Kafka consumer: ${error.message}. Will continue operating HTTP/WS server.`,
        error.stack,
      );
    }
  }

  async processMessage(
    topic: string,
    partition: number,
    message: any,
  ): Promise<void> {
    try {
      if (!message.value) {
        return;
      }

      const rawContent = message.value.toString();
      this.logger.debug(
        `Received message on [${topic} p:${partition}]: ${rawContent}`,
      );

      const parsed: PaymentProcessedEvent = JSON.parse(rawContent);

      if (
        parsed.event_type === 'PaymentProcessed' &&
        parsed.status === 'SUCCESS'
      ) {
        await this.handlePaymentProcessed(parsed);
      }
    } catch (error) {
      this.logger.error(
        `Error processing Kafka message on ${topic}: ${error.message}`,
        error.stack,
      );
    }
  }

  async handlePaymentProcessed(event: PaymentProcessedEvent): Promise<void> {
    const { booking_id, user_id, amount, gateway_transaction_id } = event;

    this.logger.log(
      `Processing confirmed ticket notification for booking: ${booking_id} (user: ${user_id})`,
    );

    // 1. Generate E-Ticket QR Code (Base64 PNG Data URL)
    const qrCodeDataUrl = await this.qrCodeService.generateTicketQRCode({
      bookingId: booking_id,
      userId: user_id,
      txId: gateway_transaction_id,
    });

    // 2. Broadcast realtime via WebSocket room 'user:{userId}'
    this.eventsGateway.sendToUser(user_id, 'BookingConfirmed', {
      bookingId: booking_id,
      amount,
      status: 'CONFIRMED',
      qrCode: qrCodeDataUrl,
      message: 'Thanh toán thành công! Vé điện tử của bạn đã sẵn sàng.',
      timestamp: new Date().toISOString(),
    });

    this.logger.log(
      `Broadcasted 'BookingConfirmed' with QR code to user ${user_id} for booking ${booking_id}`,
    );
  }

  isConsumerConnected(): boolean {
    return this.isConnected;
  }

  async onModuleDestroy(): Promise<void> {
    if (this.consumer && this.isConnected) {
      try {
        await this.consumer.disconnect();
        this.logger.log('Disconnected Kafka consumer.');
      } catch (err) {
        this.logger.error('Error disconnecting Kafka consumer', err);
      }
    }
  }
}
