import { Module } from '@nestjs/common';
import { EventsModule } from '../gateway/events.module';
import { QrCodeModule } from '../qrcode/qrcode.module';
import { KafkaConsumerService } from './kafka-consumer.service';

@Module({
  imports: [EventsModule, QrCodeModule],
  providers: [KafkaConsumerService],
  exports: [KafkaConsumerService],
})
export class KafkaModule {}
