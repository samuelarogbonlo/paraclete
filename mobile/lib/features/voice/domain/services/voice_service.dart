import 'dart:async';
import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';
import 'package:paraclete/features/voice/domain/entities/voice_state.dart';
import 'package:paraclete/features/voice/domain/repositories/voice_repository.dart';

/// Service for orchestrating voice operations
/// Coordinates STT, TTS, and manages the complete voice interaction flow
class VoiceService {
  final VoiceRepository _repository;
  final AudioPlayer _audioPlayer;

  final StreamController<VoiceState> _stateController;
  VoiceState _currentState;

  StreamSubscription<TranscriptionResult>? _transcriptionSubscription;
  List<TranscriptionResult> _transcriptionHistory = [];
  Timer? _recordingTimer;
  DateTime? _recordingStartTime;

  VoiceService({
    required VoiceRepository repository,
    AudioPlayer? audioPlayer,
  })  : _repository = repository,
        _audioPlayer = audioPlayer ?? AudioPlayer(),
        _stateController = StreamController<VoiceState>.broadcast(),
        _currentState = const VoiceState() {
    _setupAudioPlayerListeners();
  }

  /// Stream of voice state changes
  Stream<VoiceState> get stateStream => _stateController.stream;

  /// Current voice state
  VoiceState get currentState => _currentState;

  /// Start recording and transcription
  Future<void> startRecording({
    required String deepgramApiKey,
    String model = 'nova-2-general',
    String language = 'en',
  }) async {
    try {
      AppLogger.info('VoiceService: Starting recording');

      _updateState(_currentState.copyWith(
        status: VoiceStatus.initializing,
        isRecording: true,
        error: null,
      ));

      // Clear previous transcription history
      _transcriptionHistory = [];

      // Start transcription stream
      final transcriptionStream = _repository.startTranscription(
        apiKey: deepgramApiKey,
        model: model,
        language: language,
        interimResults: true,
      );

      // Listen to transcription results
      _transcriptionSubscription = transcriptionStream.listen(
        _handleTranscriptionResult,
        onError: _handleTranscriptionError,
        onDone: _handleTranscriptionDone,
      );

      // Start recording timer
      _recordingStartTime = DateTime.now();
      _recordingTimer = Timer.periodic(
        const Duration(milliseconds: 100),
        _updateRecordingDuration,
      );

      _updateState(_currentState.copyWith(
        status: VoiceStatus.recording,
        isRecording: true,
      ));

      AppLogger.info('VoiceService: Recording started');
    } catch (e, stackTrace) {
      AppLogger.error('Error starting recording', error: e, stackTrace: stackTrace);
      _updateState(_currentState.copyWith(
        status: VoiceStatus.error,
        error: 'Failed to start recording: $e',
        isRecording: false,
      ));
      rethrow;
    }
  }

  /// Stop recording and transcription
  Future<void> stopRecording() async {
    try {
      AppLogger.info('VoiceService: Stopping recording');

      _updateState(_currentState.copyWith(
        status: VoiceStatus.processing,
      ));

      await _transcriptionSubscription?.cancel();
      _transcriptionSubscription = null;

      await _repository.stopTranscription();

      _recordingTimer?.cancel();
      _recordingTimer = null;
      _recordingStartTime = null;

      _updateState(_currentState.copyWith(
        status: VoiceStatus.idle,
        isRecording: false,
        recordingDuration: null,
        audioLevel: 0.0,
      ));

      AppLogger.info('VoiceService: Recording stopped');
    } catch (e, stackTrace) {
      AppLogger.error('Error stopping recording', error: e, stackTrace: stackTrace);
      _updateState(_currentState.copyWith(
        status: VoiceStatus.error,
        error: 'Failed to stop recording: $e',
        isRecording: false,
      ));
    }
  }

  /// Synthesize and play speech
  Future<void> speakText({
    required String text,
    required String elevenLabsApiKey,
    String? voiceId,
  }) async {
    try {
      AppLogger.info('VoiceService: Speaking text');

      _updateState(_currentState.copyWith(
        status: VoiceStatus.processing,
      ));

      final voiceOutput = await _repository.synthesizeSpeech(
        text: text,
        apiKey: elevenLabsApiKey,
        voiceId: voiceId,
      );

      await _playAudio(voiceOutput);
    } catch (e, stackTrace) {
      AppLogger.error('Error speaking text', error: e, stackTrace: stackTrace);
      _updateState(_currentState.copyWith(
        status: VoiceStatus.error,
        error: 'Failed to speak text: $e',
      ));
    }
  }

