import 'package:flutter/foundation.dart';
import 'package:logger/logger.dart';
import 'package:paraclete/core/config/env_config.dart';

/// App logger configuration
class AppLogger {
  static final Logger _logger = Logger(
    printer: PrettyPrinter(
      methodCount: 0,
      errorMethodCount: 5,
      lineLength: 120,
      colors: true,
      printEmojis: false,
      dateTimeFormat: DateTimeFormat.onlyTimeAndSinceStart,
    ),
    level: _getLogLevel(),
    filter: _ProductionFilter(),
  );

  static Level _getLogLevel() {
    if (!EnvConfig.enableLogging) {
      return Level.off;
    }

    switch (EnvConfig.environment) {
      case Environment.development:
        return Level.trace;
      case Environment.staging:
        return Level.debug;
      case Environment.production:
        return Level.warning;
    }
  }

  /// Log verbose message
  static void verbose(
    dynamic message, {
    DateTime? time,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _logger.t(
      message,
      time: time ?? DateTime.now(),
      error: error,
      stackTrace: stackTrace,
    );
  }

  /// Log debug message
  static void debug(
    dynamic message, {
    DateTime? time,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _logger.d(
      message,
      time: time ?? DateTime.now(),
      error: error,
      stackTrace: stackTrace,
    );
  }

  /// Log info message
  static void info(
    dynamic message, {
    DateTime? time,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _logger.i(
      message,
      time: time ?? DateTime.now(),
      error: error,
      stackTrace: stackTrace,
    );
  }

  /// Log warning message
  static void warning(
    dynamic message, {
    DateTime? time,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _logger.w(
      message,
      time: time ?? DateTime.now(),
      error: error,
      stackTrace: stackTrace,
    );
  }

  /// Log error message
  static void error(
    dynamic message, {
    DateTime? time,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _logger.e(
      message,
      time: time ?? DateTime.now(),
      error: error,
      stackTrace: stackTrace,
    );
  }

  /// Log fatal error message
  static void fatal(
    dynamic message, {
    DateTime? time,
    Object? error,
    StackTrace? stackTrace,
  }) {
    _logger.f(
      message,
      time: time ?? DateTime.now(),
      error: error,
      stackTrace: stackTrace,
    );
  }

  /// Log API request
  static void apiRequest({
    required String method,
    required String url,
    Map<String, dynamic>? headers,
    dynamic body,
    Map<String, dynamic>? queryParams,
  }) {
    if (!EnvConfig.enableLogging) return;

    final log = StringBuffer();
    log.writeln('API Request:');
    log.writeln('  Method: $method');
    log.writeln('  URL: $url');
    if (queryParams != null && queryParams.isNotEmpty) {
      log.writeln('  Query: $queryParams');
    }
    if (headers != null && headers.isNotEmpty) {
      log.writeln('  Headers: ${_filterSensitive(headers)}');
    }
    if (body != null) {
      log.writeln('  Body: ${_filterSensitive(body)}');
    }

    debug(log.toString());
  }

  /// Log API response
  static void apiResponse({
    required String method,
    required String url,
    required int statusCode,
    Map<String, dynamic>? headers,
    dynamic body,
    Duration? duration,
  }) {
    if (!EnvConfig.enableLogging) return;

    final log = StringBuffer();
    log.writeln('API Response:');
    log.writeln('  Method: $method');
    log.writeln('  URL: $url');
    log.writeln('  Status: $statusCode');
    if (duration != null) {
      log.writeln('  Duration: ${duration.inMilliseconds}ms');
    }
    if (headers != null && headers.isNotEmpty) {
      log.writeln('  Headers: $headers');
    }
    if (body != null) {
      log.writeln('  Body: ${_filterSensitive(body)}');
    }

    if (statusCode >= 200 && statusCode < 300) {
      debug(log.toString());
    } else if (statusCode >= 400 && statusCode < 500) {
      warning(log.toString());
    } else {
      error(log.toString());
    }
  }

  /// Log WebSocket event
  static void websocket({
    required String event,
    String? sessionId,
    dynamic data,
  }) {
    if (!EnvConfig.enableLogging) return;

    final log = StringBuffer();
    log.writeln('WebSocket Event:');
    log.writeln('  Event: $event');
    if (sessionId != null) {
      log.writeln('  Session: $sessionId');
    }
    if (data != null) {
      log.writeln('  Data: ${_filterSensitive(data)}');
    }

    debug(log.toString());
  }

  /// Log navigation event
  static void navigation({
    required String from,
    required String to,
    Map<String, dynamic>? params,
  }) {
    if (!EnvConfig.enableLogging) return;

    final log = StringBuffer();
    log.writeln('Navigation:');
    log.writeln('  From: $from');
    log.writeln('  To: $to');
    if (params != null && params.isNotEmpty) {
      log.writeln('  Params: $params');
    }

    debug(log.toString());
  }

  /// Log user action
  static void userAction({
    required String action,
    Map<String, dynamic>? details,
  }) {
    if (!EnvConfig.enableLogging) return;

    final log = StringBuffer();
    log.writeln('User Action:');
    log.writeln('  Action: $action');
    if (details != null && details.isNotEmpty) {
      log.writeln('  Details: $details');
    }

    info(log.toString());
  }

  /// Log performance metric
  static void performance({
    required String metric,
    required Duration duration,
    Map<String, dynamic>? details,
  }) {
    if (!EnvConfig.enableLogging) return;

    final log = StringBuffer();
    log.writeln('Performance:');
    log.writeln('  Metric: $metric');
    log.writeln('  Duration: ${duration.inMilliseconds}ms');
    if (details != null && details.isNotEmpty) {
      log.writeln('  Details: $details');
    }

    debug(log.toString());
  }

  /// Filter sensitive data from logs
  static dynamic _filterSensitive(dynamic data, {int depth = 0}) {
    if (data == null) return null;

    // Prevent stack overflow from deeply nested objects
    if (depth > 10) return '***MAX_DEPTH***';

    if (data is Map) {
      final filtered = <String, dynamic>{};
      data.forEach((key, value) {
        final keyStr = key.toString().toLowerCase();
        if (_isSensitiveKey(keyStr)) {
          filtered[key] = '***FILTERED***';
        } else if (value is Map || value is List) {
          filtered[key] = _filterSensitive(value, depth: depth + 1);
        } else {
          filtered[key] = value;
        }
      });
      return filtered;
    } else if (data is List) {
      return data.map((item) => _filterSensitive(item, depth: depth + 1)).toList();
    }

    return data;
  }

  static bool _isSensitiveKey(String key) {
    const sensitivePatterns = [
      'password',
      'token',
      'api_key',
      'apikey',
      'secret',
      'authorization',
      'auth',
      'credential',
      'private',
      'ssn',
      'pin',
      'bearer',
      'jwt',
      'session_id',
      'refresh',
      'access_token',
      'id_token',
      'access',
      'oauth',
      'key',
    ];

    return sensitivePatterns.any((pattern) => key.contains(pattern));
  }
}

/// Custom filter to disable logs in production
class _ProductionFilter extends LogFilter {
  @override
  bool shouldLog(LogEvent event) {
    if (kReleaseMode) {
      return event.level.index >= Level.warning.index;
    }
    return true;
  }
}