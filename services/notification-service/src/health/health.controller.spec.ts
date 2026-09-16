import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { HealthController } from './health.controller';
import { KafkaConsumerService } from '../kafka/kafka-consumer.service';

jest.mock('ioredis', () => {
  return jest.fn().mockImplementation(() => {
    return {
      connect: jest.fn().mockResolvedValue(undefined),
      ping: jest.fn().mockResolvedValue('PONG'),
      disconnect: jest.fn(),
      quit: jest.fn().mockResolvedValue('OK'),
    };
  });
});

describe('HealthController', () => {
  let controller: HealthController;
  let kafkaConsumerService: jest.Mocked<KafkaConsumerService>;

  beforeEach(async () => {
    const mockKafkaConsumerService = {
      isConsumerConnected: jest.fn().mockReturnValue(true),
    };

    const mockConfigService = {
      get: jest.fn((key: string, defaultValue?: any) => {
        if (key === 'redis.url') return 'redis://localhost:6379';
        return defaultValue;
      }),
    };

    const module: TestingModule = await Test.createTestingModule({
      controllers: [HealthController],
      providers: [
        { provide: KafkaConsumerService, useValue: mockKafkaConsumerService },
        { provide: ConfigService, useValue: mockConfigService },
      ],
    }).compile();

    controller = module.get<HealthController>(HealthController);
    kafkaConsumerService = module.get(KafkaConsumerService);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
    expect(kafkaConsumerService).toBeDefined();
  });

  it('should return UP status on liveness probe', () => {
    const response = controller.liveness();
    expect(response.success).toBe(true);
    expect(response.data.status).toBe('UP');
    expect(response.data.service).toBe('notification-service');
  });

  it('should report readiness status based on dependencies', async () => {
    const response = await controller.readiness();
    expect(response).toBeDefined();
    expect(response.data.checks.redis).toBe('UP');
    expect(response.data.checks.kafka).toBe('UP');
  });
});
