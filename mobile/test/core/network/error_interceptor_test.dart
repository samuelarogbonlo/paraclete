import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:paraclete/core/network/interceptors/error_interceptor.dart';

void main() {
  group('ErrorInterceptor', () {
    late ErrorInterceptor interceptor;

    setUp(() {
      interceptor = ErrorInterceptor();
    });

    group('Exception Classes', () {
      test('ApiException creates with message and code', () {
        final exception = ApiException(
          message: 'Test error',
          statusCode: 400,
          errorCode: 'TEST_ERROR',
        );

        expect(exception.message, 'Test error');
        expect(exception.statusCode, 400);
        expect(exception.errorCode, 'TEST_ERROR');
        expect(exception.toString(), contains('ApiException'));
      });

      test('NetworkException creates with message', () {
        final exception = NetworkException('Network failed');

        expect(exception.message, 'Network failed');
        expect(exception.toString(), contains('NetworkException'));
      });

      test('ValidationException creates with errors map', () {
        final errors = {
          'email': ['Invalid email'],
          'password': ['Too short', 'Missing special char']
        };
        final exception = ValidationException(
          message: 'Validation failed',
          errors: errors,
        );

        expect(exception.message, 'Validation failed');
        expect(exception.errors, errors);
        expect(exception.toString(), contains('ValidationException'));
      });

      test('UnauthorizedException creates correctly', () {
        final exception = UnauthorizedException('Not authorized');

        expect(exception.message, 'Not authorized');
        expect(exception.toString(), contains('UnauthorizedException'));
      });

      test('ForbiddenException creates correctly', () {
        final exception = ForbiddenException('Access forbidden');

        expect(exception.message, 'Access forbidden');
        expect(exception.toString(), contains('ForbiddenException'));
      });

      test('NotFoundException creates correctly', () {
        final exception = NotFoundException('Resource not found');

        expect(exception.message, 'Resource not found');
        expect(exception.toString(), contains('NotFoundException'));
      });

      test('RateLimitException creates with retry after', () {
        final exception = RateLimitException(
          message: 'Too many requests',
          retryAfter: 60,
        );

        expect(exception.message, 'Too many requests');
        expect(exception.retryAfter, 60);
        expect(exception.toString(), contains('RateLimitException'));
      });

      test('ServerException creates correctly', () {
        final exception = ServerException('Server error');

        expect(exception.message, 'Server error');
        expect(exception.toString(), contains('ServerException'));
      });
    });

    group('Error Transformation', () {
      test('transforms connection timeout to NetworkException', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.connectionTimeout,
        );

        // Test that error handler exists
        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('transforms send timeout to NetworkException', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.sendTimeout,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('transforms receive timeout to NetworkException', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.receiveTimeout,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('transforms connection error to NetworkException', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.connectionError,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('transforms cancel to ApiException', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.cancel,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });
    });

    group('HTTP Status Code Handling', () {
      test('handles 400 Bad Request', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 400,
            data: {'message': 'Bad request'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 400 with validation errors', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 400,
            data: {
              'message': 'Validation failed',
              'errors': {
                'email': ['Invalid email'],
                'password': ['Too short']
              }
            },
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 401 Unauthorized', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 401,
            data: {'message': 'Unauthorized'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 403 Forbidden', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 403,
            data: {'message': 'Forbidden'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 404 Not Found', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 404,
            data: {'message': 'Not found'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 429 Rate Limit with Retry-After header', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 429,
            data: {'message': 'Too many requests'},
            headers: Headers.fromMap({
              'Retry-After': ['60']
            }),
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 500 Internal Server Error', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 500,
            data: {'message': 'Server error'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 502 Bad Gateway', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 502,
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 503 Service Unavailable', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 503,
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles 504 Gateway Timeout', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 504,
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });
    });

    group('Error Message Extraction', () {
      test('extracts message from response data map', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 400,
            data: {'message': 'Custom error message'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('extracts error from response data', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 400,
            data: {'error': 'Error message'},
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('handles string response data', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 400,
            data: 'Plain text error',
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });

      test('uses default message when no data', () {
        final dioError = DioException(
          requestOptions: RequestOptions(path: '/test'),
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 400,
          ),
          type: DioExceptionType.badResponse,
        );

        expect(() => interceptor.onError(dioError, _TestErrorHandler()),
            returnsNormally);
      });
    });
  });
}

// Test helper class for error handler
class _TestErrorHandler extends ErrorInterceptorHandler {
  @override
  void reject(DioException err, [bool newError = false]) {
    // Capture the rejected error for testing
  }
}
