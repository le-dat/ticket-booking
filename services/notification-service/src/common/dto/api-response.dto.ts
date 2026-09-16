export class ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: any;
  timestamp: string;

  constructor(partial: Partial<ApiResponse<T>>) {
    Object.assign(this, partial);
    this.timestamp = this.timestamp || new Date().toISOString();
  }

  static success<T>(data?: T, message = 'Success'): ApiResponse<T> {
    return new ApiResponse({
      success: true,
      message,
      data,
      timestamp: new Date().toISOString(),
    });
  }

  static error(error: any, message = 'Error'): ApiResponse<null> {
    return new ApiResponse({
      success: false,
      message,
      error,
      timestamp: new Date().toISOString(),
    });
  }
}
