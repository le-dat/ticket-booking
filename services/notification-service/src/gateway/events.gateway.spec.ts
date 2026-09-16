import { EventsGateway } from './events.gateway';

describe('EventsGateway', () => {
  let gateway: EventsGateway;
  let mockServer: any;

  beforeEach(() => {
    gateway = new EventsGateway();
    mockServer = {
      to: jest.fn().mockReturnThis(),
      emit: jest.fn(),
    };
    gateway.server = mockServer;
  });

  it('should be defined', () => {
    expect(gateway).toBeDefined();
  });

  it('should accept connection with valid X-User-ID header and join user room', () => {
    const mockSocket: any = {
      id: 'socket-1',
      handshake: {
        headers: {
          'x-user-id': 'usr-abc',
        },
        auth: {},
      },
      data: {},
      join: jest.fn(),
      emit: jest.fn(),
      disconnect: jest.fn(),
    };

    gateway.handleConnection(mockSocket);

    expect(mockSocket.data.userId).toBe('usr-abc');
    expect(mockSocket.join).toHaveBeenCalledWith('user:usr-abc');
    expect(mockSocket.disconnect).not.toHaveBeenCalled();
  });

  it('should reject connection when X-User-ID header is missing', () => {
    const mockSocket: any = {
      id: 'socket-2',
      handshake: {
        headers: {},
        auth: {},
      },
      data: {},
      join: jest.fn(),
      emit: jest.fn(),
      disconnect: jest.fn(),
    };

    gateway.handleConnection(mockSocket);

    expect(mockSocket.emit).toHaveBeenCalledWith('error', {
      error: 'missing user identification header',
    });
    expect(mockSocket.disconnect).toHaveBeenCalledWith(true);
    expect(mockSocket.join).not.toHaveBeenCalled();
  });

  it('should sendToUser to the correct user room', () => {
    const result = gateway.sendToUser('usr-999', 'BookingConfirmed', {
      status: 'CONFIRMED',
    });

    expect(result).toBe(true);
    expect(mockServer.to).toHaveBeenCalledWith('user:usr-999');
    expect(mockServer.emit).toHaveBeenCalledWith('BookingConfirmed', {
      status: 'CONFIRMED',
    });
  });

  it('should return pong on ping', () => {
    expect(gateway.handlePing()).toBe('pong');
  });
});
