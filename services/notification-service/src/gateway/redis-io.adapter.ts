import { IoAdapter } from '@nestjs/platform-socket.io';
import { ServerOptions } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import Redis from 'ioredis';
import { Logger } from '@nestjs/common';

export class RedisIoAdapter extends IoAdapter {
  private adapterConstructor: ReturnType<typeof createAdapter> | null = null;
  private readonly logger = new Logger(RedisIoAdapter.name);

  constructor(
    app: any,
    private readonly redisUrl: string,
  ) {
    super(app);
  }

  async connectToRedis(): Promise<void> {
    try {
      const pubClient = new Redis(this.redisUrl, {
        lazyConnect: true,
        maxRetriesPerRequest: 3,
      });
      const subClient = pubClient.duplicate();

      await Promise.all([pubClient.connect(), subClient.connect()]);

      this.adapterConstructor = createAdapter(pubClient, subClient);
      this.logger.log('Connected to Redis for Socket.IO Adapter');
    } catch (error) {
      this.logger.error(
        `Failed to connect to Redis for Socket.IO adapter: ${error.message}. Falling back to default in-memory adapter.`,
      );
      this.adapterConstructor = null;
    }
  }

  createIOServer(port: number, options?: ServerOptions): any {
    const server = super.createIOServer(port, options);
    if (this.adapterConstructor) {
      server.adapter(this.adapterConstructor);
      this.logger.log('Applied Redis Adapter to Socket.IO Server');
    }
    return server;
  }
}
