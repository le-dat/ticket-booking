import { Controller, Get, HttpCode, HttpStatus } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Redis from 'ioredis';
import { ApiResponse } from '../common/dto/api-response.dto';
import { KafkaConsumerService } from '../kafka/kafka-consumer.service';

@Controller('health')
export class HealthController {
  constructor(
    private readonly configService: ConfigService,
    private readonly kafkaConsumerService: KafkaConsumerService,
  ) {}

  @Get()
  @HttpCode(HttpStatus.OK)
  liveness(): ApiResponse<{ status: string; uptime: number; service: string }> {
    return ApiResponse.success({
      status: 'UP',
      uptime: process.uptime(),
      service: 'notification-service',
    });
  }

  @Get('ready')
  @HttpCode(HttpStatus.OK)
  async readiness(): Promise<ApiResponse<any>> {
    const redisUrl = this.configService.get<string>(
      'redis.url',
      'redis://localhost:6379',
    );
    let redisStatus = 'DOWN';

    try {
      const redis = new Redis(redisUrl, {
        maxRetriesPerRequest: 0,
        enableOfflineQueue: false,
        retryStrategy: () => null,
        connectTimeout: 1000,
        lazyConnect: true,
      });
      await redis.connect();
      const ping = await redis.ping();
      redisStatus = ping === 'PONG' ? 'UP' : 'DOWN';
      redis.disconnect();
    } catch {
      redisStatus = 'DOWN';
    }

    const kafkaStatus = this.kafkaConsumerService.isConsumerConnected()
      ? 'UP'
      : 'INITIALIZING_OR_DOWN';

    const isReady = redisStatus === 'UP';

    return new ApiResponse({
      success: isReady,
      message: isReady ? 'Service is healthy' : 'Some dependencies are down',
      data: {
        status: isReady ? 'UP' : 'DEGRADED',
        checks: {
          redis: redisStatus,
          kafka: kafkaStatus,
        },
      },
    });
  }
}
