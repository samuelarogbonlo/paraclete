import 'package:shared_preferences/shared_preferences.dart';

/// Preference keys enum for type safety
enum PreferenceKey {
  // Theme
  isDarkMode('is_dark_mode'),
  themeMode('theme_mode'),

  // Voice settings
  voiceLanguage('voice_language'),
  voiceModel('voice_model'),
  voiceSpeed('voice_speed'),
  voiceVolume('voice_volume'),
  voiceAutoPlay('voice_auto_play'),

  // Terminal settings
  terminalFontSize('terminal_font_size'),
  terminalColorScheme('terminal_color_scheme'),
  terminalScrollback('terminal_scrollback'),

  // Agent settings
  defaultModel('default_model'),
  parallelAgents('parallel_agents'),
  autoApprove('auto_approve'),
  agentTimeout('agent_timeout'),

  // Notification settings
  notificationsEnabled('notifications_enabled'),
  soundEnabled('sound_enabled'),
  vibrationEnabled('vibration_enabled'),

  // Display settings
  compactMode('compact_mode'),
  showAgentAvatars('show_agent_avatars'),
  showTimestamps('show_timestamps'),

  // Developer settings
  debugMode('debug_mode'),
  verboseLogging('verbose_logging'),
  showPerformanceOverlay('show_performance_overlay'),

  // Onboarding
  hasCompletedOnboarding('has_completed_onboarding'),
  hasSeenVoiceTutorial('has_seen_voice_tutorial'),
  hasSeenAgentTutorial('has_seen_agent_tutorial'),

  // Usage tracking
  firstLaunchDate('first_launch_date'),
  lastLaunchDate('last_launch_date'),
  launchCount('launch_count'),
  totalVoiceMinutes('total_voice_minutes'),
  totalAgentInvocations('total_agent_invocations');

  final String key;
  const PreferenceKey(this.key);
}

/// Wrapper around shared_preferences with type-safe methods
class PreferencesService {
  static SharedPreferences? _prefs;

  /// Initialize preferences (call once at app startup)
  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  static SharedPreferences get _instance {
    if (_prefs == null) {
      throw StateError(
        'PreferencesService not initialized. Call PreferencesService.init() first.',
      );
    }
    return _prefs!;
  }

  // Theme preferences
  static bool get isDarkMode =>
      _instance.getBool(PreferenceKey.isDarkMode.key) ?? false;

  static Future<void> setDarkMode(bool value) =>
      _instance.setBool(PreferenceKey.isDarkMode.key, value);

  static String get themeMode =>
      _instance.getString(PreferenceKey.themeMode.key) ?? 'system';

  static Future<void> setThemeMode(String value) =>
      _instance.setString(PreferenceKey.themeMode.key, value);

  // Voice settings
  static String get voiceLanguage =>
      _instance.getString(PreferenceKey.voiceLanguage.key) ?? 'en-US';

  static Future<void> setVoiceLanguage(String value) =>
      _instance.setString(PreferenceKey.voiceLanguage.key, value);

  static String get voiceModel =>
      _instance.getString(PreferenceKey.voiceModel.key) ?? 'nova-2-general';

  static Future<void> setVoiceModel(String value) =>
      _instance.setString(PreferenceKey.voiceModel.key, value);

  static double get voiceSpeed =>
      _instance.getDouble(PreferenceKey.voiceSpeed.key) ?? 1.0;

  static Future<void> setVoiceSpeed(double value) =>
      _instance.setDouble(PreferenceKey.voiceSpeed.key, value);

  static double get voiceVolume =>
      _instance.getDouble(PreferenceKey.voiceVolume.key) ?? 1.0;

  static Future<void> setVoiceVolume(double value) =>
      _instance.setDouble(PreferenceKey.voiceVolume.key, value);

  static bool get voiceAutoPlay =>
      _instance.getBool(PreferenceKey.voiceAutoPlay.key) ?? true;

  static Future<void> setVoiceAutoPlay(bool value) =>
      _instance.setBool(PreferenceKey.voiceAutoPlay.key, value);

