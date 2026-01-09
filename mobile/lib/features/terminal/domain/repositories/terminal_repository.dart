import 'package:paraclete/features/terminal/domain/entities/command_result.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';

/// Repository interface for terminal operations
abstract class TerminalRepository {
  // Connection Management
  /// Connect to an SSH host
  Future<TerminalSession> connect(SshConnection connection);

  /// Disconnect from current SSH session
  Future<void> disconnect(String sessionId);

  /// Reconnect to a session
  Future<TerminalSession> reconnect(String sessionId);

  /// Get current session state
  Future<TerminalSession?> getSession(String sessionId);

  /// Get all active sessions
  Future<List<TerminalSession>> getActiveSessions();

  // Terminal Operations
  /// Send input to terminal
  Future<void> sendInput(String sessionId, String data);

  /// Resize terminal
  Future<void> resizeTerminal(String sessionId, int width, int height);

  /// Execute a command and return result (non-interactive)
  Future<CommandResult> executeCommand(String sessionId, String command);

  // SSH Connection Storage
  /// Save SSH connection configuration
  Future<void> saveConnection(SshConnection connection);

  /// Get all saved connections
  Future<List<SshConnection>> getSavedConnections();

  /// Get a specific saved connection
  Future<SshConnection?> getSavedConnection(String id);

  /// Update saved connection
  Future<void> updateConnection(SshConnection connection);

  /// Delete saved connection
  Future<void> deleteConnection(String id);

  // Terminal Output Stream
  /// Stream of terminal output for a session
  Stream<String> getTerminalOutputStream(String sessionId);

  /// Stream of session state changes
  Stream<TerminalSession> getSessionStateStream(String sessionId);
}
