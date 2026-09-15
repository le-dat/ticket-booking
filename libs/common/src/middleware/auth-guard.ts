import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

// Interface mở rộng chứa thông tin User sau khi giải mã JWT thành công
export interface AuthenticatedRequest extends Request {
  user?: {
    userId: string;
    email: string;
    role: string;
  };
}

export const createAuthGuard = (jwtSecret: string) => {
  if (!jwtSecret) {
    throw new Error('createAuthGuard requires a valid jwtSecret');
  }

  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    const authHeader = req.headers.authorization;
    
    // LÝ DO: Kiểm tra đúng định dạng 'Bearer <token>' trong Header Authorization
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Unauthorized: Missing or invalid token format' });
    }

    const token = authHeader.split(' ')[1]; // Tách lấy chuỗi JWT token đằng sau chữ 'Bearer '
    
    try {
      // LÝ DO: Verify JWT bằng Secret key trực tiếp tại Local service (không tốn HTTP request sang Auth Service)
      const decoded = jwt.verify(token, jwtSecret);

      // LÝ DO: Runtime Validation cho decoded payload - đảm bảo object hợp lệ và đủ thông tin bắt buộc
      if (
        typeof decoded !== 'object' ||
        !decoded ||
        typeof (decoded as any).userId !== 'string' ||
        typeof (decoded as any).email !== 'string' ||
        typeof (decoded as any).role !== 'string'
      ) {
        return res.status(401).json({ error: 'Unauthorized: Invalid token payload structure' });
      }

      req.user = {
        userId: (decoded as any).userId,
        email: (decoded as any).email,
        role: (decoded as any).role,
      }; // Gán user info vào req object

      next(); // Cho phép truy cập controller bảo mật
    } catch (err) {
      // LÝ DO: Nếu token hết hạn (Expired) hoặc chữ ký sai, lập tức trả về 401 Unauthorized
      return res.status(401).json({ error: 'Unauthorized: Invalid or expired token' });
    }
  };
};