import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/voice/data/datasources/deepgram_datasource.dart';
import 'package:paraclete/features/voice/data/datasources/elevenlabs_datasource.dart';
import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';
import 'package:paraclete/features/voice/domain/repositories/voice_repository.dart';

/// Implementation of VoiceRepository
class VoiceRepositoryImpl implements VoiceRepository {
  final DeepgramDatasource _deepgramDatasource;
  final ElevenLabsDatasource _elevenLabsDatasource;

  VoiceRepositoryImpl({
    required DeepgramDatasource deepgramDatasource,
    required ElevenLabsDatasource elevenLabsDatasource,
  })  : _deepgramDatasource = deepgramDatasource,
        _elevenLabsDatasource = elevenLabsDatasource;

  @override
  Stream<TranscriptionResult> startTranscription({
    required String apiKey,
    String model = 'nova-2-general',
    String language = 'en',
    bool interimResults = true,
  }) {
    try {
      AppLogger.info('Starting transcription via repository');
      return _deepgramDatasource.startTranscription(
        model: model,
        language: language,
        interimResults: interimResults,
      );
    } catch (e, stackTrace) {
      AppLogger.error('Error starting transcription', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  @override
  Future<void> stopTranscription() async {
    try {
      AppLogger.info('Stopping transcription via repository');
      await _deepgramDatasource.stopTranscription();
    } catch (e, stackTrace) {
      AppLogger.error('Error stopping transcription', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  @override
  Future<void> streamAudioData(List<int> audioData) async {
    // Audio streaming is handled automatically by the datasource
    // This method is here for future use if manual streaming is needed
    AppLogger.debug('Audio data streaming (${audioData.length} bytes)');
  }

  @override
  Future<VoiceOutput> synthesizeSpeech({
    required String text,
    required String apiKey,
    String? voiceId,
    String model = 'eleven_turbo_v2',
  }) async {
    try {
      AppLogger.info('Synthesizing speech via repository');
      return await _elevenLabsDatasource.synthesizeSpeech(
        text: text,
        apiKey: apiKey,
        voiceId: voiceId,
        model: model,
      );
    } catch (e, stackTrace) {
      AppLogger.error('Error synthesizing speech', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  @override
  Stream<List<int>> streamSynthesizedSpeech({
    required String text,
    required String apiKey,
    String? voiceId,
    String model = 'eleven_turbo_v2',
  }) {
    try {
      AppLogger.info('Streaming synthesized speech via repository');
      return _elevenLabsDatasource.streamSynthesizedSpeech(
        text: text,
        apiKey: apiKey,
        voiceId: voiceId,
        model: model,
      );
    } catch (e, stackTrace) {
      AppLogger.error('Error streaming synthesized speech', error: e, stackTrace: stackTrace);
      rethrow;
    }
  }

  @override
  bool get isTranscribing => _deepgramDatasource.isTranscribing;

  @override
  bool get isConnected => _deepgramDatasource.isTranscribing;

  @override
  double get currentAudioLevel {
    // Audio level calculation would require additional logic
    // For now, return 0.0 as placeholder
    return 0.0;
  }

  @override
  Future<void> dispose() async {
    AppLogger.info('Disposing voice repository');
    await _deepgramDatasource.dispose();
    _elevenLabsDatasource.dispose();
  }
}
