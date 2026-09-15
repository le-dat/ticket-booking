import pino from 'pino';

// LÝ DO: Pino là logger có hiệu năng nén JSON cao nhất trong Node.js, hỗ trợ pretty print ở môi trường dev
export const createLogger = (serviceName: string) => {
  return pino({
    name: serviceName,
    level: process.env.LOG_LEVEL || 'info',
    // LÝ DO: Khử/mã hóa các trường nhạy cảm trong log để tránh rò rỉ credential/JWT/Password vào log system
    redact: [
      'req.headers.authorization',
      'req.headers.cookie',
      '*.password',
      '*.secret',
      '*.token',
      '*.refreshToken',
      '*.creditCard',
    ],
    transport:
      process.env.NODE_ENV === 'production'
        ? undefined  
        : {
            target: 'pino-pretty',
            options: {
              colorize: true,
              translateTime: 'SYS:standard',
            },
          },
  });
};

