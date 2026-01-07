import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/network/api_client.dart';
import 'package:paraclete/core/network/websocket_client.dart';
import 'package:paraclete/core/storage/secure_storage.dart';

/// Secure storage service provider
final secureStorageProvider = Provider<SecureStorageService>((ref) {
  return SecureStorageService();
});

/// API client provider
final apiClientProvider = Provider<ApiClient>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  return ApiClient(secureStorage: secureStorage);
});

/// WebSocket client provider
final webSocketClientProvider = Provider<WebSocketClient>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  return WebSocketClient(secureStorage: secureStorage);
});

/// WebSocket connection state provider
final webSocketStateProvider = StreamProvider<WebSocketState>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.state;
});

/// WebSocket messages provider
final webSocketMessagesProvider = StreamProvider<WebSocketMessage>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.messages;
});

/// Current session ID provider
final currentSessionIdProvider = StateProvider<String?>((ref) => null);

/// User authentication state
class AuthState {
  final bool isAuthenticated;
  final String? userId;
  final String? email;
  final String? accessToken;

  AuthState({
    required this.isAuthenticated,
    this.userId,
    this.email,
    this.accessToken,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    String? userId,
    String? email,
    String? accessToken,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      userId: userId ?? this.userId,
      email: email ?? this.email,
      accessToken: accessToken ?? this.accessToken,
    );
  }
}

/// Authentication state notifier
class AuthNotifier extends StateNotifier<AuthState> {
  final SecureStorageService _secureStorage;

  AuthNotifier(this._secureStorage)
      : super(AuthState(isAuthenticated: false)) {
    _loadAuthState();
  }

  Future<void> _loadAuthState() async {
    final accessToken = await _secureStorage.getAccessToken();
    final userId = await _secureStorage.getUserId();
    final email = await _secureStorage.getUserEmail();

    state = AuthState(
      isAuthenticated: accessToken != null,
      userId: userId,
      email: email,
      accessToken: accessToken,
    );
  }

  Future<void> login({
    required String accessToken,
    required String refreshToken,
    required String userId,
    required String email,
  }) async {
    await _secureStorage.storeAccessToken(accessToken);
    await _secureStorage.storeRefreshToken(refreshToken);
    await _secureStorage.storeUserId(userId);
    await _secureStorage.storeUserEmail(email);

    state = AuthState(
      isAuthenticated: true,
      userId: userId,
      email: email,
      accessToken: accessToken,
    );
  }

  Future<void> logout() async {
    await _secureStorage.clearAuthentication();
    state = AuthState(isAuthenticated: false);
  }

  Future<void> updateTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _secureStorage.storeAccessToken(accessToken);
    await _secureStorage.storeRefreshToken(refreshToken);

    state = state.copyWith(accessToken: accessToken);
  }
}

/// Authentication provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  return AuthNotifier(secureStorage);
});

/// App settings state
class AppSettings {
  final bool isDarkMode;
  final String voiceLanguage;
  final String voiceModel;
  final bool notificationsEnabled;
  final String defaultModel;

  AppSettings({
    required this.isDarkMode,
    required this.voiceLanguage,
    required this.voiceModel,
    required this.notificationsEnabled,
    required this.defaultModel,
  });

  AppSettings copyWith({
    bool? isDarkMode,
    String? voiceLanguage,
    String? voiceModel,
    bool? notificationsEnabled,
    String? defaultModel,
  }) {
    return AppSettings(
      isDarkMode: isDarkMode ?? this.isDarkMode,
      voiceLanguage: voiceLanguage ?? this.voiceLanguage,
      voiceModel: voiceModel ?? this.voiceModel,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      defaultModel: defaultModel ?? this.defaultModel,
    );
  }
}

/// App settings notifier
class AppSettingsNotifier extends StateNotifier<AppSettings> {
  AppSettingsNotifier()
      : super(AppSettings(
          isDarkMode: false,
          voiceLanguage: 'en-US',
          voiceModel: 'nova-2-general',
          notificationsEnabled: true,
          defaultModel: 'claude-3-5-sonnet',
        ));

  void toggleDarkMode() {
    state = state.copyWith(isDarkMode: !state.isDarkMode);
  }

  void setVoiceLanguage(String language) {
    state = state.copyWith(voiceLanguage: language);
  }

  void setVoiceModel(String model) {
    state = state.copyWith(voiceModel: model);
  }

  void setNotificationsEnabled(bool enabled) {
    state = state.copyWith(notificationsEnabled: enabled);
  }

  void setDefaultModel(String model) {
    state = state.copyWith(defaultModel: model);
  }
}

/// App settings provider
final appSettingsProvider =
    StateNotifierProvider<AppSettingsNotifier, AppSettings>((ref) {
  return AppSettingsNotifier();
});

/// Loading state provider for global loading indicators
final isLoadingProvider = StateProvider<bool>((ref) => false);

/// Error state provider for global error handling
final errorProvider = StateProvider<String?>((ref) => null);

/// Session list provider (placeholder for now)
final sessionsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final apiClient = ref.watch(apiClientProvider);

  try {
    final response = await apiClient.getSessions();
    if (response.statusCode == 200) {
      return List<Map<String, dynamic>>.from(response.data['sessions'] ?? []);
    }
    return [];
  } catch (e) {
    return [];
  }
});

/// Agent status provider (placeholder for now)
final agentStatusProvider = StateProvider<Map<String, String>>((ref) {
  return {
    'supervisor': 'idle',
    'researcher': 'idle',
    'coder': 'idle',
    'reviewer': 'idle',
    'designer': 'idle',
  };
});

/// API keys provider
class ApiKeys {
  final String? anthropicKey;
  final String? openaiKey;
  final String? googleKey;
  final String? deepgramKey;
  final String? elevenLabsKey;
  final String? githubToken;

  ApiKeys({
    this.anthropicKey,
    this.openaiKey,
    this.googleKey,
    this.deepgramKey,
    this.elevenLabsKey,
    this.githubToken,
  });
}

/// API keys notifier
class ApiKeysNotifier extends StateNotifier<ApiKeys> {
  final SecureStorageService _secureStorage;

  ApiKeysNotifier(this._secureStorage) : super(ApiKeys()) {
    _loadApiKeys();
  }

  Future<void> _loadApiKeys() async {
    state = ApiKeys(
      anthropicKey: await _secureStorage.getApiKey(SecureStorageKey.anthropicKey),
      openaiKey: await _secureStorage.getApiKey(SecureStorageKey.openaiKey),
      googleKey: await _secureStorage.getApiKey(SecureStorageKey.googleKey),
      deepgramKey: await _secureStorage.getApiKey(SecureStorageKey.deepgramKey),
      elevenLabsKey: await _secureStorage.getApiKey(SecureStorageKey.elevenLabsKey),
      githubToken: await _secureStorage.getApiKey(SecureStorageKey.githubToken),
    );
  }

  Future<void> updateApiKey(SecureStorageKey key, String? value) async {
    if (value != null && value.isNotEmpty) {
      await _secureStorage.storeApiKey(key, value);
    } else {
      await _secureStorage.deleteApiKey(key);
    }
    await _loadApiKeys();
  }

  Future<void> clearAllApiKeys() async {
    await _secureStorage.clearApiKeys();
    state = ApiKeys();
  }
}

/// API keys provider
final apiKeysProvider = StateNotifierProvider<ApiKeysNotifier, ApiKeys>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);
  return ApiKeysNotifier(secureStorage);
});