  // Terminal settings
  static int get terminalFontSize =>
      _instance.getInt(PreferenceKey.terminalFontSize.key) ?? 14;

  static Future<void> setTerminalFontSize(int value) =>
      _instance.setInt(PreferenceKey.terminalFontSize.key, value);

  static String get terminalColorScheme =>
      _instance.getString(PreferenceKey.terminalColorScheme.key) ?? 'default';

  static Future<void> setTerminalColorScheme(String value) =>
      _instance.setString(PreferenceKey.terminalColorScheme.key, value);

  static int get terminalScrollback =>
      _instance.getInt(PreferenceKey.terminalScrollback.key) ?? 1000;

  static Future<void> setTerminalScrollback(int value) =>
      _instance.setInt(PreferenceKey.terminalScrollback.key, value);

  // Agent settings
  static String get defaultModel =>
      _instance.getString(PreferenceKey.defaultModel.key) ??
      'claude-3-5-sonnet';

  static Future<void> setDefaultModel(String value) =>
      _instance.setString(PreferenceKey.defaultModel.key, value);

  static bool get parallelAgents =>
      _instance.getBool(PreferenceKey.parallelAgents.key) ?? true;

  static Future<void> setParallelAgents(bool value) =>
      _instance.setBool(PreferenceKey.parallelAgents.key, value);

  static bool get autoApprove =>
      _instance.getBool(PreferenceKey.autoApprove.key) ?? false;

  static Future<void> setAutoApprove(bool value) =>
      _instance.setBool(PreferenceKey.autoApprove.key, value);

  static int get agentTimeout =>
      _instance.getInt(PreferenceKey.agentTimeout.key) ?? 300; // 5 minutes

  static Future<void> setAgentTimeout(int value) =>
      _instance.setInt(PreferenceKey.agentTimeout.key, value);

  // Notification settings
  static bool get notificationsEnabled =>
      _instance.getBool(PreferenceKey.notificationsEnabled.key) ?? true;

  static Future<void> setNotificationsEnabled(bool value) =>
      _instance.setBool(PreferenceKey.notificationsEnabled.key, value);

  static bool get soundEnabled =>
      _instance.getBool(PreferenceKey.soundEnabled.key) ?? true;

  static Future<void> setSoundEnabled(bool value) =>
      _instance.setBool(PreferenceKey.soundEnabled.key, value);

  static bool get vibrationEnabled =>
      _instance.getBool(PreferenceKey.vibrationEnabled.key) ?? true;

  static Future<void> setVibrationEnabled(bool value) =>
      _instance.setBool(PreferenceKey.vibrationEnabled.key, value);

  // Display settings
  static bool get compactMode =>
      _instance.getBool(PreferenceKey.compactMode.key) ?? false;

  static Future<void> setCompactMode(bool value) =>
      _instance.setBool(PreferenceKey.compactMode.key, value);

  static bool get showAgentAvatars =>
      _instance.getBool(PreferenceKey.showAgentAvatars.key) ?? true;

  static Future<void> setShowAgentAvatars(bool value) =>
      _instance.setBool(PreferenceKey.showAgentAvatars.key, value);

  static bool get showTimestamps =>
      _instance.getBool(PreferenceKey.showTimestamps.key) ?? true;

  static Future<void> setShowTimestamps(bool value) =>
      _instance.setBool(PreferenceKey.showTimestamps.key, value);

  // Developer settings
  static bool get debugMode =>
      _instance.getBool(PreferenceKey.debugMode.key) ?? false;

  static Future<void> setDebugMode(bool value) =>
      _instance.setBool(PreferenceKey.debugMode.key, value);

  static bool get verboseLogging =>
      _instance.getBool(PreferenceKey.verboseLogging.key) ?? false;

  static Future<void> setVerboseLogging(bool value) =>
      _instance.setBool(PreferenceKey.verboseLogging.key, value);

  static bool get showPerformanceOverlay =>
      _instance.getBool(PreferenceKey.showPerformanceOverlay.key) ?? false;

