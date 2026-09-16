import { Injectable, Logger } from '@nestjs/common';
import * as QRCode from 'qrcode';
import { TicketQRPayload } from './dto/ticket-qr-payload.dto';

@Injectable()
export class QrCodeService {
  private readonly logger = new Logger(QrCodeService.name);

  /**
   * Generates a Base64 Data URL (image/png) containing ticket verification data.
   */
  async generateTicketQRCode(payload: TicketQRPayload): Promise<string> {
    try {
      const dataToEncode = JSON.stringify({
        bookingId: payload.bookingId,
        userId: payload.userId,
        txId: payload.txId,
        timestamp: payload.timestamp || new Date().toISOString(),
      });

      const qrCodeDataUrl = await QRCode.toDataURL(dataToEncode, {
        errorCorrectionLevel: 'H',
        type: 'image/png',
        margin: 2,
        width: 320,
        color: {
          dark: '#000000',
          light: '#ffffff',
        },
      });

      return qrCodeDataUrl;
    } catch (error) {
      this.logger.error(
        `Failed to generate QR Code: ${error.message}`,
        error.stack,
      );
      throw error;
    }
  }

  /**
   * Generates a raw PNG Buffer for email attachment or file storage.
   */
  async generateTicketQRCodeBuffer(payload: TicketQRPayload): Promise<Buffer> {
    try {
      const dataToEncode = JSON.stringify({
        bookingId: payload.bookingId,
        userId: payload.userId,
        txId: payload.txId,
        timestamp: payload.timestamp || new Date().toISOString(),
      });

      return await QRCode.toBuffer(dataToEncode, {
        errorCorrectionLevel: 'H',
        type: 'png',
        margin: 2,
        width: 320,
      });
    } catch (error) {
      this.logger.error(
        `Failed to generate QR Code Buffer: ${error.message}`,
        error.stack,
      );
      throw error;
    }
  }
}
