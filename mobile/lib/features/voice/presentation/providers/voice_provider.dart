import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/voice/data/datasources/deepgram_datasource.dart';
import 'package:paraclete/features/voice/data/datasources/elevenlabs_datasource.dart';
import 'package:paraclete/features/voice/data/repositories/voice_repository_impl.dart';
import 'package:paraclete/features/voice/domain/entities/voice_state.dart';
import 'package:paraclete/features/voice/domain/services/voice_service.dart';

/// Provider for Deepgram datasource
final deepgramDatasourceProvider = Provider<DeepgramDatasource>((ref) {
  // API key will be injected when starting transcription
  return DeepgramDatasource(apiKey: '');
});

/// Provider for ElevenLabs datasource
final elevenLabsDatasourceProvider = Provider<ElevenLabsDatasource>((ref) {
  return ElevenLabsDatasource();
});

/// Provider for voice repository
final voiceRepositoryProvider = Provider<VoiceRepositoryImpl>((ref) {
  return VoiceRepositoryImpl(
    deepgramDatasource: ref.watch(deepgramDatasourceProvider),
    elevenLabsDatasource: ref.watch(elevenLabsDatasourceProvider),
  );
});

/// Provider for voice service
final voiceServiceProvider = Provider<VoiceService>((ref) {
  final repository = ref.watch(voiceRepositoryProvider);
  final service = VoiceService(repository: repository);

  ref.onDispose(() {
    service.dispose();
  });

  return service;
});

/// Provider for secure storage service
final secureStorageProvider = Provider<SecureStorageService>((ref) {
  return SecureStorageService();
});

/// State notifier for voice interactions
class VoiceNotifier extends StateNotifier<AsyncValue<VoiceState>> {
  final VoiceService _voiceService;
  final SecureStorageService _secureStorage;
  StreamSubscription<VoiceState>? _stateSubscription;

  VoiceNotifier({
    required VoiceService voiceService,
    required SecureStorageService secureStorage,
  })  : _voiceService = voiceService,
        _secureStorage = secureStorage,
        super(const AsyncValue.data(VoiceState())) {
    _init();
  }

  void _init() {
    // Listen to voice service state changes
    _stateSubscription = _voiceService.stateStream.listen(
      (voiceState) {
        state = AsyncValue.data(voiceState);
      },
      onError: (error, stackTrace) {
        AppLogger.error('Voice state error', error, stackTrace);
        state = AsyncValue.error(error, stackTrace);
      },
    );
  }

  /// Start recording with hold-to-record pattern
  Future<void> startRecording() async {
    try {
      AppLogger.info('VoiceNotifier: Starting recording');

      // Get Deepgram API key
      final deepgramKey = await _secureStorage.getApiKey(
        SecureStorageKey.deepgramKey,
      );

      if (deepgramKey == null || deepgramKey.isEmpty) {
        throw Exception('Deepgram API key not configured');
      }

      await _voiceService.startRecording(
        deepgramApiKey: deepgramKey,
        model: 'nova-2-general',
        language: 'en',
      );
    } catch (e, stackTrace) {
      AppLogger.error('Error starting recording', e, stackTrace);
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }

  /// Stop recording
  Future<void> stopRecording() async {
    try {
      AppLogger.info('VoiceNotifier: Stopping recording');
      await _voiceService.stopRecording();
    } catch (e, stackTrace) {
      AppLogger.error('Error stopping recording', e, stackTrace);
      state = AsyncValue.error(e, stackTrace);
    }
  }

  /// Speak text using TTS
  Future<void> speakText(String text) async {
    try {
      AppLogger.info('VoiceNotifier: Speaking text');

      // Get ElevenLabs API key
      final elevenLabsKey = await _secureStorage.getApiKey(
        SecureStorageKey.elevenLabsKey,
      );

      if (elevenLabsKey == null || elevenLabsKey.isEmpty) {
        throw Exception('ElevenLabs API key not configured');
      }

      await _voiceService.speakText(
        text: text,
        elevenLabsApiKey: elevenLabsKey,
      );
    } catch (e, stackTrace) {
      AppLogger.error('Error speaking text', e, stackTrace);
      state = AsyncValue.error(e, stackTrace);
    }
  }

  /// Stop audio playback
  Future<void> stopPlayback() async {
    try {
      await _voiceService.stopPlayback();
    } catch (e, stackTrace) {
      AppLogger.error('Error stopping playback', e, stackTrace);
    }
  }

  /// Pause audio playback
  Future<void> pausePlayback() async {
    try {
      await _voiceService.pausePlayback();
    } catch (e, stackTrace) {
      AppLogger.error('Error pausing playback', e, stackTrace);
    }
  }

  /// Resume audio playback
  Future<void> resumePlayback() async {
    try {
      await _voiceService.resumePlayback();
    } catch (e, stackTrace) {
      AppLogger.error('Error resuming playback', e, stackTrace);
    }
  }

  /// Clear all transcription history
  void clearTranscripts() {
    try {
      _voiceService.clearTranscripts();
    } catch (e, stackTrace) {
      AppLogger.error('Error clearing transcripts', e, stackTrace);
    }
  }

  /// Cancel current operation
  Future<void> cancelOperation() async {
    try {
      if (state.value?.isRecording ?? false) {
        await stopRecording();
      }
      if (state.value?.isPlaying ?? false) {
        await stopPlayback();
      }
      clearTranscripts();
    } catch (e, stackTrace) {
      AppLogger.error('Error canceling operation', e, stackTrace);
    }
  }

  @override
  void dispose() {
    _stateSubscription?.cancel();
    super.dispose();
  }
}

/// Provider for voice notifier
final voiceNotifierProvider =
    StateNotifierProvider<VoiceNotifier, AsyncValue<VoiceState>>((ref) {
  final voiceService = ref.watch(voiceServiceProvider);
  final secureStorage = ref.watch(secureStorageProvider);

  return VoiceNotifier(
    voiceService: voiceService,
    secureStorage: secureStorage,
  );
});

/// Convenience provider for current voice state
final voiceStateProvider = Provider<VoiceState?>((ref) {
  final asyncState = ref.watch(voiceNotifierProvider);
  return asyncState.valueOrNull;
});

/// Provider for checking if recording is active
final isRecordingProvider = Provider<bool>((ref) {
  final state = ref.watch(voiceStateProvider);
  return state?.isRecording ?? false;
});

/// Provider for checking if audio is playing
final isPlayingProvider = Provider<bool>((ref) {
  final state = ref.watch(voiceStateProvider);
  return state?.isPlaying ?? false;
});

/// Provider for full transcript
final fullTranscriptProvider = Provider<String>((ref) {
  final state = ref.watch(voiceStateProvider);
  return state?.fullTranscript ?? '';
});

/// Provider for interim transcript
final interimTranscriptProvider = Provider<String>((ref) {
  final state = ref.watch(voiceStateProvider);
  return state?.interimTranscript ?? '';
});
