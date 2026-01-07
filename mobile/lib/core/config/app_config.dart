/// App configuration constants and settings
class AppConfig {
  AppConfig._();

  // App info
  static const String appName = 'Paraclete';
  static const String appVersion = '1.0.0';
  static const String appBuildNumber = '1';

  // API timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);

  // WebSocket config
  static const Duration wsReconnectDelay = Duration(seconds: 1);
  static const Duration wsPingInterval = Duration(seconds: 30);
  static const int wsMaxReconnectAttempts = 5;

  // Voice config
  static const Duration voiceRecordingMaxDuration = Duration(minutes: 5);
  static const int voiceSampleRate = 16000;
  static const Duration voiceDebounceDelay = Duration(milliseconds: 200);

  // Terminal config
  static const int terminalColumns = 80;
  static const int terminalRows = 24;
  static const int terminalScrollbackLines = 1000;

  // Session config
  static const Duration sessionTimeout = Duration(hours: 1);
  static const Duration sessionRefreshInterval = Duration(minutes: 5);

  // Cache config
  static const Duration cacheExpiration = Duration(hours: 24);
  static const int maxCacheSize = 100 * 1024 * 1024; // 100 MB

  // Feature flags
  static const bool enableVoiceInput = true;
  static const bool enableTerminal = true;
  static const bool enableMultiAgent = true;
  static const bool enableSessionSync = true;
  static const bool enableOfflineMode = false;

  // Pagination
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  // File limits
  static const int maxFileSize = 10 * 1024 * 1024; // 10 MB
  static const int maxUploadFiles = 10;

  // Rate limiting
  static const int maxApiRequestsPerMinute = 60;
  static const int maxVoiceRequestsPerMinute = 10;

  // Security
  static const int jwtExpiryMinutes = 60;
  static const int refreshTokenExpiryDays = 7;
  static const int maxLoginAttempts = 5;
  static const Duration lockoutDuration = Duration(minutes: 15);
}