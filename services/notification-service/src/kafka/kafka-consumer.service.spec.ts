import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { KafkaConsumerService } from './kafka-consumer.service';
import { EventsGateway } from '../gateway/events.gateway';
import { QrCodeService } from '../qrcode/qrcode.service';

describe('KafkaConsumerService', () => {
  let service: KafkaConsumerService;
  let eventsGateway: jest.Mocked<EventsGateway>;
  let qrCodeService: jest.Mocked<QrCodeService>;

  beforeEach(async () => {
    const mockEventsGateway = {
      sendToUser: jest.fn().mockReturnValue(true),
    };

    const mockQrCodeService = {
      generateTicketQRCode: jest
        .fn()
        .mockResolvedValue('data:image/png;base64,mockQRCodeData'),
    };

    const mockConfigService = {
      get: jest.fn((key: string, defaultValue?: any) => {
        const config: Record<string, any> = {
          'kafka.brokers': ['localhost:9092'],
          'kafka.clientId': 'test-client',
          'kafka.groupId': 'test-group',
          'kafka.paymentEventsTopic': 'payment-events',
        };
        return config[key] ?? defaultValue;
      }),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        KafkaConsumerService,
        { provide: ConfigService, useValue: mockConfigService },
        { provide: EventsGateway, useValue: mockEventsGateway },
        { provide: QrCodeService, useValue: mockQrCodeService },
      ],
    }).compile();

    service = module.get<KafkaConsumerService>(KafkaConsumerService);
    eventsGateway = module.get(EventsGateway);
    qrCodeService = module.get(QrCodeService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  it('should handle PaymentProcessed SUCCESS event and emit to user', async () => {
    const event = {
      event_type: 'PaymentProcessed',
      booking_id: 'booking-111',
      user_id: 'user-222',
      amount: 250000,
      status: 'SUCCESS',
      gateway_transaction_id: 'tx-333',
    };

    await service.handlePaymentProcessed(event);

    expect(qrCodeService.generateTicketQRCode).toHaveBeenCalledWith({
      bookingId: 'booking-111',
      userId: 'user-222',
      txId: 'tx-333',
    });

    expect(eventsGateway.sendToUser).toHaveBeenCalledWith(
      'user-222',
      'BookingConfirmed',
      expect.objectContaining({
        bookingId: 'booking-111',
        amount: 250000,
        status: 'CONFIRMED',
        qrCode: 'data:image/png;base64,mockQRCodeData',
      }),
    );
  });

  it('should ignore non-SUCCESS or unrecognized event in processMessage', async () => {
    const rawMessage = {
      value: Buffer.from(
        JSON.stringify({
          event_type: 'PaymentProcessed',
          booking_id: 'booking-111',
          user_id: 'user-222',
          amount: 250000,
          status: 'FAILED',
          gateway_transaction_id: 'tx-333',
        }),
      ),
    };

    await service.processMessage('payment-events', 0, rawMessage);

    expect(eventsGateway.sendToUser).not.toHaveBeenCalled();
    expect(qrCodeService.generateTicketQRCode).not.toHaveBeenCalled();
  });
});
