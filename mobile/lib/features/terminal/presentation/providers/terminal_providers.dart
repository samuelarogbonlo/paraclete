import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/storage/preferences.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:paraclete/features/terminal/data/repositories/terminal_repository_impl.dart';
import 'package:paraclete/features/terminal/data/terminal_session_manager.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';
import 'package:paraclete/features/terminal/domain/repositories/terminal_repository.dart';
import 'package:paraclete/features/terminal/domain/usecases/connect_ssh.dart';
import 'package:paraclete/features/terminal/domain/usecases/disconnect_ssh.dart';
import 'package:paraclete/features/terminal/domain/usecases/execute_command.dart';
import 'package:paraclete/features/terminal/domain/usecases/manage_saved_connections.dart';
import 'package:paraclete/features/terminal/domain/usecases/resize_terminal.dart';
import 'package:paraclete/features/terminal/domain/usecases/send_terminal_input.dart';

// Core Dependencies

final terminalSessionManagerProvider = Provider<TerminalSessionManager>((ref) {
  final manager = TerminalSessionManager();
  ref.onDispose(() => manager.dispose());
  return manager;
});

final terminalRepositoryProvider = Provider<TerminalRepository>((ref) {
  return TerminalRepositoryImpl(
    sessionManager: ref.watch(terminalSessionManagerProvider),
    secureStorage: SecureStorageService(),
    preferences: PreferencesService(),
  );
});

// Use Cases

final connectSshProvider = Provider<ConnectSsh>((ref) {
  return ConnectSsh(ref.watch(terminalRepositoryProvider));
});

final disconnectSshProvider = Provider<DisconnectSsh>((ref) {
  return DisconnectSsh(ref.watch(terminalRepositoryProvider));
});

final executeCommandProvider = Provider<ExecuteCommand>((ref) {
  return ExecuteCommand(ref.watch(terminalRepositoryProvider));
});

final sendTerminalInputProvider = Provider<SendTerminalInput>((ref) {
  return SendTerminalInput(ref.watch(terminalRepositoryProvider));
});

final resizeTerminalProvider = Provider<ResizeTerminal>((ref) {
  return ResizeTerminal(ref.watch(terminalRepositoryProvider));
});

final manageSavedConnectionsProvider = Provider<ManageSavedConnections>((ref) {
  return ManageSavedConnections(ref.watch(terminalRepositoryProvider));
});

// State Providers

/// Provider for saved SSH connections
final savedConnectionsProvider = FutureProvider<List<SshConnection>>((ref) async {
  final useCase = ref.watch(manageSavedConnectionsProvider);
  return useCase.getSavedConnections();
});

/// Provider for active terminal sessions
final activeSessionsProvider = StreamProvider<List<TerminalSession>>((ref) async* {
  final repository = ref.watch(terminalRepositoryProvider);
  yield await repository.getActiveSessions();

  // Listen to session manager updates
  final sessionManager = ref.watch(terminalSessionManagerProvider);
  await for (final sessions in sessionManager.sessionsStream) {
    yield sessions.values.toList();
  }
});

/// Provider for a specific terminal session
final terminalSessionProvider = StreamProvider.family<TerminalSession?, String>(
  (ref, sessionId) async* {
    final repository = ref.watch(terminalRepositoryProvider);
    yield await repository.getSession(sessionId);

    // Stream updates
    await for (final session in repository.getSessionStateStream(sessionId)) {
      yield session;
    }
  },
);

/// Provider for terminal output stream
final terminalOutputProvider = StreamProvider.family<String, String>(
  (ref, sessionId) {
    final repository = ref.watch(terminalRepositoryProvider);
    return repository.getTerminalOutputStream(sessionId);
  },
);

/// Provider for currently selected connection
final selectedConnectionProvider = StateProvider<SshConnection?>((ref) => null);

/// Provider for current active session ID
final activeSessionIdProvider = StateProvider<String?>((ref) => null);
