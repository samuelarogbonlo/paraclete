import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure storage keys enum for type safety
enum SecureStorageKey {
  // Authentication
  accessToken('access_token'),
  refreshToken('refresh_token'),
  userId('user_id'),
  userEmail('user_email'),

  // API Keys
  anthropicKey('anthropic_api_key'),
  openaiKey('openai_api_key'),
  googleKey('google_api_key'),
  deepgramKey('deepgram_api_key'),
  elevenLabsKey('elevenlabs_api_key'),
  githubToken('github_token'),

  // Session
  currentSessionId('current_session_id'),
  lastSyncTime('last_sync_time'),

  // Encryption
  masterKey('master_key'),
  encryptionSalt('encryption_salt'),

  // Settings
  biometricEnabled('biometric_enabled'),
  autoLockTimeout('auto_lock_timeout');

  final String key;
  const SecureStorageKey(this.key);
}

/// Wrapper around flutter_secure_storage with type-safe methods
class SecureStorageService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
      resetOnError: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
      accountName: 'com.paraclete.mobile',
    ),
  );

  // Authentication tokens
  Future<void> storeAccessToken(String token) async {
    await _storage.write(key: SecureStorageKey.accessToken.key, value: token);
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: SecureStorageKey.accessToken.key);
  }

  Future<void> deleteAccessToken() async {
    await _storage.delete(key: SecureStorageKey.accessToken.key);
  }

  Future<void> storeRefreshToken(String token) async {
    await _storage.write(
      key: SecureStorageKey.refreshToken.key,
      value: token,
    );
  }

  Future<String?> getRefreshToken() async {
    return _storage.read(key: SecureStorageKey.refreshToken.key);
  }

  Future<void> deleteRefreshToken() async {
    await _storage.delete(key: SecureStorageKey.refreshToken.key);
  }

  // API Keys management
  Future<void> storeApiKey(SecureStorageKey key, String value) async {
    if (!_isApiKey(key)) {
      throw ArgumentError('Invalid API key type: $key');
    }
    await _storage.write(key: key.key, value: value);
  }

  Future<String?> getApiKey(SecureStorageKey key) async {
    if (!_isApiKey(key)) {
      throw ArgumentError('Invalid API key type: $key');
    }
    return _storage.read(key: key.key);
  }

  Future<void> deleteApiKey(SecureStorageKey key) async {
    if (!_isApiKey(key)) {
      throw ArgumentError('Invalid API key type: $key');
    }
    await _storage.delete(key: key.key);
  }

  Future<Map<String, String?>> getAllApiKeys() async {
    final keys = <String, String?>{};
    for (final key in SecureStorageKey.values) {
      if (_isApiKey(key)) {
        keys[key.name] = await getApiKey(key);
      }
    }
    return keys;
  }

  // Generic secure data storage
  Future<void> storeSecureData(String key, String value) async {
    await _storage.write(key: key, value: value);
  }

  Future<String?> getSecureData(String key) async {
    return _storage.read(key: key);
  }

  Future<void> deleteSecureData(String key) async {
    await _storage.delete(key: key);
  }

  // JSON object storage
  Future<void> storeSecureJson(String key, Map<String, dynamic> json) async {
    final jsonString = jsonEncode(json);
    await _storage.write(key: key, value: jsonString);
  }

  Future<Map<String, dynamic>?> getSecureJson(String key) async {
    final jsonString = await _storage.read(key: key);
    if (jsonString == null) return null;
    return jsonDecode(jsonString) as Map<String, dynamic>;
  }

  // User data
  Future<void> storeUserId(String userId) async {
    await _storage.write(key: SecureStorageKey.userId.key, value: userId);
  }

  Future<String?> getUserId() async {
    return _storage.read(key: SecureStorageKey.userId.key);
  }

  Future<void> storeUserEmail(String email) async {
    await _storage.write(key: SecureStorageKey.userEmail.key, value: email);
  }

  Future<String?> getUserEmail() async {
    return _storage.read(key: SecureStorageKey.userEmail.key);
  }

  // Session management
  Future<void> storeCurrentSessionId(String sessionId) async {
    await _storage.write(
      key: SecureStorageKey.currentSessionId.key,
      value: sessionId,
    );
  }

  Future<String?> getCurrentSessionId() async {
    return _storage.read(key: SecureStorageKey.currentSessionId.key);
  }

  Future<void> storeLastSyncTime(DateTime time) async {
    await _storage.write(
      key: SecureStorageKey.lastSyncTime.key,
      value: time.toIso8601String(),
    );
  }

  Future<DateTime?> getLastSyncTime() async {
    final timeString = await _storage.read(
      key: SecureStorageKey.lastSyncTime.key,
    );
    if (timeString == null) return null;
    return DateTime.tryParse(timeString);
  }

  // Biometric settings
  Future<void> setBiometricEnabled(bool enabled) async {
    await _storage.write(
      key: SecureStorageKey.biometricEnabled.key,
      value: enabled.toString(),
    );
  }

  Future<bool> getBiometricEnabled() async {
    final value = await _storage.read(
      key: SecureStorageKey.biometricEnabled.key,
    );
    return value == 'true';
  }

  // Clear all stored data (for logout)
  Future<void> clearAll() async {
    await _storage.deleteAll();
  }

  // Clear only authentication data
  Future<void> clearAuthentication() async {
    await deleteAccessToken();
    await deleteRefreshToken();
    await _storage.delete(key: SecureStorageKey.userId.key);
    await _storage.delete(key: SecureStorageKey.userEmail.key);
    await _storage.delete(key: SecureStorageKey.currentSessionId.key);
  }

  // Clear only API keys
  Future<void> clearApiKeys() async {
    for (final key in SecureStorageKey.values) {
      if (_isApiKey(key)) {
        await deleteApiKey(key);
      }
    }
  }

  // Check if storage contains a key
  Future<bool> containsKey(String key) async {
    final value = await _storage.read(key: key);
    return value != null;
  }

  Future<bool> containsSecureKey(SecureStorageKey key) async {
    final value = await _storage.read(key: key.key);
    return value != null;
  }

  // Helper to check if a key is an API key
  bool _isApiKey(SecureStorageKey key) {
    return [
      SecureStorageKey.anthropicKey,
      SecureStorageKey.openaiKey,
      SecureStorageKey.googleKey,
      SecureStorageKey.deepgramKey,
      SecureStorageKey.elevenLabsKey,
      SecureStorageKey.githubToken,
    ].contains(key);
  }
}