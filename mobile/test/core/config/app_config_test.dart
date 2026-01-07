import 'package:flutter_test/flutter_test.dart';
import 'package:paraclete/core/config/app_config.dart';

void main() {
  group('AppConfig', () {
    group('App Info', () {
      test('has correct app name', () {
        expect(AppConfig.appName, 'Paraclete');
      });

      test('has valid version format', () {
        expect(AppConfig.appVersion, matches(RegExp(r'\d+\.\d+\.\d+')));
      });

      test('has valid build number', () {
        expect(AppConfig.appBuildNumber, isNotEmpty);
        expect(int.tryParse(AppConfig.appBuildNumber), isNotNull);
      });
    });

    group('API Timeouts', () {
      test('connect timeout is reasonable', () {
        expect(AppConfig.connectTimeout.inSeconds, greaterThan(0));
        expect(AppConfig.connectTimeout.inSeconds, lessThan(120));
      });

      test('receive timeout is reasonable', () {
        expect(AppConfig.receiveTimeout.inSeconds, greaterThan(0));
        expect(AppConfig.receiveTimeout.inSeconds, lessThan(120));
      });

      test('send timeout is reasonable', () {
        expect(AppConfig.sendTimeout.inSeconds, greaterThan(0));
        expect(AppConfig.sendTimeout.inSeconds, lessThan(120));
      });

      test('all timeouts are consistent', () {
        // Timeouts should be similar
        expect(AppConfig.connectTimeout, equals(Duration(seconds: 30)));
        expect(AppConfig.receiveTimeout, equals(Duration(seconds: 30)));
        expect(AppConfig.sendTimeout, equals(Duration(seconds: 30)));
      });
    });

    group('WebSocket Config', () {
      test('reconnect delay is reasonable', () {
        expect(AppConfig.wsReconnectDelay.inSeconds, greaterThan(0));
        expect(AppConfig.wsReconnectDelay.inSeconds, lessThan(10));
      });

      test('ping interval is reasonable', () {
        expect(AppConfig.wsPingInterval.inSeconds, greaterThanOrEqualTo(30));
        expect(AppConfig.wsPingInterval.inSeconds, lessThan(120));
      });

      test('max reconnect attempts is positive', () {
        expect(AppConfig.wsMaxReconnectAttempts, greaterThan(0));
        expect(AppConfig.wsMaxReconnectAttempts, lessThanOrEqualTo(10));
      });

      test('websocket config is production-ready', () {
        expect(AppConfig.wsReconnectDelay, equals(Duration(seconds: 1)));
        expect(AppConfig.wsPingInterval, equals(Duration(seconds: 30)));
        expect(AppConfig.wsMaxReconnectAttempts, equals(5));
      });
    });

    group('Voice Config', () {
      test('recording max duration is reasonable', () {
        expect(AppConfig.voiceRecordingMaxDuration.inMinutes, greaterThan(0));
        expect(AppConfig.voiceRecordingMaxDuration.inMinutes, lessThan(30));
      });

      test('sample rate matches Deepgram requirements', () {
        expect(AppConfig.voiceSampleRate, equals(16000));
      });

      test('debounce delay is reasonable', () {
        expect(AppConfig.voiceDebounceDelay.inMilliseconds, greaterThan(0));
        expect(AppConfig.voiceDebounceDelay.inMilliseconds, lessThan(1000));
      });
    });

    group('Terminal Config', () {
      test('terminal columns is standard', () {
        expect(AppConfig.terminalColumns, greaterThanOrEqualTo(80));
        expect(AppConfig.terminalColumns, lessThanOrEqualTo(200));
      });

      test('terminal rows is standard', () {
        expect(AppConfig.terminalRows, greaterThanOrEqualTo(24));
        expect(AppConfig.terminalRows, lessThanOrEqualTo(100));
      });

      test('scrollback lines is reasonable', () {
        expect(AppConfig.terminalScrollbackLines, greaterThan(0));
        expect(AppConfig.terminalScrollbackLines, lessThanOrEqualTo(10000));
      });
    });

    group('Session Config', () {
      test('session timeout is reasonable', () {
        expect(AppConfig.sessionTimeout.inHours, greaterThan(0));
        expect(AppConfig.sessionTimeout.inHours, lessThanOrEqualTo(24));
      });

      test('refresh interval is less than timeout', () {
        expect(
          AppConfig.sessionRefreshInterval,
          lessThan(AppConfig.sessionTimeout),
        );
      });
    });

    group('Cache Config', () {
      test('cache expiration is reasonable', () {
        expect(AppConfig.cacheExpiration.inHours, greaterThan(0));
        expect(AppConfig.cacheExpiration.inHours, lessThanOrEqualTo(72));
      });

      test('max cache size is positive', () {
        expect(AppConfig.maxCacheSize, greaterThan(0));
        expect(AppConfig.maxCacheSize, lessThanOrEqualTo(500 * 1024 * 1024));
      });

      test('max cache size is in bytes', () {
        // 100 MB = 100 * 1024 * 1024 bytes
        expect(AppConfig.maxCacheSize, equals(100 * 1024 * 1024));
      });
    });

    group('Feature Flags', () {
      test('voice input is enabled', () {
        expect(AppConfig.enableVoiceInput, isTrue);
      });

      test('terminal is enabled', () {
        expect(AppConfig.enableTerminal, isTrue);
      });

      test('multi-agent is enabled', () {
        expect(AppConfig.enableMultiAgent, isTrue);
      });

      test('session sync is enabled', () {
        expect(AppConfig.enableSessionSync, isTrue);
      });

      test('offline mode is disabled by default', () {
        expect(AppConfig.enableOfflineMode, isFalse);
      });
    });

    group('Pagination', () {
      test('default page size is reasonable', () {
        expect(AppConfig.defaultPageSize, greaterThan(0));
        expect(AppConfig.defaultPageSize, lessThanOrEqualTo(100));
      });

      test('max page size is greater than default', () {
        expect(AppConfig.maxPageSize, greaterThan(AppConfig.defaultPageSize));
      });

      test('pagination values are production-ready', () {
        expect(AppConfig.defaultPageSize, equals(20));
        expect(AppConfig.maxPageSize, equals(100));
      });
    });

    group('File Limits', () {
      test('max file size is reasonable', () {
        expect(AppConfig.maxFileSize, greaterThan(0));
        expect(AppConfig.maxFileSize, lessThanOrEqualTo(100 * 1024 * 1024));
      });

      test('max file size is in bytes', () {
        // 10 MB = 10 * 1024 * 1024 bytes
        expect(AppConfig.maxFileSize, equals(10 * 1024 * 1024));
      });

      test('max upload files is reasonable', () {
        expect(AppConfig.maxUploadFiles, greaterThan(0));
        expect(AppConfig.maxUploadFiles, lessThanOrEqualTo(50));
      });
    });

    group('Rate Limiting', () {
      test('max API requests per minute is reasonable', () {
        expect(AppConfig.maxApiRequestsPerMinute, greaterThan(0));
        expect(AppConfig.maxApiRequestsPerMinute, lessThanOrEqualTo(300));
      });

      test('max voice requests per minute is lower than API', () {
        expect(
          AppConfig.maxVoiceRequestsPerMinute,
          lessThan(AppConfig.maxApiRequestsPerMinute),
        );
      });

      test('rate limits are production-ready', () {
        expect(AppConfig.maxApiRequestsPerMinute, equals(60));
        expect(AppConfig.maxVoiceRequestsPerMinute, equals(10));
      });
    });

    group('Security', () {
      test('JWT expiry is reasonable', () {
        expect(AppConfig.jwtExpiryMinutes, greaterThan(0));
        expect(AppConfig.jwtExpiryMinutes, lessThanOrEqualTo(1440)); // 24 hours
      });

      test('refresh token expiry is longer than JWT', () {
        expect(
          Duration(days: AppConfig.refreshTokenExpiryDays),
          greaterThan(Duration(minutes: AppConfig.jwtExpiryMinutes)),
        );
      });

      test('max login attempts is reasonable', () {
        expect(AppConfig.maxLoginAttempts, greaterThan(0));
        expect(AppConfig.maxLoginAttempts, lessThanOrEqualTo(10));
      });

      test('lockout duration is reasonable', () {
        expect(AppConfig.lockoutDuration.inMinutes, greaterThan(0));
        expect(AppConfig.lockoutDuration.inMinutes, lessThanOrEqualTo(60));
      });

      test('security config is production-ready', () {
        expect(AppConfig.jwtExpiryMinutes, equals(60));
        expect(AppConfig.refreshTokenExpiryDays, equals(7));
        expect(AppConfig.maxLoginAttempts, equals(5));
        expect(AppConfig.lockoutDuration, equals(Duration(minutes: 15)));
      });
    });

    group('Consistency Checks', () {
      test('all durations are positive', () {
        expect(AppConfig.connectTimeout.inMilliseconds, greaterThan(0));
        expect(AppConfig.wsReconnectDelay.inMilliseconds, greaterThan(0));
        expect(AppConfig.voiceRecordingMaxDuration.inMilliseconds, greaterThan(0));
        expect(AppConfig.sessionTimeout.inMilliseconds, greaterThan(0));
        expect(AppConfig.cacheExpiration.inMilliseconds, greaterThan(0));
      });

      test('all size limits are positive', () {
        expect(AppConfig.maxCacheSize, greaterThan(0));
        expect(AppConfig.maxFileSize, greaterThan(0));
      });

      test('all counts are positive', () {
        expect(AppConfig.defaultPageSize, greaterThan(0));
        expect(AppConfig.maxPageSize, greaterThan(0));
        expect(AppConfig.maxUploadFiles, greaterThan(0));
        expect(AppConfig.maxApiRequestsPerMinute, greaterThan(0));
      });
    });
  });
}
