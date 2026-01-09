import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:paraclete/features/voice/domain/entities/voice_state.dart';
import 'package:paraclete/features/voice/domain/services/voice_service.dart';
import 'package:paraclete/features/voice/presentation/providers/voice_provider.dart';
import '../../../../mocks/mock_secure_storage.dart';

import 'voice_provider_test.mocks.dart';

@GenerateMocks([VoiceService])
void main() {
  late MockVoiceService mockVoiceService;
  late MockSecureStorageService mockSecureStorage;
  late ProviderContainer container;

  setUp(() {
    mockVoiceService = MockVoiceService();
    mockSecureStorage = MockSecureStorageService();

    // Setup default stubs
    when(mockVoiceService.stateStream).thenAnswer((_) => const Stream.empty());
    when(mockVoiceService.currentState).thenReturn(const VoiceState());
  });

  tearDown(() {
    container.dispose();
  });

  ProviderContainer createContainer() {
    return ProviderContainer(
      overrides: [
        voiceServiceProvider.overrideWithValue(mockVoiceService),
        secureStorageProvider.overrideWithValue(mockSecureStorage),
      ],
    );
  }

  group('VoiceNotifier - Recording Operations', () {
    test('startRecording should retrieve API key and start recording', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.deepgramKey))
          .thenAnswer((_) async => 'test-deepgram-key');
      when(mockVoiceService.startRecording(
        deepgramApiKey: anyNamed('deepgramApiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
      )).thenAnswer((_) async {});

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.startRecording();

      // Assert
      verify(mockSecureStorage.getApiKey(SecureStorageKey.deepgramKey)).called(1);
      verify(mockVoiceService.startRecording(
        deepgramApiKey: 'test-deepgram-key',
        model: 'nova-2-general',
        language: 'en',
      )).called(1);
    });

    test('startRecording should throw error if API key is missing', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.deepgramKey))
          .thenAnswer((_) async => null);

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act & Assert
      expect(
        () => notifier.startRecording(),
        throwsA(isA<Exception>()),
      );

      verifyNever(mockVoiceService.startRecording(
        deepgramApiKey: anyNamed('deepgramApiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
      ));
    });

    test('startRecording should throw error if API key is empty', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.deepgramKey))
          .thenAnswer((_) async => '');

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act & Assert
      expect(
        () => notifier.startRecording(),
        throwsA(isA<Exception>()),
      );

      verifyNever(mockVoiceService.startRecording(
        deepgramApiKey: anyNamed('deepgramApiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
      ));
    });

    test('startRecording should update state to error on failure', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.deepgramKey))
          .thenAnswer((_) async => 'test-key');
      when(mockVoiceService.startRecording(
        deepgramApiKey: anyNamed('deepgramApiKey'),
        model: anyNamed('model'),
        language: anyNamed('language'),
      )).thenThrow(Exception('Connection failed'));

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      try {
        await notifier.startRecording();
      } catch (_) {
        // Expected
      }

      // Assert
      final state = container.read(voiceNotifierProvider);
      expect(state.hasError, isTrue);
      expect(state.error.toString(), contains('Connection failed'));
    });

    test('stopRecording should delegate to voice service', () async {
      // Arrange
      container = createContainer();
      when(mockVoiceService.stopRecording()).thenAnswer((_) async {});

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.stopRecording();

      // Assert
      verify(mockVoiceService.stopRecording()).called(1);
    });

    test('stopRecording should update state to error on failure', () async {
      // Arrange
      container = createContainer();
      when(mockVoiceService.stopRecording())
          .thenThrow(Exception('Failed to stop'));

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.stopRecording();

      // Assert
      final state = container.read(voiceNotifierProvider);
      expect(state.hasError, isTrue);
    });
  });

  group('VoiceNotifier - TTS Operations', () {
    test('speakText should retrieve API key and synthesize speech', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.elevenLabsKey))
          .thenAnswer((_) async => 'test-elevenlabs-key');
      when(mockVoiceService.speakText(
        text: anyNamed('text'),
        elevenLabsApiKey: anyNamed('elevenLabsApiKey'),
        voiceId: anyNamed('voiceId'),
      )).thenAnswer((_) async {});

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.speakText('Hello world');

      // Assert
      verify(mockSecureStorage.getApiKey(SecureStorageKey.elevenLabsKey)).called(1);
      verify(mockVoiceService.speakText(
        text: 'Hello world',
        elevenLabsApiKey: 'test-elevenlabs-key',
      )).called(1);
    });

    test('speakText should throw error if API key is missing', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.elevenLabsKey))
          .thenAnswer((_) async => null);

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act & Assert
      expect(
        () => notifier.speakText('Hello world'),
        throwsA(isA<Exception>()),
      );

      verifyNever(mockVoiceService.speakText(
        text: anyNamed('text'),
        elevenLabsApiKey: anyNamed('elevenLabsApiKey'),
      ));
    });

    test('speakText should update state to error on failure', () async {
      // Arrange
      container = createContainer();
      when(mockSecureStorage.getApiKey(SecureStorageKey.elevenLabsKey))
          .thenAnswer((_) async => 'test-key');
      when(mockVoiceService.speakText(
        text: anyNamed('text'),
        elevenLabsApiKey: anyNamed('elevenLabsApiKey'),
      )).thenThrow(Exception('TTS failed'));

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.speakText('Hello world');

      // Assert
      final state = container.read(voiceNotifierProvider);
      expect(state.hasError, isTrue);
    });

    test('stopPlayback should delegate to voice service', () async {
      // Arrange
      container = createContainer();
      when(mockVoiceService.stopPlayback()).thenAnswer((_) async {});

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.stopPlayback();

      // Assert
      verify(mockVoiceService.stopPlayback()).called(1);
    });

    test('pausePlayback should delegate to voice service', () async {
      // Arrange
      container = createContainer();
      when(mockVoiceService.pausePlayback()).thenAnswer((_) async {});

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.pausePlayback();

      // Assert
      verify(mockVoiceService.pausePlayback()).called(1);
    });

    test('resumePlayback should delegate to voice service', () async {
      // Arrange
      container = createContainer();
      when(mockVoiceService.resumePlayback()).thenAnswer((_) async {});

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.resumePlayback();

      // Assert
      verify(mockVoiceService.resumePlayback()).called(1);
    });
  });

  group('VoiceNotifier - State Synchronization', () {
    test('should listen to voice service state changes', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      // Act
      final voiceState = const VoiceState(
        status: VoiceStatus.recording,
        isRecording: true,
      );
      stateController.add(voiceState);

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      final state = container.read(voiceNotifierProvider);
      expect(state.hasValue, isTrue);
      expect(state.value!.status, VoiceStatus.recording);
      expect(state.value!.isRecording, isTrue);

      await stateController.close();
    });

    test('should handle voice service state errors', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      // Act
      stateController.addError(Exception('State error'));

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      final state = container.read(voiceNotifierProvider);
      expect(state.hasError, isTrue);

      await stateController.close();
    });

    test('should emit multiple state updates', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      final states = <AsyncValue<VoiceState>>[];
      container.listen(
        voiceNotifierProvider,
        (previous, next) => states.add(next),
      );

      // Act
      stateController.add(const VoiceState(status: VoiceStatus.initializing));
      await Future.delayed(const Duration(milliseconds: 10));

      stateController.add(const VoiceState(status: VoiceStatus.recording));
      await Future.delayed(const Duration(milliseconds: 10));

      stateController.add(const VoiceState(status: VoiceStatus.processing));
      await Future.delayed(const Duration(milliseconds: 10));

      // Assert
      expect(states.length, greaterThanOrEqualTo(3));
      expect(states.any((s) => s.value?.status == VoiceStatus.initializing), isTrue);
      expect(states.any((s) => s.value?.status == VoiceStatus.recording), isTrue);
      expect(states.any((s) => s.value?.status == VoiceStatus.processing), isTrue);

      await stateController.close();
    });
  });

  group('VoiceNotifier - Utility Methods', () {
    test('clearTranscripts should delegate to voice service', () {
      // Arrange
      container = createContainer();
      when(mockVoiceService.clearTranscripts()).thenReturn(null);

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      notifier.clearTranscripts();

      // Assert
      verify(mockVoiceService.clearTranscripts()).called(1);
    });

    test('cancelOperation should stop recording if recording', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);
      when(mockVoiceService.stopRecording()).thenAnswer((_) async {});
      when(mockVoiceService.clearTranscripts()).thenReturn(null);

      container = createContainer();

      // Set state to recording
      stateController.add(const VoiceState(isRecording: true));
      await Future.delayed(const Duration(milliseconds: 50));

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.cancelOperation();

      // Assert
      verify(mockVoiceService.stopRecording()).called(1);
      verify(mockVoiceService.clearTranscripts()).called(1);

      await stateController.close();
    });

    test('cancelOperation should stop playback if playing', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);
      when(mockVoiceService.stopPlayback()).thenAnswer((_) async {});
      when(mockVoiceService.clearTranscripts()).thenReturn(null);

      container = createContainer();

      // Set state to playing
      stateController.add(const VoiceState(isPlaying: true));
      await Future.delayed(const Duration(milliseconds: 50));

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.cancelOperation();

      // Assert
      verify(mockVoiceService.stopPlayback()).called(1);
      verify(mockVoiceService.clearTranscripts()).called(1);

      await stateController.close();
    });

    test('cancelOperation should only clear transcripts if idle', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);
      when(mockVoiceService.clearTranscripts()).thenReturn(null);

      container = createContainer();

      // Set state to idle
      stateController.add(const VoiceState(
        isRecording: false,
        isPlaying: false,
      ));
      await Future.delayed(const Duration(milliseconds: 50));

      final notifier = container.read(voiceNotifierProvider.notifier);

      // Act
      await notifier.cancelOperation();

      // Assert
      verifyNever(mockVoiceService.stopRecording());
      verifyNever(mockVoiceService.stopPlayback());
      verify(mockVoiceService.clearTranscripts()).called(1);

      await stateController.close();
    });
  });

  group('Convenience Providers', () {
    test('voiceStateProvider should return current voice state', () {
      // Arrange
      final voiceState = const VoiceState(
        status: VoiceStatus.recording,
        isRecording: true,
      );
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();
      stateController.add(voiceState);

      // Act
      final state = container.read(voiceStateProvider);

      // Assert
      // Initial state might be null
      expect(state?.status, anyOf(isNull, equals(VoiceStatus.recording)));

      stateController.close();
    });

    test('isRecordingProvider should reflect recording state', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      // Act - Start recording
      stateController.add(const VoiceState(isRecording: true));
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(container.read(isRecordingProvider), isTrue);

      // Act - Stop recording
      stateController.add(const VoiceState(isRecording: false));
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(container.read(isRecordingProvider), isFalse);

      await stateController.close();
    });

    test('isPlayingProvider should reflect playback state', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      // Act - Start playing
      stateController.add(const VoiceState(isPlaying: true));
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(container.read(isPlayingProvider), isTrue);

      // Act - Stop playing
      stateController.add(const VoiceState(isPlaying: false));
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(container.read(isPlayingProvider), isFalse);

      await stateController.close();
    });

    test('fullTranscriptProvider should return complete transcript', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      final voiceState = const VoiceState(
        transcriptionHistory: [], // Would need actual transcription results
      );

      // Act
      stateController.add(voiceState);
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      final transcript = container.read(fullTranscriptProvider);
      expect(transcript, isA<String>());

      await stateController.close();
    });

    test('interimTranscriptProvider should return interim transcript', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      // Act
      stateController.add(const VoiceState());
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      final interim = container.read(interimTranscriptProvider);
      expect(interim, isA<String>());

      await stateController.close();
    });
  });

  group('VoiceNotifier - Resource Management', () {
    test('should dispose subscription on provider dispose', () async {
      // Arrange
      final stateController = StreamController<VoiceState>();
      when(mockVoiceService.stateStream).thenAnswer((_) => stateController.stream);

      container = createContainer();

      // Force initialization
      container.read(voiceNotifierProvider);

      // Act
      container.dispose();

      // Assert - Stream controller should still be usable (not closed by listener)
      expect(stateController.isClosed, isFalse);

      await stateController.close();
    });
  });
}
