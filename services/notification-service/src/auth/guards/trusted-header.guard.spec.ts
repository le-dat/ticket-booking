import { ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { TrustedHeaderGuard } from './trusted-header.guard';

describe('TrustedHeaderGuard', () => {
  let guard: TrustedHeaderGuard;

  beforeEach(() => {
    guard = new TrustedHeaderGuard();
  });

  it('should allow request with valid X-User-ID header', () => {
    const mockRequest: any = {
      headers: {
        'x-user-id': 'usr-12345',
      },
    };

    const mockContext = {
      switchToHttp: () => ({
        getRequest: () => mockRequest,
      }),
    } as ExecutionContext;

    const result = guard.canActivate(mockContext);
    expect(result).toBe(true);
    expect(mockRequest.user).toEqual({ id: 'usr-12345' });
  });

  it('should throw UnauthorizedException when X-User-ID is missing', () => {
    const mockRequest: any = {
      headers: {},
    };

    const mockContext = {
      switchToHttp: () => ({
        getRequest: () => mockRequest,
      }),
    } as ExecutionContext;

    expect(() => guard.canActivate(mockContext)).toThrow(UnauthorizedException);
    expect(() => guard.canActivate(mockContext)).toThrow(
      'missing user identification header',
    );
  });

  it('should throw UnauthorizedException when X-User-ID is empty string', () => {
    const mockRequest: any = {
      headers: {
        'x-user-id': '   ',
      },
    };

    const mockContext = {
      switchToHttp: () => ({
        getRequest: () => mockRequest,
      }),
    } as ExecutionContext;

    expect(() => guard.canActivate(mockContext)).toThrow(UnauthorizedException);
  });
});
