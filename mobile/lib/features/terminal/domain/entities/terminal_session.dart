import 'package:equatable/equatable.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';

/// Terminal session state
enum TerminalSessionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
  disconnecting,
}

/// Terminal session entity
class TerminalSession extends Equatable {
  final String id;
  final SshConnection connection;
  final TerminalSessionState state;
  final String? errorMessage;
  final DateTime createdAt;
  final DateTime? connectedAt;
  final DateTime? lastActivityAt;
  final int terminalWidth;
  final int terminalHeight;
  final int reconnectAttempts;
  final int maxReconnectAttempts;
  final String? tmuxSession;
  final Map<String, dynamic>? metadata;

  const TerminalSession({
    required this.id,
    required this.connection,
    this.state = TerminalSessionState.disconnected,
    this.errorMessage,
    required this.createdAt,
    this.connectedAt,
    this.lastActivityAt,
    this.terminalWidth = 80,
    this.terminalHeight = 24,
    this.reconnectAttempts = 0,
    this.maxReconnectAttempts = 5,
    this.tmuxSession,
    this.metadata,
  });

  bool get isConnected => state == TerminalSessionState.connected;
  bool get isConnecting =>
      state == TerminalSessionState.connecting ||
      state == TerminalSessionState.reconnecting;
  bool get hasError => state == TerminalSessionState.error;
  bool get canReconnect =>
      reconnectAttempts < maxReconnectAttempts && connection.autoReconnect;

  TerminalSession copyWith({
    String? id,
    SshConnection? connection,
    TerminalSessionState? state,
    String? errorMessage,
    DateTime? createdAt,
    DateTime? connectedAt,
    DateTime? lastActivityAt,
    int? terminalWidth,
    int? terminalHeight,
    int? reconnectAttempts,
    int? maxReconnectAttempts,
    String? tmuxSession,
    Map<String, dynamic>? metadata,
  }) {
    return TerminalSession(
      id: id ?? this.id,
      connection: connection ?? this.connection,
      state: state ?? this.state,
      errorMessage: errorMessage ?? this.errorMessage,
      createdAt: createdAt ?? this.createdAt,
      connectedAt: connectedAt ?? this.connectedAt,
      lastActivityAt: lastActivityAt ?? this.lastActivityAt,
      terminalWidth: terminalWidth ?? this.terminalWidth,
      terminalHeight: terminalHeight ?? this.terminalHeight,
      reconnectAttempts: reconnectAttempts ?? this.reconnectAttempts,
      maxReconnectAttempts: maxReconnectAttempts ?? this.maxReconnectAttempts,
      tmuxSession: tmuxSession ?? this.tmuxSession,
      metadata: metadata ?? this.metadata,
    );
  }

  @override
  List<Object?> get props => [
        id,
        connection,
        state,
        errorMessage,
        createdAt,
        connectedAt,
        lastActivityAt,
        terminalWidth,
        terminalHeight,
        reconnectAttempts,
        maxReconnectAttempts,
        tmuxSession,
        metadata,
      ];
}
