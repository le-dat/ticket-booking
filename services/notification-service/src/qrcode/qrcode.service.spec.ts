import { Test, TestingModule } from '@nestjs/testing';
import { QrCodeService } from './qrcode.service';

describe('QrCodeService', () => {
  let service: QrCodeService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [QrCodeService],
    }).compile();

    service = module.get<QrCodeService>(QrCodeService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  it('should generate a valid Base64 PNG Data URL', async () => {
    const payload = {
      bookingId: 'test-booking-123',
      userId: 'test-user-456',
      txId: 'tx-789',
    };

    const result = await service.generateTicketQRCode(payload);

    expect(result).toBeDefined();
    expect(typeof result).toBe('string');
    expect(result.startsWith('data:image/png;base64,')).toBe(true);
  });

  it('should generate a valid PNG Buffer', async () => {
    const payload = {
      bookingId: 'test-booking-123',
      userId: 'test-user-456',
      txId: 'tx-789',
    };

    const buffer = await service.generateTicketQRCodeBuffer(payload);

    expect(buffer).toBeDefined();
    expect(Buffer.isBuffer(buffer)).toBe(true);
    expect(buffer.length).toBeGreaterThan(0);
  });
});
