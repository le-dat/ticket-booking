import { Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { RedisIoAdapter } from './gateway/redis-io.adapter';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule);

  const configService = app.get(ConfigService);
  const port = configService.get<number>('port', 3005);
  const corsOrigins = configService.get<string[]>('cors.origins', [
    'http://localhost:3000',
    'http://localhost:8000',
  ]);
  const redisUrl = configService.get<string>(
    'redis.url',
    'redis://localhost:6379',
  );

  // Set Global Route Prefix matching Kong Gateway route (/api/v1/notifications)
  app.setGlobalPrefix('api/v1/notifications');

  // Enable CORS
  app.enableCors({
    origin: corsOrigins,
    credentials: true,
  });

  // Enable Graceful Shutdown
  app.enableShutdownHooks();

  // Socket.IO Redis Adapter for multi-instance scaling
  const redisIoAdapter = new RedisIoAdapter(app, redisUrl);
  await redisIoAdapter.connectToRedis();
  app.useWebSocketAdapter(redisIoAdapter);

  await app.listen(port);
  logger.log(`Notification Service running on http://localhost:${port}`);
  logger.log(
    `WebSocket Gateway active on ws://localhost:${port}/notifications`,
  );
  logger.log(
    `Health Check Probe available at http://localhost:${port}/api/v1/notifications/health`,
  );
}

void bootstrap();
