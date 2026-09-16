import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { App } from 'supertest/types';
import { AppModule } from '../src/app.module';

describe('Notification Service (e2e)', () => {
  let app: INestApplication<App>;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    app.setGlobalPrefix('api/v1/notifications');
    await app.init();
  });

  it('/api/v1/notifications/health (GET) should return 200 UP', () => {
    return request(app.getHttpServer())
      .get('/api/v1/notifications/health')
      .expect(200)
      .expect((res) => {
        expect(res.body.success).toBe(true);
        expect(res.body.data.status).toBe('UP');
        expect(res.body.data.service).toBe('notification-service');
      });
  });

  afterAll(async () => {
    await app.close();
  });
});
