import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Request } from 'express';

@Injectable()
export class TrustedHeaderGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const rawUserId = request.headers['x-user-id'];
    const userId = Array.isArray(rawUserId) ? rawUserId[0] : rawUserId;

    if (!userId || typeof userId !== 'string' || userId.trim() === '') {
      throw new UnauthorizedException('missing user identification header');
    }

    request['user'] = { id: userId.trim() };
    return true;
  }
}
