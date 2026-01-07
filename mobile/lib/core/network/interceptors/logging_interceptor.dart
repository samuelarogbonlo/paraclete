import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

/// Interceptor for logging HTTP requests and responses
class LoggingInterceptor extends Interceptor {
  final Logger _logger = Logger(
    printer: PrettyPrinter(
      methodCount: 0,
      errorMethodCount: 8,
      lineLength: 120,
      colors: true,
      printEmojis: false,
      dateTimeFormat: DateTimeFormat.onlyTimeAndSinceStart,
    ),
  );

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final requestLog = StringBuffer();
    requestLog.writeln('═══ REQUEST ═══');
    requestLog.writeln('${options.method} ${options.uri}');
    requestLog.writeln('Headers:');

    // Filter sensitive headers
    final headers = Map<String, dynamic>.from(options.headers);
    if (headers.containsKey('Authorization')) {
      final auth = headers['Authorization'] as String;
      headers['Authorization'] = _maskToken(auth);
    }
    headers.forEach((key, value) {
      requestLog.writeln('  $key: $value');
    });

    if (options.data != null) {
      requestLog.writeln('Data:');
      requestLog.writeln(_formatJson(options.data));
    }

    if (options.queryParameters.isNotEmpty) {
      requestLog.writeln('Query Parameters:');
      options.queryParameters.forEach((key, value) {
        requestLog.writeln('  $key: $value');
      });
    }

    _logger.d(requestLog.toString());
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    final responseLog = StringBuffer();
    responseLog.writeln('═══ RESPONSE ═══');
    responseLog.writeln(
      '${response.requestOptions.method} ${response.requestOptions.uri}',
    );
    responseLog.writeln('Status: ${response.statusCode}');
    responseLog.writeln('Headers:');
    response.headers.forEach((key, values) {
      responseLog.writeln('  $key: ${values.join(', ')}');
    });

    if (response.data != null) {
      responseLog.writeln('Data:');
      responseLog.writeln(_formatJson(response.data));
    }

    final duration = _calculateDuration(response.requestOptions);
    responseLog.writeln('Duration: ${duration}ms');

    _logger.d(responseLog.toString());
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final errorLog = StringBuffer();
    errorLog.writeln('═══ ERROR ═══');
    errorLog.writeln(
      '${err.requestOptions.method} ${err.requestOptions.uri}',
    );
    errorLog.writeln('Type: ${err.type}');
    errorLog.writeln('Message: ${err.message}');

    if (err.response != null) {
      errorLog.writeln('Status: ${err.response?.statusCode}');
      errorLog.writeln('Response Data:');
      errorLog.writeln(_formatJson(err.response?.data));
    }

    final duration = _calculateDuration(err.requestOptions);
    errorLog.writeln('Duration: ${duration}ms');

    _logger.e(errorLog.toString());
    handler.next(err);
  }

  String _formatJson(dynamic data) {
    if (data == null) return 'null';

    try {
      if (data is String) {
        // Try to parse as JSON
        try {
          final parsed = jsonDecode(data);
          return const JsonEncoder.withIndent('  ').convert(parsed);
        } catch (_) {
          // Not JSON, return as is (truncate if too long)
          return data.length > 1000 ? '${data.substring(0, 1000)}...' : data;
        }
      } else if (data is List || data is Map) {
        // Filter sensitive data
        final filtered = _filterSensitiveData(data);
        return const JsonEncoder.withIndent('  ').convert(filtered);
      } else {
        return data.toString();
      }
    } catch (e) {
      return 'Error formatting data: $e';
    }
  }

  dynamic _filterSensitiveData(dynamic data) {
    if (data is Map) {
      final filtered = <String, dynamic>{};
      data.forEach((key, value) {
        if (_isSensitiveKey(key.toString())) {
          filtered[key] = _maskValue(value);
        } else if (value is Map || value is List) {
          filtered[key] = _filterSensitiveData(value);
        } else {
          filtered[key] = value;
        }
      });
      return filtered;
    } else if (data is List) {
      return data.map((item) {
        if (item is Map || item is List) {
          return _filterSensitiveData(item);
        }
        return item;
      }).toList();
    }
    return data;
  }

  bool _isSensitiveKey(String key) {
    final sensitiveKeys = [
      'password',
      'token',
      'api_key',
      'secret',
      'authorization',
      'bearer',
      'credit_card',
      'ssn',
      'pin',
    ];
    final lowerKey = key.toLowerCase();
    return sensitiveKeys.any((sensitive) => lowerKey.contains(sensitive));
  }

  String _maskValue(dynamic value) {
    if (value == null) return 'null';
    final str = value.toString();
    if (str.length <= 8) return '****';
    return '${str.substring(0, 4)}...${str.substring(str.length - 4)}';
  }

  String _maskToken(String token) {
    if (token.length <= 20) return '****';
    return '${token.substring(0, 10)}...${token.substring(token.length - 10)}';
  }

  int _calculateDuration(RequestOptions options) {
    final extra = options.extra;
    if (extra.containsKey('start_time')) {
      final startTime = extra['start_time'] as DateTime;
      return DateTime.now().difference(startTime).inMilliseconds;
    }
    return 0;
  }
}