export * from './events';
import path from 'path';

// Đường dẫn tuyệt đối tới file product.proto để các microservice có thể import sử dụng
export const PRODUCT_PROTO_PATH = path.join(__dirname, './proto/product.proto');
