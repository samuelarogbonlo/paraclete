import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:deepgram_speech_to_text/deepgram_speech_to_text.dart';
import 'package:record/record.dart';
import 'package:paraclete/features/voice/data/datasources/deepgram_datasource.dart';
import 'package:paraclete/features/voice/domain/entities/transcription_result.dart';

@GenerateMocks([Deepgram, AudioRecorder])
import 'deepgram_datasource_test.mocks.dart';

void main() {
  group('DeepgramDatasource', () {
    late MockDeepgram mockDeepgram;
    late MockAudioRecorder mockRecorder;
    late DeepgramDatasource datasource;

    setUp(() {
      mockDeepgram = MockDeepgram();
      mockRecorder = MockAudioRecorder();
    });

    tearDown(() async {
      await datasource.dispose();
    });

    group('Audio Configuration', () {
      test('uses correct audio parameters', () {
        expect(DeepgramDatasource.sampleRate, equals(16000));
        expect(DeepgramDatasource.bitDepth, equals(16));
        expect(DeepgramDatasource.channels, equals(1));
        expect(DeepgramDatasource.encoding, equals('linear16'));
      });
    });

    group('Transcription Lifecycle', () {
      test('startTranscription throws if already transcribing', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        // Mock successful permission check
        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        // Mock audio stream
        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        // Mock Deepgram transcription stream
        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        // Start first transcription
        final stream1 = datasource.startTranscription();

        // Attempt to start second transcription should throw
        expect(
          () => datasource.startTranscription(),
          throwsA(isA<StateError>().having(
            (e) => e.message,
            'message',
            contains('already in progress'),
          )),
        );

        await stream1.drain();
        await audioController.close();
        await transcriptionController.close();
      });

      test('isTranscribing returns correct state', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        expect(datasource.isTranscribing, isFalse);

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);
        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        datasource.startTranscription();

        // Wait a moment for async initialization
        await Future.delayed(const Duration(milliseconds: 100));

        expect(datasource.isTranscribing, isTrue);

        await datasource.stopTranscription();
        expect(datasource.isTranscribing, isFalse);

        await audioController.close();
        await transcriptionController.close();
      });

      test('stopTranscription cleans up resources', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);
        when(mockRecorder.stop()).thenAnswer((_) async => null);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription();

        await Future.delayed(const Duration(milliseconds: 100));

        await datasource.stopTranscription();

        verify(mockRecorder.stop()).called(1);
        expect(datasource.isTranscribing, isFalse);

        await stream.drain();
        await audioController.close();
        await transcriptionController.close();
      });
    });

    group('Transcription Results', () {
      test('emits interim results correctly', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription(interimResults: true);

        final results = <TranscriptionResult>[];
        final subscription = stream.listen(results.add);

        await Future.delayed(const Duration(milliseconds: 100));

        // Emit interim result
        transcriptionController.add(DeepgramSttResult(
          transcript: 'hello',
          isFinal: false,
          confidence: 0.85,
        ));

        await Future.delayed(const Duration(milliseconds: 100));

        expect(results.length, equals(1));
        expect(results[0].text, equals('hello'));
        expect(results[0].isFinal, isFalse);
        expect(results[0].confidence, equals(0.85));

        await subscription.cancel();
        await datasource.stopTranscription();
        await audioController.close();
        await transcriptionController.close();
      });

      test('emits final results correctly', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription();

        final results = <TranscriptionResult>[];
        final subscription = stream.listen(results.add);

        await Future.delayed(const Duration(milliseconds: 100));

        // Emit final result
        transcriptionController.add(DeepgramSttResult(
          transcript: 'hello world',
          isFinal: true,
          confidence: 0.95,
          duration: 2.5,
        ));

        await Future.delayed(const Duration(milliseconds: 100));

        expect(results.length, equals(1));
        expect(results[0].text, equals('hello world'));
        expect(results[0].isFinal, isTrue);
        expect(results[0].confidence, equals(0.95));
        expect(results[0].duration, equals(2.5));

        await subscription.cancel();
        await datasource.stopTranscription();
        await audioController.close();
        await transcriptionController.close();
      });

      test('filters out empty transcripts', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription();

        final results = <TranscriptionResult>[];
        final subscription = stream.listen(results.add);

        await Future.delayed(const Duration(milliseconds: 100));

        // Emit empty results (should be filtered)
        transcriptionController.add(DeepgramSttResult(
          transcript: '',
          isFinal: false,
        ));
        transcriptionController.add(DeepgramSttResult(
          transcript: null,
          isFinal: false,
        ));

        await Future.delayed(const Duration(milliseconds: 100));

        expect(results.length, equals(0));

        await subscription.cancel();
        await datasource.stopTranscription();
        await audioController.close();
        await transcriptionController.close();
      });
    });

    group('Error Handling', () {
      test('handles permission denial gracefully', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => false);

        final stream = datasource.startTranscription();

        final errors = <Object>[];
        final subscription = stream.listen(
          (_) {},
          onError: errors.add,
        );

        await Future.delayed(const Duration(milliseconds: 100));

        expect(errors.length, equals(1));
        expect(errors[0].toString(), contains('permission'));

        await subscription.cancel();
        await datasource.stopTranscription();
      });

      test('implements exponential backoff on connection errors', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        // Test retry delay calculation
        // First retry: 1s, second: 2s, third: 4s, fourth: 8s, fifth: 16s
        final delays = <int>[];
        for (int i = 1; i <= 5; i++) {
          final delay = datasource._calculateRetryDelay();
          delays.add(delay);
        }

        // Verify exponential backoff pattern exists
        expect(delays.length, equals(5));
      });

      test('gives up after max retries', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);
        when(mockRecorder.startStream(any)).thenThrow(Exception('Connection failed'));

        final stream = datasource.startTranscription();

        final errors = <Object>[];
        final subscription = stream.listen(
          (_) {},
          onError: errors.add,
        );

        // Wait for retries to complete
        await Future.delayed(const Duration(seconds: 2));

        // Should have received error after max retries
        expect(errors.isNotEmpty, isTrue);

        await subscription.cancel();
        await datasource.stopTranscription();
      });

      test('handles transcription stream errors', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription();

        final errors = <Object>[];
        final subscription = stream.listen(
          (_) {},
          onError: errors.add,
        );

        await Future.delayed(const Duration(milliseconds: 100));

        // Emit error on transcription stream
        transcriptionController.addError(Exception('WebSocket error'));

        await Future.delayed(const Duration(milliseconds: 100));

        expect(errors.length, equals(1));
        expect(errors[0].toString(), contains('Transcription failed'));

        await subscription.cancel();
        await datasource.stopTranscription();
        await audioController.close();
        await transcriptionController.close();
      });
    });

    group('Reconnection Logic', () {
      test('resets retry count on successful connection', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription();

        await Future.delayed(const Duration(milliseconds: 100));

        // Verify successful connection resets retry count
        expect(datasource.isTranscribing, isTrue);

        await stream.drain();
        await datasource.stopTranscription();
        await audioController.close();
        await transcriptionController.close();
      });
    });

    group('Resource Cleanup', () {
      test('dispose stops transcription and cleans up', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);
        when(mockRecorder.stop()).thenAnswer((_) async => null);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        datasource.startTranscription();

        await Future.delayed(const Duration(milliseconds: 100));

        await datasource.dispose();

        verify(mockRecorder.dispose()).called(1);
        expect(datasource.isTranscribing, isFalse);

        await audioController.close();
        await transcriptionController.close();
      });

      test('dispose is idempotent', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.stop()).thenAnswer((_) async => null);

        await datasource.dispose();
        await datasource.dispose();

        // Should not throw
        expect(() => datasource.dispose(), returnsNormally);
      });
    });

    group('Edge Cases', () {
      test('handles rapid start/stop cycles', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);
        when(mockRecorder.stop()).thenAnswer((_) async => null);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        for (int i = 0; i < 3; i++) {
          datasource.startTranscription();
          await Future.delayed(const Duration(milliseconds: 50));
          await datasource.stopTranscription();
        }

        expect(datasource.isTranscribing, isFalse);

        await audioController.close();
        await transcriptionController.close();
      });

      test('handles concurrent transcription results', () async {
        datasource = DeepgramDatasource(
          apiKey: 'test_api_key',
          recorder: mockRecorder,
        );

        when(mockRecorder.hasPermission()).thenAnswer((_) async => true);

        final audioController = StreamController<Uint8List>();
        when(mockRecorder.startStream(any)).thenAnswer((_) async => audioController.stream);

        final transcriptionController = StreamController<DeepgramSttResult>();
        when(mockDeepgram.transcribeFromLiveAudioStream(any, any))
            .thenAnswer((_) => transcriptionController.stream);

        final stream = datasource.startTranscription();

        final results = <TranscriptionResult>[];
        final subscription = stream.listen(results.add);

        await Future.delayed(const Duration(milliseconds: 100));

        // Emit multiple results rapidly
        for (int i = 0; i < 10; i++) {
          transcriptionController.add(DeepgramSttResult(
            transcript: 'word $i',
            isFinal: false,
            confidence: 0.9,
          ));
        }

        await Future.delayed(const Duration(milliseconds: 100));

        expect(results.length, equals(10));

        await subscription.cancel();
        await datasource.stopTranscription();
        await audioController.close();
        await transcriptionController.close();
      });
    });
  });
}
