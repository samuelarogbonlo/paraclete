import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';

/// ElevenLabs datasource for text-to-speech
/// Implements streaming TTS for natural response playback
class ElevenLabsDatasource {
  static const String _baseUrl = 'https://api.elevenlabs.io/v1';
  static const String _defaultVoiceId = 'EXAVITQu4vr4xnSDxMaL'; // Bella voice

  final Dio _dio;

  ElevenLabsDatasource({Dio? dio})
      : _dio = dio ??
            Dio(BaseOptions(
              baseUrl: _baseUrl,
              connectTimeout: const Duration(seconds: 30),
              receiveTimeout: const Duration(minutes: 2),
            ));

  /// Synthesize speech from text (non-streaming)
  /// Returns complete audio data
  Future<VoiceOutput> synthesizeSpeech({
    required String text,
    required String apiKey,
    String? voiceId,
    String model = 'eleven_turbo_v2',
  }) async {
    try {
      final effectiveVoiceId = voiceId ?? _defaultVoiceId;
      AppLogger.info('Synthesizing speech with ElevenLabs (voice: $effectiveVoiceId)');

      final response = await _dio.post<List<int>>(
        '/text-to-speech/$effectiveVoiceId',
        data: {
          'text': text,
          'model_id': model,
          'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75,
          },
        },
        options: Options(
          headers: {
            'xi-api-key': apiKey,
            'Content-Type': 'application/json',
          },
          responseType: ResponseType.bytes,
        ),
      );

      if (response.data == null || response.data!.isEmpty) {
        throw Exception('Empty audio data received from ElevenLabs');
      }

      final audioData = response.data!;
      AppLogger.info('Received ${audioData.length} bytes of audio data');

      return VoiceOutput(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: text,
        audioData: audioData,
        voiceId: effectiveVoiceId,
        timestamp: DateTime.now(),
        duration: _estimateDuration(audioData.length),
        status: VoiceOutputStatus.pending,
      );
    } catch (e, stackTrace) {
      AppLogger.error('Error synthesizing speech', e, stackTrace);
      rethrow;
    }
  }

  /// Stream synthesized speech for real-time playback
  /// Returns audio chunks as they are received
  Stream<List<int>> streamSynthesizedSpeech({
    required String text,
    required String apiKey,
    String? voiceId,
    String model = 'eleven_turbo_v2',
  }) async* {
    try {
      final effectiveVoiceId = voiceId ?? _defaultVoiceId;
      AppLogger.info('Streaming speech with ElevenLabs (voice: $effectiveVoiceId)');

      final response = await _dio.post<ResponseBody>(
        '/text-to-speech/$effectiveVoiceId/stream',
        data: {
          'text': text,
          'model_id': model,
          'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75,
          },
        },
        options: Options(
          headers: {
            'xi-api-key': apiKey,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
          },
          responseType: ResponseType.stream,
        ),
      );

      if (response.data == null) {
        throw Exception('No stream received from ElevenLabs');
      }

      final stream = response.data!.stream;
      await for (final chunk in stream) {
        if (chunk is List<int> && chunk.isNotEmpty) {
          yield chunk;
        }
      }

      AppLogger.info('Speech streaming completed');
    } catch (e, stackTrace) {
      AppLogger.error('Error streaming speech', e, stackTrace);
      rethrow;
    }
  }

  /// Get available voices from ElevenLabs
  Future<List<Map<String, dynamic>>> getVoices({
    required String apiKey,
  }) async {
    try {
      AppLogger.info('Fetching available voices from ElevenLabs');

      final response = await _dio.get(
        '/voices',
        options: Options(
          headers: {
            'xi-api-key': apiKey,
          },
        ),
      );

      final voices = (response.data['voices'] as List)
          .map((v) => v as Map<String, dynamic>)
          .toList();

      AppLogger.info('Retrieved ${voices.length} voices');
      return voices;
    } catch (e, stackTrace) {
      AppLogger.error('Error fetching voices', e, stackTrace);
      rethrow;
    }
  }

  /// Get user subscription info
  Future<Map<String, dynamic>> getUserInfo({
    required String apiKey,
  }) async {
    try {
      final response = await _dio.get(
        '/user',
        options: Options(
          headers: {
            'xi-api-key': apiKey,
          },
        ),
      );

      return response.data as Map<String, dynamic>;
    } catch (e, stackTrace) {
      AppLogger.error('Error fetching user info', e, stackTrace);
      rethrow;
    }
  }

  /// Estimate audio duration based on byte size
  /// Rough estimation: MP3 at 128kbps = ~16KB/second
  Duration _estimateDuration(int bytes) {
    const bytesPerSecond = 16000; // ~128kbps MP3
    final seconds = bytes / bytesPerSecond;
    return Duration(milliseconds: (seconds * 1000).round());
  }

  /// Dispose resources
  void dispose() {
    _dio.close();
  }
}
