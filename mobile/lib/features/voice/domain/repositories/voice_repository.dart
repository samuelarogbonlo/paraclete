import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';

/// Repository interface for voice operations
abstract class VoiceRepository {
  /// Start streaming audio for real-time transcription
  /// Returns a stream of transcription results (both interim and final)
  Stream<TranscriptionResult> startTranscription({
    required String apiKey,
    String model = 'nova-2-general',
    String language = 'en',
    bool interimResults = true,
  });

  /// Stop the current transcription stream
  Future<void> stopTranscription();

  /// Stream audio data for transcription
  /// Used to send audio chunks to the transcription service
  Future<void> streamAudioData(List<int> audioData);

  /// Synthesize speech from text using TTS
  /// Returns a VoiceOutput containing audio data
  Future<VoiceOutput> synthesizeSpeech({
    required String text,
    required String apiKey,
    String? voiceId,
    String model = 'eleven_turbo_v2',
  });

  /// Stream synthesized speech for real-time playback
  /// Returns a stream of audio chunks
  Stream<List<int>> streamSynthesizedSpeech({
    required String text,
    required String apiKey,
    String? voiceId,
    String model = 'eleven_turbo_v2',
  });

  /// Check if transcription is currently active
  bool get isTranscribing;

  /// Check if there's an active WebSocket connection
  bool get isConnected;

  /// Get the current audio level (0.0 to 1.0)
  double get currentAudioLevel;

  /// Dispose resources
  Future<void> dispose();
}
