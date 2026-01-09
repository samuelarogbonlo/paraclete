import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:dio/dio.dart';
import 'package:paraclete/features/voice/data/datasources/elevenlabs_datasource.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';

@GenerateMocks([Dio, Response, ResponseBody])
import 'elevenlabs_datasource_test.mocks.dart';

void main() {
  group('ElevenLabsDatasource', () {
    late MockDio mockDio;
    late ElevenLabsDatasource datasource;

    setUp(() {
      mockDio = MockDio();
      datasource = ElevenLabsDatasource(dio: mockDio);
    });

    tearDown(() {
      datasource.dispose();
    });

    group('Speech Synthesis (Non-Streaming)', () {
      test('synthesizeSpeech returns valid VoiceOutput', () async {
        final audioData = Uint8List.fromList(List.generate(16000, (i) => i % 256));

        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn(audioData);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final result = await datasource.synthesizeSpeech(
          text: 'Hello world',
          apiKey: 'test_api_key',
        );

        expect(result, isA<VoiceOutput>());
        expect(result.text, equals('Hello world'));
        expect(result.audioData, equals(audioData));
        expect(result.status, equals(VoiceOutputStatus.pending));
        expect(result.voiceId, isNotEmpty);
        expect(result.duration, isA<Duration>());

        verify(mockDio.post<List<int>>(
          contains('/text-to-speech/'),
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).called(1);
      });

      test('uses default voice ID when not specified', () async {
        final audioData = Uint8List.fromList([1, 2, 3]);

        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn(audioData);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final result = await datasource.synthesizeSpeech(
          text: 'Test',
          apiKey: 'test_api_key',
        );

        verify(mockDio.post<List<int>>(
          contains('EXAVITQu4vr4xnSDxMaL'), // Default voice ID
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).called(1);
      });

      test('uses custom voice ID when specified', () async {
        final audioData = Uint8List.fromList([1, 2, 3]);

        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn(audioData);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        await datasource.synthesizeSpeech(
          text: 'Test',
          apiKey: 'test_api_key',
          voiceId: 'custom_voice_id',
        );

        verify(mockDio.post<List<int>>(
          contains('custom_voice_id'),
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).called(1);
      });

      test('passes correct headers and model', () async {
        final audioData = Uint8List.fromList([1, 2, 3]);

        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn(audioData);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        await datasource.synthesizeSpeech(
          text: 'Test',
          apiKey: 'my_secret_key',
          model: 'eleven_turbo_v2',
        );

        final captured = verify(mockDio.post<List<int>>(
          any,
          data: captureAnyNamed('data'),
          options: anyNamed('options'),
        )).captured;

        final requestData = captured[0] as Map<String, dynamic>;
        expect(requestData['text'], equals('Test'));
        expect(requestData['model_id'], equals('eleven_turbo_v2'));
        expect(requestData['voice_settings'], isA<Map>());
      });

      test('throws exception for empty audio data', () async {
        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn([]);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        expect(
          () => datasource.synthesizeSpeech(
            text: 'Test',
            apiKey: 'test_api_key',
          ),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Empty audio data'),
          )),
        );
      });

      test('throws exception for null audio data', () async {
        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn(null);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        expect(
          () => datasource.synthesizeSpeech(
            text: 'Test',
            apiKey: 'test_api_key',
          ),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('Empty audio data'),
          )),
        );
      });

      test('handles API errors gracefully', () async {
        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenThrow(DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.connectionTimeout,
          message: 'Connection timeout',
        ));

        expect(
          () => datasource.synthesizeSpeech(
            text: 'Test',
            apiKey: 'test_api_key',
          ),
          throwsA(isA<DioException>()),
        );
      });

      test('estimates duration correctly', () async {
        // 16KB should estimate to ~1 second at 128kbps
        final audioData = Uint8List.fromList(List.generate(16000, (i) => i % 256));

        final mockResponse = MockResponse<List<int>>();
        when(mockResponse.data).thenReturn(audioData);

        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final result = await datasource.synthesizeSpeech(
          text: 'Test',
          apiKey: 'test_api_key',
        );

        expect(result.duration.inMilliseconds, greaterThan(900));
        expect(result.duration.inMilliseconds, lessThan(1100));
      });
    });

    group('Speech Synthesis (Streaming)', () {
      test('streamSynthesizedSpeech yields audio chunks', () async {
        final mockResponseBody = MockResponseBody();
        final audioChunks = [
          Uint8List.fromList([1, 2, 3]),
          Uint8List.fromList([4, 5, 6]),
          Uint8List.fromList([7, 8, 9]),
        ];

        final streamController = StreamController<List<int>>();
        when(mockResponseBody.stream).thenAnswer((_) => streamController.stream);

        final mockResponse = MockResponse<ResponseBody>();
        when(mockResponse.data).thenReturn(mockResponseBody);

        when(mockDio.post<ResponseBody>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final streamFuture = datasource
            .streamSynthesizedSpeech(
              text: 'Test streaming',
              apiKey: 'test_api_key',
            )
            .toList();

        // Emit chunks
        for (final chunk in audioChunks) {
          streamController.add(chunk);
        }
        await streamController.close();

        final results = await streamFuture;

        expect(results.length, equals(3));
        expect(results[0], equals(audioChunks[0]));
        expect(results[1], equals(audioChunks[1]));
        expect(results[2], equals(audioChunks[2]));
      });

      test('filters out empty chunks', () async {
        final mockResponseBody = MockResponseBody();

        final streamController = StreamController<List<int>>();
        when(mockResponseBody.stream).thenAnswer((_) => streamController.stream);

        final mockResponse = MockResponse<ResponseBody>();
        when(mockResponse.data).thenReturn(mockResponseBody);

        when(mockDio.post<ResponseBody>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final streamFuture = datasource
            .streamSynthesizedSpeech(
              text: 'Test',
              apiKey: 'test_api_key',
            )
            .toList();

        // Emit chunks with empty ones
        streamController.add([1, 2, 3]);
        streamController.add([]); // Should be filtered
        streamController.add([4, 5, 6]);
        await streamController.close();

        final results = await streamFuture;

        expect(results.length, equals(2));
        expect(results[0], equals([1, 2, 3]));
        expect(results[1], equals([4, 5, 6]));
      });

      test('throws exception for null stream', () async {
        final mockResponse = MockResponse<ResponseBody>();
        when(mockResponse.data).thenReturn(null);

        when(mockDio.post<ResponseBody>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        expect(
          () => datasource
              .streamSynthesizedSpeech(
                text: 'Test',
                apiKey: 'test_api_key',
              )
              .toList(),
          throwsA(isA<Exception>().having(
            (e) => e.toString(),
            'message',
            contains('No stream received'),
          )),
        );
      });

      test('uses streaming endpoint', () async {
        final mockResponseBody = MockResponseBody();
        final streamController = StreamController<List<int>>();
        when(mockResponseBody.stream).thenAnswer((_) => streamController.stream);

        final mockResponse = MockResponse<ResponseBody>();
        when(mockResponse.data).thenReturn(mockResponseBody);

        when(mockDio.post<ResponseBody>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final streamFuture = datasource
            .streamSynthesizedSpeech(
              text: 'Test',
              apiKey: 'test_api_key',
            )
            .toList();

        await streamController.close();
        await streamFuture;

        verify(mockDio.post<ResponseBody>(
          contains('/stream'),
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).called(1);
      });
    });

    group('Voice Management', () {
      test('getVoices returns list of voices', () async {
        final mockVoices = [
          {'voice_id': 'voice1', 'name': 'Voice 1'},
          {'voice_id': 'voice2', 'name': 'Voice 2'},
        ];

        final mockResponse = MockResponse<Map<String, dynamic>>();
        when(mockResponse.data).thenReturn({'voices': mockVoices});

        when(mockDio.get(
          any,
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final voices = await datasource.getVoices(apiKey: 'test_api_key');

        expect(voices.length, equals(2));
        expect(voices[0]['voice_id'], equals('voice1'));
        expect(voices[1]['voice_id'], equals('voice2'));

        verify(mockDio.get(
          '/voices',
          options: anyNamed('options'),
        )).called(1);
      });

      test('getUserInfo returns user subscription info', () async {
        final mockUserInfo = {
          'subscription': {'tier': 'free'},
          'character_count': 1000,
          'character_limit': 10000,
        };

        final mockResponse = MockResponse<Map<String, dynamic>>();
        when(mockResponse.data).thenReturn(mockUserInfo);

        when(mockDio.get(
          any,
          options: anyNamed('options'),
        )).thenAnswer((_) async => mockResponse);

        final userInfo = await datasource.getUserInfo(apiKey: 'test_api_key');

        expect(userInfo['subscription'], isNotNull);
        expect(userInfo['character_count'], equals(1000));

        verify(mockDio.get(
          '/user',
          options: anyNamed('options'),
        )).called(1);
      });
    });

    group('Error Handling', () {
      test('handles 401 authentication error', () async {
        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenThrow(DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 401,
          ),
        ));

        expect(
          () => datasource.synthesizeSpeech(
            text: 'Test',
            apiKey: 'invalid_key',
          ),
          throwsA(isA<DioException>()),
        );
      });

      test('handles 429 rate limit error', () async {
        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenThrow(DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/test'),
            statusCode: 429,
          ),
        ));

        expect(
          () => datasource.synthesizeSpeech(
            text: 'Test',
            apiKey: 'test_api_key',
          ),
          throwsA(isA<DioException>()),
        );
      });

      test('handles network timeout', () async {
        when(mockDio.post<List<int>>(
          any,
          data: anyNamed('data'),
          options: anyNamed('options'),
        )).thenThrow(DioException(
          requestOptions: RequestOptions(path: '/test'),
          type: DioExceptionType.connectionTimeout,
        ));

        expect(
          () => datasource.synthesizeSpeech(
            text: 'Test',
            apiKey: 'test_api_key',
          ),
          throwsA(isA<DioException>()),
        );
      });
    });

    group('Resource Cleanup', () {
      test('dispose closes Dio client', () {
        datasource.dispose();

        verify(mockDio.close()).called(1);
      });

      test('dispose is idempotent', () {
        datasource.dispose();
        datasource.dispose();

        // Should not throw and close should be called multiple times
        verify(mockDio.close()).called(2);
      });
    });
  });
}
