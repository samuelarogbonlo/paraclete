import 'dart:async';

import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/terminal/data/ssh_client.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';
import 'package:uuid/uuid.dart';

/// Manages active terminal sessions
class TerminalSessionManager {
  final Map<String, _SessionContext> _sessions = {};
  final StreamController<Map<String, TerminalSession>> _sessionsController =
      StreamController.broadcast();

  /// Stream of all sessions
  Stream<Map<String, TerminalSession>> get sessionsStream =>
      _sessionsController.stream;

  /// Create a new terminal session
  Future<TerminalSession> createSession({
    required SshConnection connection,
    int terminalWidth = 80,
    int terminalHeight = 24,
  }) async {
    final sessionId = const Uuid().v4();
    final session = TerminalSession(
      id: sessionId,
      connection: connection,
      state: TerminalSessionState.disconnected,
      createdAt: DateTime.now(),
      terminalWidth: terminalWidth,
      terminalHeight: terminalHeight,
    );

    final sshClient = SshClientWrapper(connection);
    final context = _SessionContext(
      session: session,
      sshClient: sshClient,
    );

    _sessions[sessionId] = context;
    _notifySessionsChanged();

    AppLogger.info('Created terminal session $sessionId');
    return session;
  }

  /// Connect a session
  Future<TerminalSession> connect(String sessionId) async {
    final context = _sessions[sessionId];
    if (context == null) {
      throw Exception('Session not found: $sessionId');
    }

    try {
      // Update state to connecting
      context.session = context.session.copyWith(
        state: TerminalSessionState.connecting,
      );
      _notifySessionsChanged();

      // Listen to SSH client state changes
      context.sshClient.stateStream.listen((sshState) {
        _updateSessionFromSshState(sessionId, sshState);
      });

      // Connect SSH client
      await context.sshClient.connect(
        terminalWidth: context.session.terminalWidth,
        terminalHeight: context.session.terminalHeight,
      );

      // Update session state
      context.session = context.session.copyWith(
        state: TerminalSessionState.connected,
        connectedAt: DateTime.now(),
        lastActivityAt: DateTime.now(),
        reconnectAttempts: 0,
      );
      _notifySessionsChanged();

      AppLogger.info('Session $sessionId connected');
      return context.session;
    } catch (e) {
      context.session = context.session.copyWith(
        state: TerminalSessionState.error,
        errorMessage: e.toString(),
      );
      _notifySessionsChanged();
      rethrow;
    }
  }

  /// Disconnect a session
  Future<void> disconnect(String sessionId) async {
    final context = _sessions[sessionId];
    if (context == null) {
      AppLogger.warning('Attempted to disconnect non-existent session: $sessionId');
      return;
    }

    try {
      context.session = context.session.copyWith(
        state: TerminalSessionState.disconnecting,
      );
      _notifySessionsChanged();

      await context.sshClient.disconnect();

      context.session = context.session.copyWith(
        state: TerminalSessionState.disconnected,
      );
      _notifySessionsChanged();

      AppLogger.info('Session $sessionId disconnected');
    } catch (e) {
      AppLogger.error('Error disconnecting session $sessionId: $e');
      context.session = context.session.copyWith(
        state: TerminalSessionState.error,
        errorMessage: e.toString(),
      );
      _notifySessionsChanged();
    }
  }

  /// Reconnect a session
  Future<TerminalSession> reconnect(String sessionId) async {
    final context = _sessions[sessionId];
    if (context == null) {
      throw Exception('Session not found: $sessionId');
    }

    context.session = context.session.copyWith(
      state: TerminalSessionState.reconnecting,
      reconnectAttempts: context.session.reconnectAttempts + 1,
    );
    _notifySessionsChanged();

    return connect(sessionId);
  }

  /// Get a specific session
  TerminalSession? getSession(String sessionId) {
    return _sessions[sessionId]?.session;
  }

  /// Get all active sessions
  List<TerminalSession> getAllSessions() {
    return _sessions.values.map((ctx) => ctx.session).toList();
  }

  /// Send input to terminal
  void sendInput(String sessionId, String data) {
    final context = _sessions[sessionId];
    if (context == null) {
      throw Exception('Session not found: $sessionId');
    }

    context.sshClient.sendInput(data);
    context.session = context.session.copyWith(
      lastActivityAt: DateTime.now(),
    );
  }

  /// Resize terminal
  Future<void> resizeTerminal(String sessionId, int width, int height) async {
    final context = _sessions[sessionId];
    if (context == null) {
      throw Exception('Session not found: $sessionId');
    }

    await context.sshClient.resize(width, height);
    context.session = context.session.copyWith(
      terminalWidth: width,
      terminalHeight: height,
    );
    _notifySessionsChanged();
  }

  /// Get terminal output stream for a session
  Stream<String>? getOutputStream(String sessionId) {
    return _sessions[sessionId]?.sshClient.outputStream;
  }

  /// Get session state stream
  Stream<TerminalSession> getSessionStream(String sessionId) {
    return _sessionsController.stream.map((sessions) {
      final session = sessions[sessionId];
      if (session == null) {
        throw Exception('Session not found: $sessionId');
      }
      return session;
    });
  }

  /// Execute a command (non-interactive)
  Future<String> executeCommand(String sessionId, String command) async {
    final context = _sessions[sessionId];
    if (context == null) {
      throw Exception('Session not found: $sessionId');
    }

    return context.sshClient.executeCommand(command);
  }

  /// Remove a session
  Future<void> removeSession(String sessionId) async {
    final context = _sessions[sessionId];
    if (context == null) {
      return;
    }

    await disconnect(sessionId);
    context.sshClient.dispose();
    _sessions.remove(sessionId);
    _notifySessionsChanged();

    AppLogger.info('Removed session $sessionId');
  }

  /// Dispose all sessions
  Future<void> dispose() async {
    for (final sessionId in _sessions.keys.toList()) {
      await removeSession(sessionId);
    }
    _sessionsController.close();
  }

  // Private methods

  void _updateSessionFromSshState(String sessionId, SshClientState sshState) {
    final context = _sessions[sessionId];
    if (context == null) return;

    final sessionState = switch (sshState) {
      SshClientState.disconnected => TerminalSessionState.disconnected,
      SshClientState.connecting => TerminalSessionState.connecting,
      SshClientState.connected => TerminalSessionState.connected,
      SshClientState.reconnecting => TerminalSessionState.reconnecting,
      SshClientState.error => TerminalSessionState.error,
      SshClientState.disconnecting => TerminalSessionState.disconnecting,
    };

    context.session = context.session.copyWith(state: sessionState);
    _notifySessionsChanged();
  }

  void _notifySessionsChanged() {
    if (!_sessionsController.isClosed) {
      final sessionMap = {
        for (var entry in _sessions.entries) entry.key: entry.value.session
      };
      _sessionsController.add(sessionMap);
    }
  }
}

/// Internal context for managing a session
class _SessionContext {
  TerminalSession session;
  final SshClientWrapper sshClient;

  _SessionContext({
    required this.session,
    required this.sshClient,
  });
}
