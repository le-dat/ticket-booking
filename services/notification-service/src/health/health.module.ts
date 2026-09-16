import { Module } from '@nestjs/common';
import { KafkaModule } from '../kafka/kafka.module';
import { HealthController } from './health.controller';

@Module({
  imports: [KafkaModule],
  controllers: [HealthController],
})
export class HealthModule {}
