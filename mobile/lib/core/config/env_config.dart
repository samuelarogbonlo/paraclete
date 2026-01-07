/// Environment configuration for different deployment stages
enum Environment {
  development,
  staging,
  production,
}

class EnvConfig {
  EnvConfig._();

  static Environment _environment = Environment.development;

  static void setEnvironment(Environment env) {
    _environment = env;
  }

  static Environment get environment => _environment;

  static bool get isDevelopment => _environment == Environment.development;
  static bool get isStaging => _environment == Environment.staging;
  static bool get isProduction => _environment == Environment.production;

  /// API base URL based on environment
  static String get apiBaseUrl {
    switch (_environment) {
      case Environment.development:
        return 'http://localhost:8000';
      case Environment.staging:
        return 'https://staging-api.paraclete.dev';
      case Environment.production:
        return 'https://api.paraclete.dev';
    }
  }

  /// WebSocket base URL based on environment
  static String get wsBaseUrl {
    switch (_environment) {
      case Environment.development:
        return 'ws://localhost:8000';
      case Environment.staging:
        return 'wss://staging-api.paraclete.dev';
      case Environment.production:
        return 'wss://api.paraclete.dev';
    }
  }

  /// Deepgram WebSocket URL
  static String get deepgramWsUrl {
    return 'wss://api.deepgram.com/v1/listen';
  }

  /// ElevenLabs API base URL
  static String get elevenLabsApiUrl {
    return 'https://api.elevenlabs.io/v1';
  }

  /// Firebase project configuration
  static Map<String, String> get firebaseConfig {
    switch (_environment) {
      case Environment.development:
        return {
          'projectId': 'paraclete-dev',
          'messagingSenderId': '123456789',
        };
      case Environment.staging:
        return {
          'projectId': 'paraclete-staging',
          'messagingSenderId': '987654321',
        };
      case Environment.production:
        return {
          'projectId': 'paraclete-prod',
          'messagingSenderId': '456789123',
        };
    }
  }

  /// Enable logging based on environment
  static bool get enableLogging {
    switch (_environment) {
      case Environment.development:
        return true;
      case Environment.staging:
        return true;
      case Environment.production:
        return false;
    }
  }

  /// Enable error reporting
  static bool get enableErrorReporting {
    switch (_environment) {
      case Environment.development:
        return false;
      case Environment.staging:
        return true;
      case Environment.production:
        return true;
    }
  }

  /// Enable mock data for development
  static bool get useMockData {
    return _environment == Environment.development;
  }

  /// Analytics configuration
  static bool get enableAnalytics {
    return _environment == Environment.production;
  }

  /// Feature overrides for testing
  static Map<String, bool> get featureOverrides {
    switch (_environment) {
      case Environment.development:
        return {
          'debugShowGrid': true,
          'debugShowPerformanceOverlay': false,
          'showDebugBanner': true,
        };
      case Environment.staging:
        return {
          'debugShowGrid': false,
          'debugShowPerformanceOverlay': false,
          'showDebugBanner': false,
        };
      case Environment.production:
        return {
          'debugShowGrid': false,
          'debugShowPerformanceOverlay': false,
          'showDebugBanner': false,
        };
    }
  }
}