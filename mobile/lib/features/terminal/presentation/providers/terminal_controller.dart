import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';
import 'package:paraclete/features/terminal/presentation/providers/terminal_providers.dart';
import 'package:uuid/uuid.dart';

/// State for terminal controller
class TerminalControllerState {
  final TerminalSession? currentSession;
  final bool isLoading;
  final String? errorMessage;

  const TerminalControllerState({
    this.currentSession,
    this.isLoading = false,
    this.errorMessage,
  });

  TerminalControllerState copyWith({
    TerminalSession? currentSession,
    bool? isLoading,
    String? errorMessage,
  }) {
    return TerminalControllerState(
      currentSession: currentSession ?? this.currentSession,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }
}

/// Controller for terminal operations
class TerminalController extends StateNotifier<TerminalControllerState> {
  final Ref _ref;

  TerminalController(this._ref) : super(const TerminalControllerState());

  /// Connect to SSH host
  Future<void> connect(SshConnection connection) async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final connectUseCase = _ref.read(connectSshProvider);
      final session = await connectUseCase(connection);

      state = state.copyWith(
        currentSession: session,
        isLoading: false,
      );

      // Update active session ID
      _ref.read(activeSessionIdProvider.notifier).state = session.id;

      AppLogger.info('Connected to ${connection.host}');
    } catch (e) {
      AppLogger.error('Failed to connect: $e');
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
      rethrow;
    }
  }

  /// Disconnect current session
  Future<void> disconnect() async {
    final sessionId = state.currentSession?.id;
    if (sessionId == null) return;

    try {
      final disconnectUseCase = _ref.read(disconnectSshProvider);
      await disconnectUseCase(sessionId);

      state = state.copyWith(currentSession: null);
      _ref.read(activeSessionIdProvider.notifier).state = null;

      AppLogger.info('Disconnected session $sessionId');
    } catch (e) {
      AppLogger.error('Failed to disconnect: $e');
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  /// Send input to terminal
  void sendInput(String data) {
    final sessionId = state.currentSession?.id;
    if (sessionId == null) return;

    try {
      final sendInputUseCase = _ref.read(sendTerminalInputProvider);
      sendInputUseCase(sessionId, data);
    } catch (e) {
      AppLogger.error('Failed to send input: $e');
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  /// Resize terminal
  Future<void> resize(int width, int height) async {
    final sessionId = state.currentSession?.id;
    if (sessionId == null) return;

    try {
      final resizeUseCase = _ref.read(resizeTerminalProvider);
      await resizeUseCase(sessionId, width, height);
    } catch (e) {
      AppLogger.error('Failed to resize terminal: $e');
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  /// Execute a command
  Future<void> executeCommand(String command) async {
    final sessionId = state.currentSession?.id;
    if (sessionId == null) return;

    try {
      final executeUseCase = _ref.read(executeCommandProvider);
      await executeUseCase(sessionId, command);
    } catch (e) {
      AppLogger.error('Failed to execute command: $e');
      state = state.copyWith(errorMessage: e.toString());
    }
  }

  /// Clear error message
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

/// Provider for terminal controller
final terminalControllerProvider =
    StateNotifierProvider<TerminalController, TerminalControllerState>((ref) {
  return TerminalController(ref);
});

/// Controller for managing saved connections
class ConnectionsController extends StateNotifier<AsyncValue<List<SshConnection>>> {
  final Ref _ref;

  ConnectionsController(this._ref) : super(const AsyncValue.loading()) {
    _loadConnections();
  }

  Future<void> _loadConnections() async {
    state = const AsyncValue.loading();
    try {
      final useCase = _ref.read(manageSavedConnectionsProvider);
      final connections = await useCase.getSavedConnections();
      state = AsyncValue.data(connections);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  /// Add a new connection
  Future<void> addConnection(SshConnection connection) async {
    try {
      final useCase = _ref.read(manageSavedConnectionsProvider);
      await useCase.saveConnection(connection);
      await _loadConnections();
    } catch (e) {
      AppLogger.error('Failed to add connection: $e');
      rethrow;
    }
  }

  /// Update a connection
  Future<void> updateConnection(SshConnection connection) async {
    try {
      final useCase = _ref.read(manageSavedConnectionsProvider);
      await useCase.updateConnection(connection);
      await _loadConnections();
    } catch (e) {
      AppLogger.error('Failed to update connection: $e');
      rethrow;
    }
  }

  /// Delete a connection
  Future<void> deleteConnection(String id) async {
    try {
      final useCase = _ref.read(manageSavedConnectionsProvider);
      await useCase.deleteConnection(id);
      await _loadConnections();
    } catch (e) {
      AppLogger.error('Failed to delete connection: $e');
      rethrow;
    }
  }

  /// Refresh connections
  Future<void> refresh() => _loadConnections();
}

/// Provider for connections controller
final connectionsControllerProvider =
    StateNotifierProvider<ConnectionsController, AsyncValue<List<SshConnection>>>((ref) {
  return ConnectionsController(ref);
});

/// Helper to create a new SSH connection with default values
SshConnection createNewConnection({
  required String name,
  required String host,
  required String username,
  int port = 22,
  SshAuthMethod authMethod = SshAuthMethod.password,
  String? password,
  String? privateKey,
  String? description,
}) {
  return SshConnection(
    id: const Uuid().v4(),
    name: name,
    host: host,
    port: port,
    username: username,
    authMethod: authMethod,
    password: password,
    privateKey: privateKey,
    createdAt: DateTime.now(),
    description: description,
  );
}
