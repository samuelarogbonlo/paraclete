import 'package:dio/dio.dart';

/// Custom exception classes for API errors
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? errorCode;
  final Map<String, dynamic>? details;

  ApiException({
    required this.message,
    this.statusCode,
    this.errorCode,
    this.details,
  });

  @override
  String toString() => 'ApiException: $message (code: $statusCode)';
}

class NetworkException implements Exception {
  final String message;

  NetworkException(this.message);

  @override
  String toString() => 'NetworkException: $message';
}

class ValidationException implements Exception {
  final String message;
  final Map<String, List<String>>? errors;

  ValidationException({required this.message, this.errors});

  @override
  String toString() => 'ValidationException: $message';
}

class UnauthorizedException implements Exception {
  final String message;

  UnauthorizedException(this.message);

  @override
  String toString() => 'UnauthorizedException: $message';
}

class ForbiddenException implements Exception {
  final String message;

  ForbiddenException(this.message);

  @override
  String toString() => 'ForbiddenException: $message';
}

class NotFoundException implements Exception {
  final String message;

  NotFoundException(this.message);

  @override
  String toString() => 'NotFoundException: $message';
}

class RateLimitException implements Exception {
  final String message;
  final int? retryAfter;

  RateLimitException({required this.message, this.retryAfter});

  @override
  String toString() => 'RateLimitException: $message';
}

class ServerException implements Exception {
  final String message;

  ServerException(this.message);

  @override
  String toString() => 'ServerException: $message';
}

/// Interceptor to handle and transform errors
class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    Exception transformedException;

    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        transformedException = NetworkException(
          'Connection timeout. Please check your internet connection.',
        );
        break;

      case DioExceptionType.connectionError:
        transformedException = NetworkException(
          'Unable to connect to the server. Please check your internet connection.',
        );
        break;

      case DioExceptionType.cancel:
        transformedException = ApiException(
          message: 'Request was cancelled',
        );
        break;

      case DioExceptionType.badResponse:
        transformedException = _handleResponseError(err);
        break;

      default:
        transformedException = NetworkException(
          'An unexpected error occurred. Please try again.',
        );
    }

    handler.reject(
      DioException(
        requestOptions: err.requestOptions,
        response: err.response,
        type: err.type,
        error: transformedException,
      ),
    );
  }

  Exception _handleResponseError(DioException err) {
    final statusCode = err.response?.statusCode;
    final data = err.response?.data;

    String message = 'An error occurred';
    String? errorCode;
    Map<String, dynamic>? details;

    // Try to extract error message from response
    if (data != null) {
      if (data is Map<String, dynamic>) {
        message = data['message'] ?? data['error'] ?? message;
        errorCode = data['error_code'] ?? data['code'];
        details = data['details'] as Map<String, dynamic>?;
      } else if (data is String) {
        message = data;
      }
    }

    switch (statusCode) {
      case 400:
        // Check if it's a validation error
        if (data is Map<String, dynamic> && data.containsKey('errors')) {
          final errors = data['errors'] as Map<String, dynamic>?;
          final validationErrors = <String, List<String>>{};

          errors?.forEach((key, value) {
            if (value is List) {
              validationErrors[key] = value.cast<String>();
            } else if (value is String) {
              validationErrors[key] = [value];
            }
          });

          return ValidationException(
            message: message,
            errors: validationErrors,
          );
        }
        return ApiException(
          message: message,
          statusCode: statusCode,
          errorCode: errorCode,
          details: details,
        );

      case 401:
        return UnauthorizedException(message);

      case 403:
        return ForbiddenException(message);

      case 404:
        return NotFoundException(message);

      case 429:
        final retryAfter = err.response?.headers.value('Retry-After');
        return RateLimitException(
          message: message,
          retryAfter: retryAfter != null ? int.tryParse(retryAfter) : null,
        );

      case 500:
      case 502:
      case 503:
      case 504:
        return ServerException(
          'Server error. Please try again later.',
        );

      default:
        return ApiException(
          message: message,
          statusCode: statusCode,
          errorCode: errorCode,
          details: details,
        );
    }
  }
}