  /// Play audio from VoiceOutput
  Future<void> _playAudio(VoiceOutput voiceOutput) async {
    try {
      AppLogger.info('Playing audio (${voiceOutput.audioData.length} bytes)');

      _updateState(_currentState.copyWith(
        status: VoiceStatus.speaking,
        isPlaying: true,
        currentOutput: voiceOutput.copyWith(status: VoiceOutputStatus.playing),
      ));

      // Create a source from bytes
      final audioBytes = voiceOutput.audioData is List<int>
          ? Uint8List.fromList(voiceOutput.audioData as List<int>)
          : voiceOutput.audioData as Uint8List;
      final source = BytesSource(audioBytes);
      await _audioPlayer.play(source);

      AppLogger.info('Audio playback started');
    } catch (e, stackTrace) {
      AppLogger.error('Error playing audio', error: e, stackTrace: stackTrace);
      _updateState(_currentState.copyWith(
        status: VoiceStatus.error,
        error: 'Failed to play audio: $e',
        isPlaying: false,
      ));
    }
  }

  /// Stop audio playback
  Future<void> stopPlayback() async {
    try {
      AppLogger.info('VoiceService: Stopping playback');
      await _audioPlayer.stop();

      _updateState(_currentState.copyWith(
        status: VoiceStatus.idle,
        isPlaying: false,
        currentOutput: _currentState.currentOutput?.copyWith(
          status: VoiceOutputStatus.completed,
        ),
      ));
    } catch (e, stackTrace) {
      AppLogger.error('Error stopping playback', error: e, stackTrace: stackTrace);
    }
  }

  /// Pause audio playback
  Future<void> pausePlayback() async {
    try {
      await _audioPlayer.pause();

      _updateState(_currentState.copyWith(
        isPlaying: false,
        currentOutput: _currentState.currentOutput?.copyWith(
          status: VoiceOutputStatus.paused,
        ),
      ));
    } catch (e, stackTrace) {
      AppLogger.error('Error pausing playback', error: e, stackTrace: stackTrace);
    }
  }

  /// Resume audio playback
  Future<void> resumePlayback() async {
    try {
      await _audioPlayer.resume();

      _updateState(_currentState.copyWith(
        isPlaying: true,
        currentOutput: _currentState.currentOutput?.copyWith(
          status: VoiceOutputStatus.playing,
        ),
      ));
    } catch (e, stackTrace) {
      AppLogger.error('Error resuming playback', error: e, stackTrace: stackTrace);
    }
  }

  /// Clear all transcription history
  void clearTranscripts() {
    _transcriptionHistory = [];
    _updateState(_currentState.copyWith(
      currentTranscription: null,
      transcriptionHistory: [],
    ));
  }

  /// Handle transcription result from stream
  void _handleTranscriptionResult(TranscriptionResult result) {
    AppLogger.debug('Transcription result: ${result.text} (final: ${result.isFinal})');

    if (result.isFinal) {
      _transcriptionHistory.add(result);
      _updateState(_currentState.copyWith(
        currentTranscription: null,
        transcriptionHistory: List.from(_transcriptionHistory),
      ));
    } else {
      _updateState(_currentState.copyWith(
        currentTranscription: result,
      ));
    }
  }

  /// Handle transcription error
  void _handleTranscriptionError(dynamic error) {
    AppLogger.error('Transcription error: $error');
    _updateState(_currentState.copyWith(
      status: VoiceStatus.error,
      error: 'Transcription failed: $error',
    ));
  }

  /// Handle transcription stream completion
  void _handleTranscriptionDone() {
    AppLogger.info('Transcription stream completed');
  }

  /// Update recording duration
  void _updateRecordingDuration(Timer timer) {
    if (_recordingStartTime != null) {
      final duration = DateTime.now().difference(_recordingStartTime!);
      _updateState(_currentState.copyWith(
        recordingDuration: duration,
      ));
    }
  }

  /// Setup audio player event listeners
  void _setupAudioPlayerListeners() {
    _audioPlayer.onPlayerComplete.listen((_) {
      AppLogger.info('Audio playback completed');
      _updateState(_currentState.copyWith(
        status: VoiceStatus.idle,
        isPlaying: false,
        currentOutput: _currentState.currentOutput?.copyWith(
          status: VoiceOutputStatus.completed,
        ),
      ));
    });

    _audioPlayer.onPlayerStateChanged.listen((state) {
      AppLogger.debug('Audio player state: $state');
    });
  }

  /// Update state and notify listeners
  void _updateState(VoiceState newState) {
    _currentState = newState;
    if (!_stateController.isClosed) {
      _stateController.add(newState);
    }
  }

  /// Dispose resources
  Future<void> dispose() async {
    AppLogger.info('VoiceService: Disposing');

    await _transcriptionSubscription?.cancel();
    _transcriptionSubscription = null;

    _recordingTimer?.cancel();
    _recordingTimer = null;

    await _audioPlayer.dispose();
    await _repository.dispose();

    await _stateController.close();
  }
}
