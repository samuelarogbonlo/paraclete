import 'dart:async';
import 'package:deepgram_speech_to_text/deepgram_speech_to_text.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';
import 'package:record/record.dart';

/// Deepgram datasource for real-time speech-to-text
/// Implements the verified pattern from CLAUDE.md Appendix
class DeepgramDatasource {
  // Audio Configuration - DO NOT MODIFY THESE VALUES
  static const int sampleRate = 16000; // 16kHz
  static const int bitDepth = 16; // 16-bit
  static const int channels = 1; // Mono
  static const String encoding = 'linear16'; // PCM

  final Deepgram _deepgram;
  final AudioRecorder _recorder;
  StreamSubscription<DeepgramSttResult>? _transcriptionSubscription;
  StreamController<TranscriptionResult>? _resultController;
  bool _isTranscribing = false;
  int _retryCount = 0;
  static const int _maxRetries = 5;
  static const int _initialRetryDelay = 1000; // milliseconds
  static const int _maxRetryDelay = 30000; // milliseconds

  DeepgramDatasource({
    required String apiKey,
    AudioRecorder? recorder,
  })  : _deepgram = Deepgram(apiKey, baseQueryParams: {}),
        _recorder = recorder ?? AudioRecorder();

  /// Start real-time transcription with WebSocket streaming
  Stream<TranscriptionResult> startTranscription({
    String model = 'nova-2-general',
    String language = 'en',
    bool interimResults = true,
  }) {
    if (_isTranscribing) {
      throw StateError('Transcription already in progress');
    }

    _resultController = StreamController<TranscriptionResult>.broadcast();
    _isTranscribing = true;
    _retryCount = 0;

    _startTranscriptionInternal(
      model: model,
      language: language,
      interimResults: interimResults,
    );

    return _resultController!.stream;
  }

  Future<void> _startTranscriptionInternal({
    required String model,
    required String language,
    required bool interimResults,
  }) async {
    try {
      AppLogger.info('Starting Deepgram transcription with WebSocket');

      // Check microphone permission
      if (!await _recorder.hasPermission()) {
        AppLogger.error('Microphone permission not granted');
        _emitError('Microphone permission denied');
        return;
      }

      // Start audio recording with verified configuration
      final audioStream = await _recorder.startStream(
        const RecordConfig(
          encoder: AudioEncoder.pcm16bits, // Must be linear16
          sampleRate: sampleRate,
          numChannels: channels,
        ),
      );

      // Configure Deepgram streaming parameters
      final streamParams = DeepgramSttParams(
        model: model,
        language: language,
        interimResults: interimResults,
        encoding: encoding,
        sampleRate: sampleRate,
        channels: channels,
      );

      AppLogger.info('Deepgram params: $streamParams');

      // Create live transcription stream
      final transcriptionStream = _deepgram.transcribeFromLiveAudioStream(
        audioStream,
        streamParams,
      );

      // Listen to transcription results
      _transcriptionSubscription = transcriptionStream.listen(
        (result) => _handleTranscriptionResult(result),
        onError: (error) => _handleTranscriptionError(error),
        onDone: () => _handleTranscriptionDone(),
        cancelOnError: false,
      );

      _retryCount = 0; // Reset retry count on successful connection
      AppLogger.info('Deepgram transcription started successfully');
    } catch (e, stackTrace) {
      AppLogger.error('Error starting transcription', e, stackTrace);
      await _handleConnectionError(
        model: model,
        language: language,
        interimResults: interimResults,
      );
    }
  }

  void _handleTranscriptionResult(DeepgramSttResult result) {
    try {
      if (result.transcript == null || result.transcript!.isEmpty) {
        return;
      }

      final transcriptionResult = TranscriptionResult(
        text: result.transcript!,
        isFinal: result.isFinal ?? false,
        confidence: result.confidence ?? 0.0,
        timestamp: DateTime.now(),
        duration: result.duration,
      );

      AppLogger.debug(
        'Transcription: "${transcriptionResult.text}" (final: ${transcriptionResult.isFinal})',
      );

      _resultController?.add(transcriptionResult);
    } catch (e, stackTrace) {
      AppLogger.error('Error handling transcription result', e, stackTrace);
    }
  }

  void _handleTranscriptionError(dynamic error) {
    AppLogger.error('Transcription error: $error');
    _emitError('Transcription failed: $error');
  }

  void _handleTranscriptionDone() {
    AppLogger.info('Transcription stream completed');
  }

  Future<void> _handleConnectionError({
    required String model,
    required String language,
    required bool interimResults,
  }) async {
    if (_retryCount >= _maxRetries) {
      AppLogger.error('Max retries reached, giving up');
      _emitError('Failed to connect after $_maxRetries attempts');
      await stopTranscription();
      return;
    }

    _retryCount++;
    final delayMs = _calculateRetryDelay();

    AppLogger.warning(
      'Connection error, retrying in ${delayMs}ms (attempt $_retryCount/$_maxRetries)',
    );

    await Future.delayed(Duration(milliseconds: delayMs));

    if (_isTranscribing) {
      await _startTranscriptionInternal(
        model: model,
        language: language,
        interimResults: interimResults,
      );
    }
  }

  int _calculateRetryDelay() {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
    final delay = _initialRetryDelay * (1 << (_retryCount - 1));
    return delay > _maxRetryDelay ? _maxRetryDelay : delay;
  }

  void _emitError(String message) {
    if (_resultController != null && !_resultController!.isClosed) {
      _resultController!.addError(Exception(message));
    }
  }

  /// Stop transcription and cleanup resources
  Future<void> stopTranscription() async {
    try {
      AppLogger.info('Stopping Deepgram transcription');

      _isTranscribing = false;

      await _transcriptionSubscription?.cancel();
      _transcriptionSubscription = null;

      await _recorder.stop();

      await _resultController?.close();
      _resultController = null;

      _retryCount = 0;

      AppLogger.info('Deepgram transcription stopped');
    } catch (e, stackTrace) {
      AppLogger.error('Error stopping transcription', e, stackTrace);
    }
  }

  /// Check if transcription is active
  bool get isTranscribing => _isTranscribing;

  /// Check if recorder is recording
  Future<bool> get isRecording async {
    return await _recorder.isRecording();
  }

  /// Dispose resources
  Future<void> dispose() async {
    await stopTranscription();
    _recorder.dispose();
  }
}
