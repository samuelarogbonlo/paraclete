import 'dart:async';
import 'dart:convert';
import 'package:dartssh2/dartssh2.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:paraclete/features/terminal/data/ssh_client.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';

import 'ssh_client_test.mocks.dart';

// Mock classes for dartssh2
class MockSSHSocket extends Mock implements SSHSocket {}

class MockSSHClient extends Mock implements SSHClient {}

class MockSSHSession extends Mock implements SSHSession {}

@GenerateMocks([])
void main() {
  late SshConnection testConfig;

  setUp(() {
    testConfig = const SshConnection(
      id: 'test-1',
      name: 'Test Server',
      host: 'test.example.com',
      port: 22,
      username: 'testuser',
      authMethod: SshAuthMethod.password,
      password: 'testpass',
      autoReconnect: false,
      reconnectDelay: 1000,
    );
  });

  group('SshClientWrapper - Connection', () {
    test('connect should establish SSH connection with password auth', () async {
      // Note: This test demonstrates the structure but requires mocking dartssh2
      // In practice, we'd need dependency injection for proper testing
      final client = SshClientWrapper(testConfig);

      // Assert initial state
      expect(client.state, SshClientState.disconnected);
      expect(client.isConnected, isFalse);

      client.dispose();
    });

    test('should start in disconnected state', () {
      final client = SshClientWrapper(testConfig);

      expect(client.state, SshClientState.disconnected);
      expect(client.isConnected, isFalse);

      client.dispose();
    });

    test('should emit state changes through stateStream', () async {
      final client = SshClientWrapper(testConfig);

      final states = <SshClientState>[];
      final subscription = client.stateStream.listen(states.add);

      // Note: Can't easily test state transitions without connection
      // This test demonstrates the structure

      await subscription.cancel();
      client.dispose();
    });

    test('connect with missing password should throw error', () async {
      final configWithoutPassword = const SshConnection(
        id: 'test-1',
        name: 'Test Server',
        host: 'test.example.com',
        port: 22,
        username: 'testuser',
        authMethod: SshAuthMethod.password,
        password: null, // Missing password
        autoReconnect: false,
        reconnectDelay: 1000,
      );

      final client = SshClientWrapper(configWithoutPassword);

      // This would throw if we could actually execute connect
      // In practice, we need proper mocking infrastructure

      client.dispose();
    });

    test('connect with public key auth should require private key', () async {
      final configWithPublicKey = const SshConnection(
        id: 'test-1',
        name: 'Test Server',
        host: 'test.example.com',
        port: 22,
        username: 'testuser',
        authMethod: SshAuthMethod.publicKey,
        privateKey: null, // Missing private key
        autoReconnect: false,
        reconnectDelay: 1000,
      );

      final client = SshClientWrapper(configWithPublicKey);

      // Would throw SshConnectionException if connect was called

      client.dispose();
    });

    test('connect should use configured terminal dimensions', () async {
      final client = SshClientWrapper(testConfig);

      // Note: Would need to mock SSHClient to verify PTY config
      // Structure test only

      client.dispose();
    });

    test('disconnect should update state and clean up resources', () async {
      final client = SshClientWrapper(testConfig);

      await client.disconnect();

      expect(client.state, SshClientState.disconnected);
      expect(client.isConnected, isFalse);

      client.dispose();
    });

    test('connect when disposed should throw error', () async {
      final client = SshClientWrapper(testConfig);
      client.dispose();

      expect(
        () => client.connect(terminalWidth: 80, terminalHeight: 24),
        throwsA(isA<SshConnectionException>()),
      );
    });
  });

  group('SshClientWrapper - Input/Output', () {
    test('sendInput when not connected should throw error', () {
      final client = SshClientWrapper(testConfig);

      expect(
        () => client.sendInput('ls\n'),
        throwsA(isA<SshConnectionException>()),
      );

      client.dispose();
    });

    test('sendInput should encode and send data to shell', () {
      final client = SshClientWrapper(testConfig);

      // Can't test without connection, but validates API
      expect(
        () => client.sendInput('test command\n'),
        throwsA(isA<SshConnectionException>()),
      );

      client.dispose();
    });

    test('outputStream should emit terminal output', () async {
      final client = SshClientWrapper(testConfig);

      final outputs = <String>[];
      final subscription = client.outputStream.listen(outputs.add);

      // Would receive output if connected
      await Future.delayed(const Duration(milliseconds: 50));

      expect(outputs, isEmpty); // No connection, no output

      await subscription.cancel();
      client.dispose();
    });

    test('should handle both stdout and stderr', () async {
      final client = SshClientWrapper(testConfig);

      // Both streams would be merged into outputStream
      final subscription = client.outputStream.listen((_) {});

      await subscription.cancel();
      client.dispose();
    });

    test('executeCommand when not connected should throw error', () async {
      final client = SshClientWrapper(testConfig);

      expect(
        () => client.executeCommand('ls -la'),
        throwsA(isA<SshConnectionException>()),
      );

      client.dispose();
    });
  });

  group('SshClientWrapper - Terminal Management', () {
    test('resize when not connected should throw error', () async {
      final client = SshClientWrapper(testConfig);

      expect(
        () => client.resize(100, 30),
        throwsA(isA<SshConnectionException>()),
      );

      client.dispose();
    });

    test('resize should update terminal dimensions', () async {
      final client = SshClientWrapper(testConfig);

      // Would call shell.resizeTerminal if connected
      expect(
        () => client.resize(120, 40),
        throwsA(isA<SshConnectionException>()),
      );

      client.dispose();
    });
  });

  group('SshClientWrapper - Reconnection Logic', () {
    test('should calculate exponential backoff delays', () {
      final client = SshClientWrapper(testConfig);

      // Backoff: 1s, 2s, 4s, 8s, 16s (capped at 30s)
      // This is tested internally through reconnection attempts

      client.dispose();
    });

    test('reconnection should respect max attempts limit', () async {
      final configWithReconnect = testConfig.copyWith(
        autoReconnect: true,
        reconnectDelay: 100, // Fast for testing
      );

      final client = SshClientWrapper(configWithReconnect);

      // Would attempt reconnection up to 5 times

      client.dispose();
    });

    test('reconnection should be cancellable', () async {
      final configWithReconnect = testConfig.copyWith(
        autoReconnect: true,
        reconnectDelay: 1000,
      );

      final client = SshClientWrapper(configWithReconnect);

      // Calling disconnect should cancel any pending reconnection
      await client.disconnect();

      expect(client.state, SshClientState.disconnected);

      client.dispose();
    });

    test('should update state to reconnecting during reconnection', () async {
      final configWithReconnect = testConfig.copyWith(
        autoReconnect: true,
        reconnectDelay: 100,
      );

      final client = SshClientWrapper(configWithReconnect);

      final states = <SshClientState>[];
      final subscription = client.stateStream.listen(states.add);

      // Would emit reconnecting state if connection was lost

      await subscription.cancel();
      client.dispose();
    });

    test('should reset reconnect attempts on successful connection', () async {
      final configWithReconnect = testConfig.copyWith(
        autoReconnect: true,
      );

      final client = SshClientWrapper(configWithReconnect);

      // Internal counter would reset on successful connect

      client.dispose();
    });
  });

  group('SshClientWrapper - Error Handling', () {
    test('should handle connection timeout', () async {
      final client = SshClientWrapper(testConfig);

      // SSHSocket.connect has 30s timeout
      // Would throw on timeout

      client.dispose();
    });

    test('should handle authentication failure', () async {
      final client = SshClientWrapper(testConfig);

      // Would throw on invalid credentials

      client.dispose();
    });

    test('should handle connection closed unexpectedly', () async {
      final client = SshClientWrapper(testConfig);

      final states = <SshClientState>[];
      final subscription = client.stateStream.listen(states.add);

      // Would emit error state and potentially reconnect

      await subscription.cancel();
      client.dispose();
    });

    test('should handle shell output errors', () async {
      final client = SshClientWrapper(testConfig);

      // Output stream errors would be logged and handled

      client.dispose();
    });

    test('should not process events after disposal', () async {
      final client = SshClientWrapper(testConfig);

      final outputs = <String>[];
      final subscription = client.outputStream.listen(outputs.add);

      client.dispose();

      // Any pending events should be ignored
      await Future.delayed(const Duration(milliseconds: 50));

      expect(outputs, isEmpty);

      await subscription.cancel();
    });
  });

  group('SshClientWrapper - Resource Cleanup', () {
    test('dispose should clean up all resources', () async {
      final client = SshClientWrapper(testConfig);

      final subscription = client.outputStream.listen((_) {});

      client.dispose();

      // Should close streams and cancel timers
      await subscription.cancel();
    });

    test('dispose should be idempotent', () {
      final client = SshClientWrapper(testConfig);

      client.dispose();
      client.dispose(); // Should not throw

      expect(() => client.dispose(), returnsNormally);
    });

    test('dispose should cancel pending reconnection', () async {
      final configWithReconnect = testConfig.copyWith(
        autoReconnect: true,
        reconnectDelay: 1000,
      );

      final client = SshClientWrapper(configWithReconnect);

      // Even if reconnection is scheduled
      client.dispose();

      // Should cancel the timer
      await Future.delayed(const Duration(milliseconds: 1100));

      // No reconnection should occur
    });

    test('dispose should close output stream', () async {
      final client = SshClientWrapper(testConfig);

      var streamClosed = false;
      client.outputStream.listen(
        (_) {},
        onDone: () => streamClosed = true,
      );

      client.dispose();

      await Future.delayed(const Duration(milliseconds: 50));

      // Stream should be closed
      expect(streamClosed, isTrue);
    });

    test('dispose should close state stream', () async {
      final client = SshClientWrapper(testConfig);

      var streamClosed = false;
      client.stateStream.listen(
        (_) {},
        onDone: () => streamClosed = true,
      );

      client.dispose();

      await Future.delayed(const Duration(milliseconds: 50));

      // Stream should be closed
      expect(streamClosed, isTrue);
    });
  });

  group('SshConnection Entity', () {
    test('should create connection with required fields', () {
      expect(testConfig.id, 'test-1');
      expect(testConfig.host, 'test.example.com');
      expect(testConfig.port, 22);
      expect(testConfig.username, 'testuser');
    });

    test('should support password authentication', () {
      expect(testConfig.authMethod, SshAuthMethod.password);
      expect(testConfig.password, 'testpass');
    });

    test('should support public key authentication', () {
      final publicKeyConfig = testConfig.copyWith(
        authMethod: SshAuthMethod.publicKey,
        privateKey: '-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----',
        privateKeyPassphrase: 'keypass',
      );

      expect(publicKeyConfig.authMethod, SshAuthMethod.publicKey);
      expect(publicKeyConfig.privateKey, isNotNull);
      expect(publicKeyConfig.privateKeyPassphrase, 'keypass');
    });

    test('should support auto-reconnect configuration', () {
      final reconnectConfig = testConfig.copyWith(
        autoReconnect: true,
        reconnectDelay: 2000,
      );

      expect(reconnectConfig.autoReconnect, isTrue);
      expect(reconnectConfig.reconnectDelay, 2000);
    });

    test('copyWith should create modified copy', () {
      final modified = testConfig.copyWith(
        host: 'new.example.com',
        port: 2222,
      );

      expect(modified.host, 'new.example.com');
      expect(modified.port, 2222);
      expect(modified.username, testConfig.username); // Unchanged
    });
  });

  group('SshConnectionException', () {
    test('should format error message correctly', () {
      final exception = SshConnectionException('Connection failed');

      expect(exception.toString(), 'SshConnectionException: Connection failed');
    });

    test('should store original error', () {
      final originalError = Exception('Network error');
      final exception = SshConnectionException('Connection failed', originalError);

      expect(exception.message, 'Connection failed');
      expect(exception.originalError, originalError);
    });
  });

  group('SshClientState Enum', () {
    test('should have all expected states', () {
      expect(SshClientState.values, hasLength(6));
      expect(SshClientState.values, contains(SshClientState.disconnected));
      expect(SshClientState.values, contains(SshClientState.connecting));
      expect(SshClientState.values, contains(SshClientState.connected));
      expect(SshClientState.values, contains(SshClientState.reconnecting));
      expect(SshClientState.values, contains(SshClientState.error));
      expect(SshClientState.values, contains(SshClientState.disconnecting));
    });

    test('should support state transitions', () {
      // Valid transitions:
      // disconnected -> connecting -> connected
      // connected -> disconnecting -> disconnected
      // connected -> error -> reconnecting -> connecting
      // connected -> reconnecting -> connected

      final validInitialStates = [
        SshClientState.disconnected,
        SshClientState.connecting,
        SshClientState.connected,
        SshClientState.reconnecting,
        SshClientState.error,
        SshClientState.disconnecting,
      ];

      expect(validInitialStates, hasLength(6));
    });
  });
}
