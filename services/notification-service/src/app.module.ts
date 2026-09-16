import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import configuration from './config/configuration';
import { validationSchema } from './config/validation.schema';
import { EventsModule } from './gateway/events.module';
import { HealthModule } from './health/health.module';
import { KafkaModule } from './kafka/kafka.module';
import { QrCodeModule } from './qrcode/qrcode.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [configuration],
      validationSchema,
    }),
    EventsModule,
    QrCodeModule,
    KafkaModule,
    HealthModule,
  ],
})
export class AppModule {}
