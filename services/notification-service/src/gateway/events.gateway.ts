import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  OnGatewayInit,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Logger } from '@nestjs/common';

@WebSocketGateway({
  cors: {
    origin: '*',
    credentials: true,
  },
  namespace: '/notifications',
})
export class EventsGateway
  implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect
{
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(EventsGateway.name);

  afterInit() {
    this.logger.log('EventsGateway initialized on namespace /notifications');
  }

  handleConnection(client: Socket) {
    // Extract trusted user ID header from Kong Gateway handshake
    const headers = client.handshake.headers;
    const auth = client.handshake.auth || {};

    const rawUserId =
      headers['x-user-id'] ||
      headers['X-User-ID'] ||
      auth['x-user-id'] ||
      auth['userId'];

    const userId = Array.isArray(rawUserId) ? rawUserId[0] : rawUserId;

    if (!userId || typeof userId !== 'string' || userId.trim() === '') {
      this.logger.warn(
        `[Unauthorized] Client ${client.id} rejected: missing 'X-User-ID' header`,
      );
      client.emit('error', {
        error: 'missing user identification header',
      });
      client.disconnect(true);
      return;
    }

    const cleanUserId = userId.trim();
    client.data.userId = cleanUserId;

    // Join user-specific room for targeted push notifications
    const userRoom = `user:${cleanUserId}`;
    void client.join(userRoom);

    this.logger.log(
      `[Connected] Client ${client.id} joined room '${userRoom}'`,
    );
  }

  handleDisconnect(client: Socket) {
    const userId = client.data?.userId;
    this.logger.log(
      `[Disconnected] Client ${client.id}${userId ? ` (user:${userId})` : ''}`,
    );
  }

  /**
   * Broadcast an event to all active socket connections belonging to a specific user.
   */
  sendToUser(userId: string, event: string, payload: any): boolean {
    if (!this.server) {
      this.logger.error('WebSocket server is not initialized yet.');
      return false;
    }

    const room = `user:${userId}`;
    this.server.to(room).emit(event, payload);
    this.logger.log(`Broadcasted '${event}' to room '${room}'`);
    return true;
  }

  @SubscribeMessage('ping')
  handlePing(): string {
    return 'pong';
  }
}
