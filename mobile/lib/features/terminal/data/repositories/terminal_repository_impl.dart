import 'package:paraclete/core/storage/preferences.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/terminal/data/models/ssh_connection_model.dart';
import 'package:paraclete/features/terminal/data/terminal_session_manager.dart';
import 'package:paraclete/features/terminal/domain/entities/command_result.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';
import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';

/// Implementation of TerminalRepository
class TerminalRepositoryImpl implements TerminalRepository {
  final TerminalSessionManager _sessionManager;
  final SecureStorageService _secureStorage;
  final PreferencesService _preferences;

  static const String _connectionsKey = 'ssh_connections';

  TerminalRepositoryImpl({
    required TerminalSessionManager sessionManager,
    required SecureStorageService secureStorage,
    required PreferencesService preferences,
  })  : _sessionManager = sessionManager,
        _secureStorage = secureStorage,
        _preferences = preferences;

  // Connection Management

  @override
  Future<TerminalSession> connect(SshConnection connection) async {
    try {
      // Create session
      final session = await _sessionManager.createSession(
        connection: connection,
        terminalWidth: 80,
        terminalHeight: 24,
      );

      // Connect
      final connectedSession = await _sessionManager.connect(session.id);

      // Update last used time
      final updatedConnection = connection.copyWith(
        lastUsedAt: DateTime.now(),
      );
      await updateConnection(updatedConnection);

      return connectedSession;
    } catch (e) {
      AppLogger.error('Failed to connect: $e');
      rethrow;
    }
  }

  @override
  Future<void> disconnect(String sessionId) async {
    try {
      await _sessionManager.disconnect(sessionId);
      await _sessionManager.removeSession(sessionId);
    } catch (e) {
      AppLogger.error('Failed to disconnect: $e');
      rethrow;
    }
  }

  @override
  Future<TerminalSession> reconnect(String sessionId) async {
    try {
      return await _sessionManager.reconnect(sessionId);
    } catch (e) {
      AppLogger.error('Failed to reconnect: $e');
      rethrow;
    }
  }

  @override
  Future<TerminalSession?> getSession(String sessionId) async {
    return _sessionManager.getSession(sessionId);
  }

  @override
  Future<List<TerminalSession>> getActiveSessions() async {
    return _sessionManager.getAllSessions();
  }

  // Terminal Operations

  @override
  Future<void> sendInput(String sessionId, String data) async {
    try {
      _sessionManager.sendInput(sessionId, data);
    } catch (e) {
      AppLogger.error('Failed to send input: $e');
      rethrow;
    }
  }

  @override
  Future<void> resizeTerminal(String sessionId, int width, int height) async {
    try {
      await _sessionManager.resizeTerminal(sessionId, width, height);
    } catch (e) {
      AppLogger.error('Failed to resize terminal: $e');
      rethrow;
    }
  }

  @override
  Future<CommandResult> executeCommand(String sessionId, String command) async {
    try {
      final startTime = DateTime.now();
      final output = await _sessionManager.executeCommand(sessionId, command);
      final endTime = DateTime.now();

      return CommandResult(
        command: command,
        output: output,
        executedAt: startTime,
        executionTime: endTime.difference(startTime),
      );
    } catch (e) {
      AppLogger.error('Failed to execute command: $e');
      rethrow;
    }
  }

  // SSH Connection Storage

  @override
  Future<void> saveConnection(SshConnection connection) async {
    try {
      final connections = await getSavedConnections();
      final existingIndex = connections.indexWhere((c) => c.id == connection.id);

      if (existingIndex >= 0) {
        connections[existingIndex] = connection;
      } else {
        connections.add(connection);
      }

      await _saveConnections(connections);
      AppLogger.info('Saved SSH connection: ${connection.name}');
    } catch (e) {
      AppLogger.error('Failed to save connection: $e');
      rethrow;
    }
  }

  @override
  Future<List<SshConnection>> getSavedConnections() async {
    try {
      final jsonData = await _secureStorage.getSecureJson(_connectionsKey);
      if (jsonData == null) {
        return [];
      }

      final connectionsList = jsonData['connections'] as List<dynamic>?;
      if (connectionsList == null) {
        return [];
      }

      return connectionsList
          .map((json) => SshConnectionModel.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      AppLogger.error('Failed to load connections: $e');
      return [];
    }
  }

  @override
  Future<SshConnection?> getSavedConnection(String id) async {
    final connections = await getSavedConnections();
    try {
      return connections.firstWhere((c) => c.id == id);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<void> updateConnection(SshConnection connection) async {
    await saveConnection(connection);
  }

  @override
  Future<void> deleteConnection(String id) async {
    try {
      final connections = await getSavedConnections();
      connections.removeWhere((c) => c.id == id);
      await _saveConnections(connections);
      AppLogger.info('Deleted SSH connection: $id');
    } catch (e) {
      AppLogger.error('Failed to delete connection: $e');
      rethrow;
    }
  }

  // Terminal Output Streams

  @override
  Stream<String> getTerminalOutputStream(String sessionId) {
    final stream = _sessionManager.getOutputStream(sessionId);
    if (stream == null) {
      throw Exception('Session not found: $sessionId');
    }
    return stream;
  }

  @override
  Stream<TerminalSession> getSessionStateStream(String sessionId) {
    return _sessionManager.getSessionStream(sessionId);
  }

  // Private methods

  Future<void> _saveConnections(List<SshConnection> connections) async {
    final jsonData = {
      'connections': connections.map((c) => c.toJson()).toList(),
    };
    await _secureStorage.storeSecureJson(_connectionsKey, jsonData);
  }
}
