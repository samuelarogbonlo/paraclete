import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';
import 'package:paraclete/features/voice/domain/entities/voice_state.dart';
import 'package:paraclete/features/voice/domain/repositories/voice_repository.dart';
import 'package:paraclete/features/voice/domain/services/voice_service.dart';

import 'voice_service_test.mocks.dart';

@GenerateMocks([VoiceRepository, AudioPlayer])
void main() {
  late MockVoiceRepository mockRepository;
  late MockAudioPlayer mockAudioPlayer;
  late VoiceService voiceService;

  setUp(() {
    mockRepository = MockVoiceRepository();
    mockAudioPlayer = MockAudioPlayer();
    voiceService = VoiceService(
      repository: mockRepository,
      audioPlayer: mockAudioPlayer,
    );
  });

  tearDown(() async {
    await voiceService.dispose();
  });

  group('VoiceService - Recording Operations', () {
    test('startRecording should initialize and start transcription stream', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      // Act
      final stateStream = voiceService.stateStream;
      final states = <VoiceState>[];
      final subscription = stateStream.listen(states.add);

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      await Future.delayed(const Duration(milliseconds: 100));

      // Assert
      expect(states.length, greaterThanOrEqualTo(2));
      expect(states.first.status, VoiceStatus.initializing);
      expect(states.last.status, VoiceStatus.recording);
      expect(states.last.isRecording, isTrue);

      verify(mockRepository.startTranscription(
        apiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
        interimResults: true,
      )).called(1);

      await subscription.cancel();
      await transcriptionController.close();
    });

    test('stopRecording should cancel subscription and stop transcription', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      when(mockRepository.stopTranscription()).thenAnswer((_) async {});

      // Start recording first
      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Act
      await voiceService.stopRecording();

      // Assert
      expect(voiceService.currentState.status, VoiceStatus.idle);
      expect(voiceService.currentState.isRecording, isFalse);
      expect(voiceService.currentState.recordingDuration, isNull);
      expect(voiceService.currentState.audioLevel, 0.0);

      verify(mockRepository.stopTranscription()).called(1);

      await transcriptionController.close();
    });

    test('startRecording should handle errors and update state accordingly', () async {
      // Arrange
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenThrow(Exception('Deepgram connection failed'));

      // Act & Assert
      expect(
        () => voiceService.startRecording(
          deepgramApiKey: 'test-key',
          model: 'nova-2-general',
          language: 'en',
        ),
        throwsException,
      );

      // Verify error state
      await Future.delayed(const Duration(milliseconds: 50));
      expect(voiceService.currentState.status, VoiceStatus.error);
      expect(voiceService.currentState.isRecording, isFalse);
      expect(voiceService.currentState.error, contains('Failed to start recording'));
    });

    test('recording should update duration periodically', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      // Act
      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Wait for timer to tick
      await Future.delayed(const Duration(milliseconds: 250));

      // Assert
      expect(voiceService.currentState.recordingDuration, isNotNull);
      expect(
        voiceService.currentState.recordingDuration!.inMilliseconds,
        greaterThan(200),
      );

      await transcriptionController.close();
    });

    test('startRecording should clear previous transcription history', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      when(mockRepository.stopTranscription()).thenAnswer((_) async {});

      // Start first recording and add transcription
      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      transcriptionController.add(TranscriptionResult(
        text: 'Previous transcript',
        confidence: 0.95,
        isFinal: true,
        duration: const Duration(seconds: 2),
      ));

      await Future.delayed(const Duration(milliseconds: 50));
      await voiceService.stopRecording();

      // Act - Start new recording
      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Assert
      expect(voiceService.currentState.transcriptionHistory, isEmpty);

      await transcriptionController.close();
    });
  });

  group('VoiceService - Transcription Handling', () {
    test('should update currentTranscription with interim results', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Act
      final interimResult = TranscriptionResult(
        text: 'Hello world',
        confidence: 0.85,
        isFinal: false,
        duration: const Duration(milliseconds: 500),
      );
      transcriptionController.add(interimResult);

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(voiceService.currentState.currentTranscription, isNotNull);
      expect(voiceService.currentState.currentTranscription!.text, 'Hello world');
      expect(voiceService.currentState.currentTranscription!.isFinal, isFalse);

      await transcriptionController.close();
    });

    test('should add final results to transcription history', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Act
      final finalResult = TranscriptionResult(
        text: 'Final transcript',
        confidence: 0.95,
        isFinal: true,
        duration: const Duration(seconds: 2),
      );
      transcriptionController.add(finalResult);

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(voiceService.currentState.transcriptionHistory, hasLength(1));
      expect(voiceService.currentState.transcriptionHistory.first.text, 'Final transcript');
      expect(voiceService.currentState.transcriptionHistory.first.isFinal, isTrue);
      expect(voiceService.currentState.currentTranscription, isNull);

      await transcriptionController.close();
    });

    test('should handle multiple transcription results', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Act - Add multiple results
      transcriptionController.add(TranscriptionResult(
        text: 'First',
        confidence: 0.9,
        isFinal: true,
        duration: const Duration(seconds: 1),
      ));

      await Future.delayed(const Duration(milliseconds: 50));

      transcriptionController.add(TranscriptionResult(
        text: 'Second',
        confidence: 0.92,
        isFinal: true,
        duration: const Duration(seconds: 1),
      ));

      await Future.delayed(const Duration(milliseconds: 50));

      transcriptionController.add(TranscriptionResult(
        text: 'Third',
        confidence: 0.88,
        isFinal: true,
        duration: const Duration(seconds: 1),
      ));

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(voiceService.currentState.transcriptionHistory, hasLength(3));
      expect(voiceService.currentState.transcriptionHistory[0].text, 'First');
      expect(voiceService.currentState.transcriptionHistory[1].text, 'Second');
      expect(voiceService.currentState.transcriptionHistory[2].text, 'Third');

      await transcriptionController.close();
    });

    test('should handle transcription errors', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Act
      transcriptionController.addError(Exception('WebSocket connection lost'));

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(voiceService.currentState.status, VoiceStatus.error);
      expect(voiceService.currentState.error, contains('Transcription failed'));

      await transcriptionController.close();
    });

    test('clearTranscripts should remove all transcription history', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      transcriptionController.add(TranscriptionResult(
        text: 'Test transcript',
        confidence: 0.95,
        isFinal: true,
        duration: const Duration(seconds: 2),
      ));

      await Future.delayed(const Duration(milliseconds: 50));

      // Act
      voiceService.clearTranscripts();

      // Assert
      expect(voiceService.currentState.transcriptionHistory, isEmpty);
      expect(voiceService.currentState.currentTranscription, isNull);

      await transcriptionController.close();
    });
  });

  group('VoiceService - TTS Operations', () {
    test('speakText should synthesize and play audio', () async {
      // Arrange
      final audioData = List<int>.filled(1000, 0);
      final voiceOutput = VoiceOutput(
        audioData: audioData,
        duration: const Duration(seconds: 3),
        text: 'Hello world',
        voiceId: 'test-voice',
        status: VoiceOutputStatus.ready,
      );

      when(mockRepository.synthesizeSpeech(
        text: anyNamed('text'),
        apiKey: anyNamed('apiKey'),
        voiceId: anyNamed('voiceId'),
      )).thenAnswer((_) async => voiceOutput);

      when(mockAudioPlayer.play(any)).thenAnswer((_) async {});

      // Act
      await voiceService.speakText(
        text: 'Hello world',
        elevenLabsApiKey: 'test-key',
        voiceId: 'test-voice',
      );

      // Assert
      expect(voiceService.currentState.status, VoiceStatus.speaking);
      expect(voiceService.currentState.isPlaying, isTrue);
      expect(voiceService.currentState.currentOutput, isNotNull);
      expect(voiceService.currentState.currentOutput!.text, 'Hello world');

      verify(mockRepository.synthesizeSpeech(
        text: 'Hello world',
        apiKey: 'test-key',
        voiceId: 'test-voice',
      )).called(1);

      verify(mockAudioPlayer.play(any)).called(1);
    });

    test('speakText should handle synthesis errors', () async {
      // Arrange
      when(mockRepository.synthesizeSpeech(
        text: anyNamed('text'),
        apiKey: anyNamed('apiKey'),
        voiceId: anyNamed('voiceId'),
      )).thenThrow(Exception('ElevenLabs API error'));

      // Act
      await voiceService.speakText(
        text: 'Hello world',
        elevenLabsApiKey: 'test-key',
      );

      // Assert
      expect(voiceService.currentState.status, VoiceStatus.error);
      expect(voiceService.currentState.error, contains('Failed to speak text'));
      expect(voiceService.currentState.isPlaying, isFalse);
    });

    test('stopPlayback should stop audio and update state', () async {
      // Arrange
      final audioData = List<int>.filled(1000, 0);
      final voiceOutput = VoiceOutput(
        audioData: audioData,
        duration: const Duration(seconds: 3),
        text: 'Hello world',
        voiceId: 'test-voice',
        status: VoiceOutputStatus.playing,
      );

      when(mockRepository.synthesizeSpeech(
        text: anyNamed('text'),
        apiKey: anyNamed('apiKey'),
        voiceId: anyNamed('voiceId'),
      )).thenAnswer((_) async => voiceOutput);

      when(mockAudioPlayer.play(any)).thenAnswer((_) async {});
      when(mockAudioPlayer.stop()).thenAnswer((_) async {});

      // Start playing first
      await voiceService.speakText(
        text: 'Hello world',
        elevenLabsApiKey: 'test-key',
      );

      // Act
      await voiceService.stopPlayback();

      // Assert
      expect(voiceService.currentState.status, VoiceStatus.idle);
      expect(voiceService.currentState.isPlaying, isFalse);
      expect(voiceService.currentState.currentOutput!.status, VoiceOutputStatus.completed);

      verify(mockAudioPlayer.stop()).called(1);
    });

    test('pausePlayback should pause audio', () async {
      // Arrange
      when(mockAudioPlayer.pause()).thenAnswer((_) async {});

      // Act
      await voiceService.pausePlayback();

      // Assert
      expect(voiceService.currentState.isPlaying, isFalse);
      verify(mockAudioPlayer.pause()).called(1);
    });

    test('resumePlayback should resume audio', () async {
      // Arrange
      when(mockAudioPlayer.resume()).thenAnswer((_) async {});

      // Act
      await voiceService.resumePlayback();

      // Assert
      expect(voiceService.currentState.isPlaying, isTrue);
      verify(mockAudioPlayer.resume()).called(1);
    });

    test('should handle audio playback completion', () async {
      // Arrange
      final completeController = StreamController<void>();
      when(mockAudioPlayer.onPlayerComplete).thenAnswer((_) => completeController.stream);
      when(mockAudioPlayer.onPlayerStateChanged).thenAnswer((_) => const Stream.empty());

      // Create new service to capture listener setup
      final service = VoiceService(
        repository: mockRepository,
        audioPlayer: mockAudioPlayer,
      );

      final audioData = List<int>.filled(1000, 0);
      final voiceOutput = VoiceOutput(
        audioData: audioData,
        duration: const Duration(seconds: 1),
        text: 'Short text',
        voiceId: 'test-voice',
        status: VoiceOutputStatus.ready,
      );

      when(mockRepository.synthesizeSpeech(
        text: anyNamed('text'),
        apiKey: anyNamed('apiKey'),
        voiceId: anyNamed('voiceId'),
      )).thenAnswer((_) async => voiceOutput);

      when(mockAudioPlayer.play(any)).thenAnswer((_) async {});

      await service.speakText(
        text: 'Short text',
        elevenLabsApiKey: 'test-key',
      );

      // Act - Simulate completion
      completeController.add(null);
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(service.currentState.status, VoiceStatus.idle);
      expect(service.currentState.isPlaying, isFalse);
      expect(service.currentState.currentOutput!.status, VoiceOutputStatus.completed);

      await service.dispose();
      await completeController.close();
    });
  });

  group('VoiceService - State Management', () {
    test('should emit state changes through stateStream', () async {
      // Arrange
      final states = <VoiceState>[];
      final subscription = voiceService.stateStream.listen(states.add);

      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      when(mockRepository.stopTranscription()).thenAnswer((_) async {});

      // Act
      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      await Future.delayed(const Duration(milliseconds: 50));

      await voiceService.stopRecording();

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(states.length, greaterThan(2));
      expect(states.any((s) => s.status == VoiceStatus.initializing), isTrue);
      expect(states.any((s) => s.status == VoiceStatus.recording), isTrue);
      expect(states.any((s) => s.status == VoiceStatus.processing), isTrue);
      expect(states.last.status, VoiceStatus.idle);

      await subscription.cancel();
      await transcriptionController.close();
    });

    test('currentState should always reflect latest state', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      // Act & Assert - Initial state
      expect(voiceService.currentState.status, VoiceStatus.idle);
      expect(voiceService.currentState.isRecording, isFalse);

      // Start recording
      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      expect(voiceService.currentState.status, VoiceStatus.recording);
      expect(voiceService.currentState.isRecording, isTrue);

      await transcriptionController.close();
    });
  });

  group('VoiceService - Resource Cleanup', () {
    test('dispose should clean up all resources', () async {
      // Arrange
      final transcriptionController = StreamController<TranscriptionResult>();
      when(mockRepository.startTranscription(
        apiKey: anyNamed('apiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
        interimResults: anyNamed('interimResults'),
      )).thenAnswer((_) => transcriptionController.stream);

      when(mockAudioPlayer.dispose()).thenAnswer((_) async {});
      when(mockRepository.dispose()).thenAnswer((_) async {});

      await voiceService.startRecording(
        deepgramApiKey: 'test-key',
        model: 'nova-2-general',
        language: 'en',
      );

      // Act
      await voiceService.dispose();

      // Assert
      verify(mockAudioPlayer.dispose()).called(1);
      verify(mockRepository.dispose()).called(1);

      await transcriptionController.close();
    });

    test('dispose should be idempotent', () async {
      // Arrange
      when(mockAudioPlayer.dispose()).thenAnswer((_) async {});
      when(mockRepository.dispose()).thenAnswer((_) async {});

      // Act
      await voiceService.dispose();
      await voiceService.dispose(); // Call twice

      // Assert - Should not throw
      verify(mockAudioPlayer.dispose()).called(2);
      verify(mockRepository.dispose()).called(2);
    });
  });
}