  static Future<void> setShowPerformanceOverlay(bool value) =>
      _instance.setBool(PreferenceKey.showPerformanceOverlay.key, value);

  // Onboarding
  static bool get hasCompletedOnboarding =>
      _instance.getBool(PreferenceKey.hasCompletedOnboarding.key) ?? false;

  static Future<void> setHasCompletedOnboarding(bool value) =>
      _instance.setBool(PreferenceKey.hasCompletedOnboarding.key, value);

  static bool get hasSeenVoiceTutorial =>
      _instance.getBool(PreferenceKey.hasSeenVoiceTutorial.key) ?? false;

  static Future<void> setHasSeenVoiceTutorial(bool value) =>
      _instance.setBool(PreferenceKey.hasSeenVoiceTutorial.key, value);

  static bool get hasSeenAgentTutorial =>
      _instance.getBool(PreferenceKey.hasSeenAgentTutorial.key) ?? false;

  static Future<void> setHasSeenAgentTutorial(bool value) =>
      _instance.setBool(PreferenceKey.hasSeenAgentTutorial.key, value);

  // Usage tracking
  static DateTime? get firstLaunchDate {
    final timestamp = _instance.getInt(PreferenceKey.firstLaunchDate.key);
    return timestamp != null
        ? DateTime.fromMillisecondsSinceEpoch(timestamp)
        : null;
  }

  static Future<void> setFirstLaunchDate(DateTime value) =>
      _instance.setInt(
        PreferenceKey.firstLaunchDate.key,
        value.millisecondsSinceEpoch,
      );

  static DateTime? get lastLaunchDate {
    final timestamp = _instance.getInt(PreferenceKey.lastLaunchDate.key);
    return timestamp != null
        ? DateTime.fromMillisecondsSinceEpoch(timestamp)
        : null;
  }

  static Future<void> setLastLaunchDate(DateTime value) =>
      _instance.setInt(
        PreferenceKey.lastLaunchDate.key,
        value.millisecondsSinceEpoch,
      );

  static int get launchCount =>
      _instance.getInt(PreferenceKey.launchCount.key) ?? 0;

  static Future<void> incrementLaunchCount() =>
      _instance.setInt(PreferenceKey.launchCount.key, launchCount + 1);

  static double get totalVoiceMinutes =>
      _instance.getDouble(PreferenceKey.totalVoiceMinutes.key) ?? 0.0;

  static Future<void> addVoiceMinutes(double minutes) =>
      _instance.setDouble(
        PreferenceKey.totalVoiceMinutes.key,
        totalVoiceMinutes + minutes,
      );

  static int get totalAgentInvocations =>
      _instance.getInt(PreferenceKey.totalAgentInvocations.key) ?? 0;

  static Future<void> incrementAgentInvocations() =>
      _instance.setInt(
        PreferenceKey.totalAgentInvocations.key,
        totalAgentInvocations + 1,
      );

  // Generic methods
  static Future<bool> setString(String key, String value) =>
      _instance.setString(key, value);

  static String? getString(String key) => _instance.getString(key);

  static Future<bool> setInt(String key, int value) =>
      _instance.setInt(key, value);

  static int? getInt(String key) => _instance.getInt(key);

  static Future<bool> setBool(String key, bool value) =>
      _instance.setBool(key, value);

  static bool? getBool(String key) => _instance.getBool(key);

  static Future<bool> setDouble(String key, double value) =>
      _instance.setDouble(key, value);

  static double? getDouble(String key) => _instance.getDouble(key);

  static Future<bool> setStringList(String key, List<String> value) =>
      _instance.setStringList(key, value);

  static List<String>? getStringList(String key) =>
      _instance.getStringList(key);

  static Future<bool> remove(String key) => _instance.remove(key);

  static Future<bool> clear() => _instance.clear();

  static bool containsKey(String key) => _instance.containsKey(key);

  static Set<String> getKeys() => _instance.getKeys();

  static Future<void> reload() => _instance.reload();
}