import { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'crypto';

// Mở rộng kiểu Request của Express để lưu thêm correlationId
export interface RequestWithCorrelation extends Request {
  correlationId?: string; // Dấu ? vì lúc bắt đầu request có thể chưa gán
}

// LÝ DO: Regex kiểm tra chuỗi ID an toàn (chỉ cho phép chữ cái, chữ số, dấu gạch ngang, gạch dưới, độ dài từ 1 đến 128 ký tự)
const SAFE_CORRELATION_ID_REGEX = /^[a-zA-Z0-9\-_]{1,128}$/;

export const correlationIdMiddleware = (req: RequestWithCorrelation, res: Response, next: NextFunction) => {
  const rawHeader = req.headers['x-request-id'];

  // LÝ DO: Nếu header là một mảng (do gửi trùng header), lấy phần tử đầu tiên
  const candidateId = Array.isArray(rawHeader) ? rawHeader[0] : rawHeader;

  // LÝ DO: Lọc bỏ ký tự độc hại (CRLF, injection, XSS). Nếu candidateId rỗng hoặc không đúng định dạng an toàn, tự sinh UUIDv4 mới
  const correlationId =
    candidateId && SAFE_CORRELATION_ID_REGEX.test(candidateId.trim())
      ? candidateId.trim()
      : randomUUID();

  req.correlationId = correlationId; // LÝ DO: Đính kèm vào req object để Controller/Logger dùng lại
  res.setHeader('X-Request-ID', correlationId); // LÝ DO: Trả lại Header cho Client để tra cứu khi gặp sự cố

  next(); // Chuyển sang middleware/controller tiếp theo
};