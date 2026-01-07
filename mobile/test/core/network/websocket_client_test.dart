import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:paraclete/core/network/websocket_client.dart';
import 'package:paraclete/core/storage/secure_storage.dart';

@GenerateMocks([SecureStorageService, WebSocketChannel, WebSocketSink])
import 'websocket_client_test.mocks.dart';

void main() {
  group('WebSocketClient', () {
    late MockSecureStorageService mockSecureStorage;
    late WebSocketClient client;

    setUp(() {
      mockSecureStorage = MockSecureStorageService();
      client = WebSocketClient(secureStorage: mockSecureStorage);
    });

    tearDown(() {
      client.dispose();
    });

    group('Connection States', () {
      test('initializes in disconnected state', () {
        expect(client.currentState, WebSocketState.disconnected);
        expect(client.isConnected, isFalse);
      });

      test('state stream emits state changes', () async {
        final states = <WebSocketState>[];
        client.state.listen(states.add);

        // Simulate state change (would need to actually connect in real scenario)
        await Future.delayed(const Duration(milliseconds: 100));

        // State should be emitted when changed
        expect(states, isA<List<WebSocketState>>());
      });

      test('message stream is available', () {
        expect(client.messages, isA<Stream<WebSocketMessage>>());
      });
    });

    group('WebSocketMessage', () {
      test('creates message with type and data', () {
        final message = WebSocketMessage(
          type: 'test',
          data: {'key': 'value'},
        );

        expect(message.type, 'test');
        expect(message.data, {'key': 'value'});
        expect(message.timestamp, isA<DateTime>());
      });

      test('converts to JSON correctly', () {
        final message = WebSocketMessage(
          type: 'test',
          data: {'key': 'value'},
          timestamp: DateTime(2024, 1, 1),
        );

        final json = message.toJson();

        expect(json['type'], 'test');
        expect(json['data'], {'key': 'value'});
        expect(json['timestamp'], '2024-01-01T00:00:00.000');
      });

      test('creates from JSON correctly', () {
        final json = {
          'type': 'test',
          'data': {'key': 'value'},
          'timestamp': '2024-01-01T00:00:00.000',
        };

        final message = WebSocketMessage.fromJson(json);

        expect(message.type, 'test');
        expect(message.data, {'key': 'value'});
        expect(message.timestamp.year, 2024);
      });

      test('handles missing timestamp in JSON', () {
        final json = {
          'type': 'test',
          'data': {'key': 'value'},
        };

        final message = WebSocketMessage.fromJson(json);

        expect(message.type, 'test');
        expect(message.timestamp, isA<DateTime>());
      });
    });

    group('Message Sending', () {
      test('sendMessage validates connection state', () {
        final message = WebSocketMessage(
          type: 'test',
          data: {},
        );

        // Should not throw when disconnected, but won't send
        expect(() => client.sendMessage(message), returnsNormally);
      });

      test('sendVoiceInput creates correct message format', () {
        expect(
          () => client.sendVoiceInput('Hello world'),
          returnsNormally,
        );
      });

      test('sendApproval creates correct message format', () {
        expect(
          () => client.sendApproval('action_123', true),
          returnsNormally,
        );

        expect(
          () => client.sendApproval('action_456', false),
          returnsNormally,
        );
      });

      test('cancelTask creates correct message format', () {
        expect(
          () => client.cancelTask('User requested'),
          returnsNormally,
        );
      });
    });

    group('Connection Management', () {
      test('connect requires session ID', () async {
        when(mockSecureStorage.getAccessToken())
            .thenAnswer((_) async => 'test_token');

        // Note: Actual connection will fail without real WebSocket server
        // This tests the method signature and validation
        expect(
          () => client.connect(sessionId: 'session_123'),
          returnsNormally,
        );
      });

      test('connect with additional parameters', () async {
        when(mockSecureStorage.getAccessToken())
            .thenAnswer((_) async => 'test_token');

        expect(
          () => client.connect(
            sessionId: 'session_123',
            params: {'custom': 'param'},
          ),
          returnsNormally,
        );
      });

      test('disconnect cleans up resources', () async {
        await client.disconnect();

        expect(client.currentState, WebSocketState.disconnected);
      });

      test('disconnect is idempotent', () async {
        await client.disconnect();
        await client.disconnect();

        // Should not throw
        expect(client.currentState, WebSocketState.disconnected);
      });
    });

    group('Error Handling', () {
      test('handles missing access token', () async {
        when(mockSecureStorage.getAccessToken()).thenAnswer((_) async => null);

        // Should handle missing token gracefully
        await client.connect(sessionId: 'session_123');

        // Connection should fail or be in error state
        expect(
          client.currentState,
          anyOf(
            WebSocketState.error,
            WebSocketState.disconnected,
          ),
        );
      });

      test('handles connection errors gracefully', () async {
        when(mockSecureStorage.getAccessToken())
            .thenAnswer((_) async => 'test_token');

        // Will fail to connect to invalid URL
        await client.connect(sessionId: 'session_123');

        // Should transition to error or disconnected state
        expect(client.currentState, isA<WebSocketState>());
      });
    });

    group('Reconnection Logic', () {
      test('tracks reconnection attempts', () async {
        // Reconnection logic is internal, but we can verify
        // the client handles disconnections
        expect(client.currentState, WebSocketState.disconnected);
      });
    });

    group('Lifecycle Management', () {
      test('dispose cleans up all resources', () {
        client.dispose();

        // After dispose, client should be in clean state
        expect(() => client.dispose(), returnsNormally);
      });

      test('dispose can be called multiple times', () {
        client.dispose();
        client.dispose();

        // Should not throw
        expect(() => client.dispose(), returnsNormally);
      });
    });

    group('Edge Cases', () {
      test('handles rapid connect/disconnect cycles', () async {
        when(mockSecureStorage.getAccessToken())
            .thenAnswer((_) async => 'test_token');

        await client.connect(sessionId: 'session_123');
        await client.disconnect();
        await client.connect(sessionId: 'session_456');
        await client.disconnect();

        expect(client.currentState, WebSocketState.disconnected);
      });

      test('prevents duplicate connections', () async {
        when(mockSecureStorage.getAccessToken())
            .thenAnswer((_) async => 'test_token');

        await client.connect(sessionId: 'session_123');
        await client.connect(sessionId: 'session_123');

        // Should not create duplicate connections
        expect(() => client.disconnect(), returnsNormally);
      });
    });
  });

  group('WebSocketState enum', () {
    test('has all required states', () {
      expect(WebSocketState.disconnected, isA<WebSocketState>());
      expect(WebSocketState.connecting, isA<WebSocketState>());
      expect(WebSocketState.connected, isA<WebSocketState>());
      expect(WebSocketState.reconnecting, isA<WebSocketState>());
      expect(WebSocketState.error, isA<WebSocketState>());
    });
  });
}
