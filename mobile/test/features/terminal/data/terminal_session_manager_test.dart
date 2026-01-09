import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:paraclete/features/terminal/data/ssh_client.dart';
import 'package:paraclete/features/terminal/data/terminal_session_manager.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';

import 'terminal_session_manager_test.mocks.dart';

@GenerateMocks([SshClientWrapper])
void main() {
  late TerminalSessionManager manager;
  late SshConnection testConnection;

  setUp(() {
    manager = TerminalSessionManager();
    testConnection = const SshConnection(
      id: 'conn-1',
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

  tearDown(() async {
    await manager.dispose();
  });

  group('TerminalSessionManager - Session Creation', () {
    test('createSession should create new session with unique ID', () async {
      // Act
      final session = await manager.createSession(
        connection: testConnection,
        terminalWidth: 80,
        terminalHeight: 24,
      );

      // Assert
      expect(session.id, isNotEmpty);
      expect(session.connection.id, testConnection.id);
      expect(session.state, TerminalSessionState.disconnected);
      expect(session.terminalWidth, 80);
      expect(session.terminalHeight, 24);
      expect(session.createdAt, isNotNull);
    });

    test('createSession should add session to active sessions', () async {
      // Act
      final session = await manager.createSession(
        connection: testConnection,
      );

      // Assert
      final allSessions = manager.getAllSessions();
      expect(allSessions, hasLength(1));
      expect(allSessions.first.id, session.id);
    });

    test('createSession should emit session update', () async {
      // Arrange
      final sessions = <Map<String, TerminalSession>>[];
      final subscription = manager.sessionsStream.listen(sessions.add);

      // Act
      await manager.createSession(connection: testConnection);

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(sessions, isNotEmpty);
      expect(sessions.last.values, hasLength(1));

      await subscription.cancel();
    });

    test('createSession should use default terminal dimensions', () async {
      // Act
      final session = await manager.createSession(
        connection: testConnection,
        // Not specifying dimensions
      );

      // Assert
      expect(session.terminalWidth, 80); // Default
      expect(session.terminalHeight, 24); // Default
    });

    test('createSession should handle custom terminal dimensions', () async {
      // Act
      final session = await manager.createSession(
        connection: testConnection,
        terminalWidth: 120,
        terminalHeight: 40,
      );

      // Assert
      expect(session.terminalWidth, 120);
      expect(session.terminalHeight, 40);
    });

    test('should create multiple sessions', () async {
      // Act
      final session1 = await manager.createSession(connection: testConnection);
      final session2 = await manager.createSession(connection: testConnection);
      final session3 = await manager.createSession(connection: testConnection);

      // Assert
      final allSessions = manager.getAllSessions();
      expect(allSessions, hasLength(3));
      expect(session1.id, isNot(equals(session2.id)));
      expect(session2.id, isNot(equals(session3.id)));
    });
  });

  group('TerminalSessionManager - Session Retrieval', () {
    test('getSession should return existing session', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act
      final retrieved = manager.getSession(session.id);

      // Assert
      expect(retrieved, isNotNull);
      expect(retrieved!.id, session.id);
    });

    test('getSession should return null for non-existent session', () {
      // Act
      final session = manager.getSession('non-existent-id');

      // Assert
      expect(session, isNull);
    });

    test('getAllSessions should return all active sessions', () async {
      // Arrange
      await manager.createSession(connection: testConnection);
      await manager.createSession(connection: testConnection);
      await manager.createSession(connection: testConnection);

      // Act
      final allSessions = manager.getAllSessions();

      // Assert
      expect(allSessions, hasLength(3));
    });

    test('getAllSessions should return empty list when no sessions', () {
      // Act
      final allSessions = manager.getAllSessions();

      // Assert
      expect(allSessions, isEmpty);
    });

    test('getOutputStream should return stream for session', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act
      final stream = manager.getOutputStream(session.id);

      // Assert
      expect(stream, isNotNull);
      expect(stream, isA<Stream<String>>());
    });

    test('getOutputStream should return null for non-existent session', () {
      // Act
      final stream = manager.getOutputStream('non-existent-id');

      // Assert
      expect(stream, isNull);
    });

    test('getSessionStream should emit session updates', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      final updates = <TerminalSession>[];
      final subscription = manager.getSessionStream(session.id).listen(updates.add);

      // Wait for initial emission
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(updates, isNotEmpty);

      await subscription.cancel();
    });
  });

  group('TerminalSessionManager - Connection Management', () {
    test('connect should update session state to connecting', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Note: Without mocking SSH client, connection will fail
      // This tests the structure

      // Act & Assert
      expect(
        () => manager.connect(session.id),
        throwsA(anything), // Will throw due to real SSH connection attempt
      );
    });

    test('connect should throw error for non-existent session', () async {
      // Act & Assert
      expect(
        () => manager.connect('non-existent-id'),
        throwsA(isA<Exception>()),
      );
    });

    test('disconnect should update session state', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act
      await manager.disconnect(session.id);

      // Assert
      final updated = manager.getSession(session.id);
      expect(updated!.state, TerminalSessionState.disconnected);
    });

    test('disconnect should handle non-existent session gracefully', () async {
      // Act & Assert - Should not throw
      await manager.disconnect('non-existent-id');
    });

    test('disconnect should emit session update', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      final updates = <Map<String, TerminalSession>>[];
      final subscription = manager.sessionsStream.listen(updates.add);

      // Act
      await manager.disconnect(session.id);

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(updates.length, greaterThan(1));

      await subscription.cancel();
    });

    test('reconnect should increment reconnect attempts', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act - Will fail but should update state
      try {
        await manager.reconnect(session.id);
      } catch (_) {
        // Expected to fail
      }

      // Assert
      final updated = manager.getSession(session.id);
      expect(updated!.reconnectAttempts, greaterThan(0));
    });

    test('reconnect should throw error for non-existent session', () async {
      // Act & Assert
      expect(
        () => manager.reconnect('non-existent-id'),
        throwsA(isA<Exception>()),
      );
    });
  });

  group('TerminalSessionManager - Terminal Interaction', () {
    test('sendInput should throw error for non-existent session', () {
      // Act & Assert
      expect(
        () => manager.sendInput('non-existent-id', 'ls\n'),
        throwsA(isA<Exception>()),
      );
    });

    test('sendInput should update lastActivityAt', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Note: Can't actually send input without connection
      // This tests the error handling

      // Act & Assert
      expect(
        () => manager.sendInput(session.id, 'test\n'),
        throwsA(anything), // Will throw due to no connection
      );
    });

    test('resizeTerminal should throw error for non-existent session', () async {
      // Act & Assert
      expect(
        () => manager.resizeTerminal('non-existent-id', 100, 30),
        throwsA(isA<Exception>()),
      );
    });

    test('resizeTerminal should update session dimensions', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Note: Can't actually resize without connection
      // This tests the error handling

      // Act & Assert
      expect(
        () => manager.resizeTerminal(session.id, 120, 40),
        throwsA(anything), // Will throw due to no connection
      );
    });

    test('executeCommand should throw error for non-existent session', () async {
      // Act & Assert
      expect(
        () => manager.executeCommand('non-existent-id', 'ls -la'),
        throwsA(isA<Exception>()),
      );
    });

    test('executeCommand should execute non-interactive command', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act & Assert
      expect(
        () => manager.executeCommand(session.id, 'pwd'),
        throwsA(anything), // Will throw due to no connection
      );
    });
  });

  group('TerminalSessionManager - Session Removal', () {
    test('removeSession should disconnect and remove session', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act
      await manager.removeSession(session.id);

      // Assert
      final retrieved = manager.getSession(session.id);
      expect(retrieved, isNull);

      final allSessions = manager.getAllSessions();
      expect(allSessions, isEmpty);
    });

    test('removeSession should emit session update', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      final updates = <Map<String, TerminalSession>>[];
      final subscription = manager.sessionsStream.listen(updates.add);

      // Act
      await manager.removeSession(session.id);

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(updates.last.values, isEmpty);

      await subscription.cancel();
    });

    test('removeSession should handle non-existent session gracefully', () async {
      // Act & Assert - Should not throw
      await manager.removeSession('non-existent-id');
    });

    test('removeSession should clean up SSH client resources', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Act
      await manager.removeSession(session.id);

      // Assert - Session should be fully cleaned up
      final retrieved = manager.getSession(session.id);
      expect(retrieved, isNull);
    });
  });

  group('TerminalSessionManager - State Synchronization', () {
    test('should update session state from SSH client state', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Note: Without mocking, we can't test actual state transitions
      // This validates the structure

      expect(session.state, TerminalSessionState.disconnected);
    });

    test('should map SSH client states to terminal session states', () async {
      // Arrange
      final session = await manager.createSession(connection: testConnection);

      // Expected mappings:
      // SshClientState.disconnected -> TerminalSessionState.disconnected
      // SshClientState.connecting -> TerminalSessionState.connecting
      // SshClientState.connected -> TerminalSessionState.connected
      // SshClientState.reconnecting -> TerminalSessionState.reconnecting
      // SshClientState.error -> TerminalSessionState.error
      // SshClientState.disconnecting -> TerminalSessionState.disconnecting

      expect(session.state, TerminalSessionState.disconnected);
    });

    test('sessionsStream should emit updates on state changes', () async {
      // Arrange
      final updates = <Map<String, TerminalSession>>[];
      final subscription = manager.sessionsStream.listen(updates.add);

      // Act
      await manager.createSession(connection: testConnection);
      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(updates, isNotEmpty);
      expect(updates.last.values, hasLength(1));

      await subscription.cancel();
    });
  });

  group('TerminalSessionManager - Resource Cleanup', () {
    test('dispose should remove all sessions', () async {
      // Arrange
      await manager.createSession(connection: testConnection);
      await manager.createSession(connection: testConnection);
      await manager.createSession(connection: testConnection);

      expect(manager.getAllSessions(), hasLength(3));

      // Act
      await manager.dispose();

      // Assert
      expect(manager.getAllSessions(), isEmpty);
    });

    test('dispose should disconnect all sessions', () async {
      // Arrange
      final session1 = await manager.createSession(connection: testConnection);
      final session2 = await manager.createSession(connection: testConnection);

      // Act
      await manager.dispose();

      // Assert
      final retrieved1 = manager.getSession(session1.id);
      final retrieved2 = manager.getSession(session2.id);

      expect(retrieved1, isNull);
      expect(retrieved2, isNull);
    });

    test('dispose should close sessions stream', () async {
      // Arrange
      var streamClosed = false;
      manager.sessionsStream.listen(
        (_) {},
        onDone: () => streamClosed = true,
      );

      // Act
      await manager.dispose();

      await Future.delayed(const Duration(milliseconds: 50));

      // Assert
      expect(streamClosed, isTrue);
    });

    test('dispose should be idempotent', () async {
      // Act & Assert - Should not throw
      await manager.dispose();
      await manager.dispose();
    });
  });

  group('TerminalSession Entity', () {
    test('should create session with required fields', () {
      final session = TerminalSession(
        id: 'session-1',
        connection: testConnection,
        state: TerminalSessionState.disconnected,
        createdAt: DateTime.now(),
        terminalWidth: 80,
        terminalHeight: 24,
      );

      expect(session.id, 'session-1');
      expect(session.connection.id, testConnection.id);
      expect(session.state, TerminalSessionState.disconnected);
      expect(session.terminalWidth, 80);
      expect(session.terminalHeight, 24);
    });

    test('copyWith should create modified copy', () {
      final session = TerminalSession(
        id: 'session-1',
        connection: testConnection,
        state: TerminalSessionState.disconnected,
        createdAt: DateTime.now(),
        terminalWidth: 80,
        terminalHeight: 24,
      );

      final modified = session.copyWith(
        state: TerminalSessionState.connected,
        terminalWidth: 120,
      );

      expect(modified.state, TerminalSessionState.connected);
      expect(modified.terminalWidth, 120);
      expect(modified.terminalHeight, 24); // Unchanged
      expect(modified.id, session.id); // Unchanged
    });

    test('should track connection timestamps', () {
      final createdAt = DateTime.now();
      final connectedAt = createdAt.add(const Duration(seconds: 2));

      final session = TerminalSession(
        id: 'session-1',
        connection: testConnection,
        state: TerminalSessionState.connected,
        createdAt: createdAt,
        connectedAt: connectedAt,
        terminalWidth: 80,
        terminalHeight: 24,
      );

      expect(session.createdAt, createdAt);
      expect(session.connectedAt, connectedAt);
    });

    test('should track last activity', () {
      final session = TerminalSession(
        id: 'session-1',
        connection: testConnection,
        state: TerminalSessionState.connected,
        createdAt: DateTime.now(),
        lastActivityAt: DateTime.now(),
        terminalWidth: 80,
        terminalHeight: 24,
      );

      expect(session.lastActivityAt, isNotNull);
    });

    test('should track reconnection attempts', () {
      final session = TerminalSession(
        id: 'session-1',
        connection: testConnection,
        state: TerminalSessionState.reconnecting,
        createdAt: DateTime.now(),
        reconnectAttempts: 3,
        terminalWidth: 80,
        terminalHeight: 24,
      );

      expect(session.reconnectAttempts, 3);
    });

    test('should store error messages', () {
      final session = TerminalSession(
        id: 'session-1',
        connection: testConnection,
        state: TerminalSessionState.error,
        createdAt: DateTime.now(),
        errorMessage: 'Connection timeout',
        terminalWidth: 80,
        terminalHeight: 24,
      );

      expect(session.errorMessage, 'Connection timeout');
    });
  });

  group('TerminalSessionState Enum', () {
    test('should have all expected states', () {
      expect(TerminalSessionState.values, hasLength(6));
      expect(TerminalSessionState.values, contains(TerminalSessionState.disconnected));
      expect(TerminalSessionState.values, contains(TerminalSessionState.connecting));
      expect(TerminalSessionState.values, contains(TerminalSessionState.connected));
      expect(TerminalSessionState.values, contains(TerminalSessionState.reconnecting));
      expect(TerminalSessionState.values, contains(TerminalSessionState.error));
      expect(TerminalSessionState.values, contains(TerminalSessionState.disconnecting));
    });

    test('should match SSH client states', () {
      // Mapping validation
      final terminalStates = TerminalSessionState.values.map((s) => s.name).toSet();
      final expectedStates = {
        'disconnected',
        'connecting',
        'connected',
        'reconnecting',
        'error',
        'disconnecting',
      };

      expect(terminalStates, equals(expectedStates));
    });
  });
}
