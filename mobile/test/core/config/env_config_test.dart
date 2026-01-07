import 'package:flutter_test/flutter_test.dart';
import 'package:paraclete/core/config/env_config.dart';

void main() {
  group('EnvConfig', () {
    setUp(() {
      // Reset to development for tests
      EnvConfig.setEnvironment(Environment.development);
    });

    group('Environment Management', () {
      test('defaults to development environment', () {
        expect(EnvConfig.environment, Environment.development);
        expect(EnvConfig.isDevelopment, isTrue);
        expect(EnvConfig.isStaging, isFalse);
        expect(EnvConfig.isProduction, isFalse);
      });

      test('can set environment to staging', () {
        EnvConfig.setEnvironment(Environment.staging);

        expect(EnvConfig.environment, Environment.staging);
        expect(EnvConfig.isDevelopment, isFalse);
        expect(EnvConfig.isStaging, isTrue);
        expect(EnvConfig.isProduction, isFalse);
      });

      test('can set environment to production', () {
        EnvConfig.setEnvironment(Environment.production);

        expect(EnvConfig.environment, Environment.production);
        expect(EnvConfig.isDevelopment, isFalse);
        expect(EnvConfig.isStaging, isFalse);
        expect(EnvConfig.isProduction, isTrue);
      });
    });

    group('API Base URL', () {
      test('returns localhost for development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.apiBaseUrl, 'http://localhost:8000');
      });

      test('returns staging URL for staging', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.apiBaseUrl, 'https://staging-api.paraclete.dev');
      });

      test('returns production URL for production', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.apiBaseUrl, 'https://api.paraclete.dev');
      });

      test('all URLs are valid HTTP(S) URLs', () {
        for (var env in Environment.values) {
          EnvConfig.setEnvironment(env);
          final url = EnvConfig.apiBaseUrl;
          expect(url, anyOf(startsWith('http://'), startsWith('https://')));
        }
      });
    });

    group('WebSocket Base URL', () {
      test('returns localhost WebSocket for development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.wsBaseUrl, 'ws://localhost:8000');
      });

      test('returns staging WebSocket URL for staging', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.wsBaseUrl, 'wss://staging-api.paraclete.dev');
      });

      test('returns production WebSocket URL for production', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.wsBaseUrl, 'wss://api.paraclete.dev');
      });

      test('uses secure WebSocket in non-development', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.wsBaseUrl, startsWith('wss://'));

        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.wsBaseUrl, startsWith('wss://'));
      });

      test('uses insecure WebSocket in development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.wsBaseUrl, startsWith('ws://'));
      });
    });

    group('External Service URLs', () {
      test('Deepgram URL is constant across environments', () {
        for (var env in Environment.values) {
          EnvConfig.setEnvironment(env);
          expect(EnvConfig.deepgramWsUrl, 'wss://api.deepgram.com/v1/listen');
        }
      });

      test('ElevenLabs URL is constant across environments', () {
        for (var env in Environment.values) {
          EnvConfig.setEnvironment(env);
          expect(EnvConfig.elevenLabsApiUrl, 'https://api.elevenlabs.io/v1');
        }
      });

      test('external URLs use HTTPS/WSS', () {
        expect(EnvConfig.deepgramWsUrl, startsWith('wss://'));
        expect(EnvConfig.elevenLabsApiUrl, startsWith('https://'));
      });
    });

    group('Firebase Configuration', () {
      test('development has dev Firebase project', () {
        EnvConfig.setEnvironment(Environment.development);
        final config = EnvConfig.firebaseConfig;

        expect(config['projectId'], 'paraclete-dev');
        expect(config['messagingSenderId'], isNotEmpty);
      });

      test('staging has staging Firebase project', () {
        EnvConfig.setEnvironment(Environment.staging);
        final config = EnvConfig.firebaseConfig;

        expect(config['projectId'], 'paraclete-staging');
        expect(config['messagingSenderId'], isNotEmpty);
      });

      test('production has prod Firebase project', () {
        EnvConfig.setEnvironment(Environment.production);
        final config = EnvConfig.firebaseConfig;

        expect(config['projectId'], 'paraclete-prod');
        expect(config['messagingSenderId'], isNotEmpty);
      });

      test('Firebase config has required fields', () {
        for (var env in Environment.values) {
          EnvConfig.setEnvironment(env);
          final config = EnvConfig.firebaseConfig;

          expect(config.containsKey('projectId'), isTrue);
          expect(config.containsKey('messagingSenderId'), isTrue);
          expect(config['projectId'], isNotEmpty);
          expect(config['messagingSenderId'], isNotEmpty);
        }
      });
    });

    group('Logging Configuration', () {
      test('logging enabled in development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.enableLogging, isTrue);
      });

      test('logging enabled in staging', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.enableLogging, isTrue);
      });

      test('logging disabled in production', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.enableLogging, isFalse);
      });
    });

    group('Error Reporting', () {
      test('error reporting disabled in development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.enableErrorReporting, isFalse);
      });

      test('error reporting enabled in staging', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.enableErrorReporting, isTrue);
      });

      test('error reporting enabled in production', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.enableErrorReporting, isTrue);
      });
    });

    group('Mock Data', () {
      test('mock data enabled in development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.useMockData, isTrue);
      });

      test('mock data disabled in staging', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.useMockData, isFalse);
      });

      test('mock data disabled in production', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.useMockData, isFalse);
      });
    });

    group('Analytics', () {
      test('analytics disabled in development', () {
        EnvConfig.setEnvironment(Environment.development);
        expect(EnvConfig.enableAnalytics, isFalse);
      });

      test('analytics disabled in staging', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.enableAnalytics, isFalse);
      });

      test('analytics enabled in production', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.enableAnalytics, isTrue);
      });
    });

    group('Feature Overrides', () {
      test('development has debug features enabled', () {
        EnvConfig.setEnvironment(Environment.development);
        final overrides = EnvConfig.featureOverrides;

        expect(overrides['debugShowGrid'], isTrue);
        expect(overrides['showDebugBanner'], isTrue);
      });

      test('staging has debug features disabled', () {
        EnvConfig.setEnvironment(Environment.staging);
        final overrides = EnvConfig.featureOverrides;

        expect(overrides['debugShowGrid'], isFalse);
        expect(overrides['showDebugBanner'], isFalse);
      });

      test('production has all debug features disabled', () {
        EnvConfig.setEnvironment(Environment.production);
        final overrides = EnvConfig.featureOverrides;

        expect(overrides['debugShowGrid'], isFalse);
        expect(overrides['debugShowPerformanceOverlay'], isFalse);
        expect(overrides['showDebugBanner'], isFalse);
      });

      test('feature overrides are consistent', () {
        for (var env in Environment.values) {
          EnvConfig.setEnvironment(env);
          final overrides = EnvConfig.featureOverrides;

          expect(overrides.containsKey('debugShowGrid'), isTrue);
          expect(overrides.containsKey('debugShowPerformanceOverlay'), isTrue);
          expect(overrides.containsKey('showDebugBanner'), isTrue);
        }
      });
    });

    group('Security Best Practices', () {
      test('production uses HTTPS for API', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.apiBaseUrl, startsWith('https://'));
      });

      test('production uses WSS for WebSocket', () {
        EnvConfig.setEnvironment(Environment.production);
        expect(EnvConfig.wsBaseUrl, startsWith('wss://'));
      });

      test('staging uses HTTPS/WSS', () {
        EnvConfig.setEnvironment(Environment.staging);
        expect(EnvConfig.apiBaseUrl, startsWith('https://'));
        expect(EnvConfig.wsBaseUrl, startsWith('wss://'));
      });

      test('production has minimal debug surface', () {
        EnvConfig.setEnvironment(Environment.production);

        expect(EnvConfig.enableLogging, isFalse);
        expect(EnvConfig.useMockData, isFalse);
        expect(EnvConfig.featureOverrides['debugShowGrid'], isFalse);
        expect(EnvConfig.featureOverrides['showDebugBanner'], isFalse);
      });
    });

    group('Environment Enum', () {
      test('has all required environments', () {
        expect(Environment.values.length, 3);
        expect(Environment.values, contains(Environment.development));
        expect(Environment.values, contains(Environment.staging));
        expect(Environment.values, contains(Environment.production));
      });
    });
  });
}
