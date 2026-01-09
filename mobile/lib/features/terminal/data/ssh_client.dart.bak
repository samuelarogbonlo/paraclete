import 'dart:async';
import 'dart:convert';

import 'package:dartssh2/dartssh2.dart';
import 'package:paraclete/core/utils/logger.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';

/// Exception thrown when SSH connection fails
class SshConnectionException implements Exception {
  final String message;
  final Object? originalError;

  SshConnectionException(this.message, [this.originalError]);

  @override
  String toString() => 'SshConnectionException: $message';
}

/// Wrapper around dartssh2 for SSH client operations
class SshClientWrapper {
  SSHClient? _client;
  SSHSession? _shell;
  final SshConnection config;
  final StreamController<String> _outputController = StreamController.broadcast();
  final StreamController<SshClientState> _stateController = StreamController.broadcast();

  SshClientState _currentState = SshClientState.disconnected;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _isDisposed = false;

  SshClientWrapper(this.config);

  /// Current connection state
  SshClientState get state => _currentState;

  /// Stream of terminal output
  Stream<String> get outputStream => _outputController.stream;

  /// Stream of state changes
  Stream<SshClientState> get stateStream => _stateController.stream;

  /// Check if connected
  bool get isConnected => _currentState == SshClientState.connected;

  /// Connect to SSH host
  Future<void> connect({
    required int terminalWidth,
    required int terminalHeight,
  }) async {
    if (_isDisposed) {
      throw SshConnectionException('Client is disposed');
    }

    _updateState(SshClientState.connecting);

    try {
      // Establish socket connection
      final socket = await SSHSocket.connect(
        config.host,
        config.port,
        timeout: const Duration(seconds: 30),
      );

      // Create SSH client with authentication
      if (config.authMethod == SshAuthMethod.password) {
        if (config.password == null) {
          throw SshConnectionException('Password is required for password authentication');
        }
        _client = SSHClient(
          socket,
          username: config.username,
          onPasswordRequest: () => config.password!,
        );
      } else if (config.authMethod == SshAuthMethod.publicKey) {
        if (config.privateKey == null) {
          throw SshConnectionException('Private key is required for public key authentication');
        }
        _client = SSHClient(
          socket,
          username: config.username,
          identities: [
            ...SSHKeyPair.fromPem(
              config.privateKey!,
              config.privateKeyPassphrase,
            ),
          ],
        );
      } else {
        throw SshConnectionException('Unsupported authentication method: ${config.authMethod}');
      }

      // Request PTY and start shell
      _shell = await _client!.shell(
        pty: SSHPtyConfig(
          type: 'xterm-256color',
          width: terminalWidth,
          height: terminalHeight,
        ),
      );

      // Listen to shell output
      _shell!.stdout.cast<List<int>>().transform(utf8.decoder).listen(
        (data) {
          if (!_isDisposed) {
            _outputController.add(data);
          }
        },
        onError: (error) {
          AppLogger.error('SSH shell output error: $error');
          if (!_isDisposed) {
            _handleConnectionError(error);
          }
        },
        onDone: () {
          AppLogger.info('SSH shell output closed');
          if (!_isDisposed && _currentState == SshClientState.connected) {
            _handleConnectionClosed();
          }
        },
      );

      // Also listen to stderr
      _shell!.stderr.cast<List<int>>().transform(utf8.decoder).listen(
        (data) {
          if (!_isDisposed) {
            _outputController.add(data);
          }
        },
      );

      _reconnectAttempts = 0;
      _updateState(SshClientState.connected);
      AppLogger.info('SSH connected to ${config.host}:${config.port}');
    } catch (e, stackTrace) {
      AppLogger.error('SSH connection failed: $e', error: e, stackTrace: stackTrace);
      _updateState(SshClientState.error);

      if (config.autoReconnect && _reconnectAttempts < 5) {
        _scheduleReconnect(terminalWidth, terminalHeight);
      } else {
        throw SshConnectionException('Failed to connect to ${config.host}:${config.port}', e);
      }
    }
  }

  /// Disconnect from SSH host
  Future<void> disconnect() async {
    _cancelReconnect();
    _updateState(SshClientState.disconnecting);

    try {
      _shell?.close();
      _client?.close();
    } catch (e) {
      AppLogger.error('Error during disconnect: $e');
    } finally {
      _shell = null;
      _client = null;
      _updateState(SshClientState.disconnected);
      AppLogger.info('SSH disconnected from ${config.host}');
    }
  }

  /// Send input to terminal
  void sendInput(String data) {
    if (!isConnected || _shell == null) {
      throw SshConnectionException('Not connected');
    }

    try {
      _shell!.stdin.add(utf8.encode(data));
    } catch (e) {
      AppLogger.error('Failed to send input: $e');
      throw SshConnectionException('Failed to send input', e);
    }
  }

  /// Resize terminal
  Future<void> resize(int width, int height) async {
    if (!isConnected || _shell == null) {
      throw SshConnectionException('Not connected');
    }

    try {
      _shell!.resizeTerminal(width, height);
      AppLogger.debug('Terminal resized to ${width}x$height');
    } catch (e) {
      AppLogger.error('Failed to resize terminal: $e');
      throw SshConnectionException('Failed to resize terminal', e);
    }
  }

  /// Execute a command and wait for result (non-interactive)
  Future<String> executeCommand(String command) async {
    if (!isConnected || _client == null) {
      throw SshConnectionException('Not connected');
    }

    try {
      final result = await _client!.run(command);
      return utf8.decode(result);
    } catch (e) {
      AppLogger.error('Failed to execute command: $e');
      throw SshConnectionException('Failed to execute command', e);
    }
  }

  /// Dispose resources
  void dispose() {
    if (_isDisposed) return;

    _isDisposed = true;
    _cancelReconnect();

    disconnect().catchError((e) {
      AppLogger.error('Error during dispose: $e');
    });

    _outputController.close();
    _stateController.close();
  }

  // Private methods

  void _updateState(SshClientState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      if (!_stateController.isClosed) {
        _stateController.add(newState);
      }
    }
  }

  void _handleConnectionError(Object error) {
    AppLogger.error('Connection error: $error');
    _updateState(SshClientState.error);

    if (config.autoReconnect && _reconnectAttempts < 5) {
      _scheduleReconnect(80, 24); // Default terminal size
    }
  }

  void _handleConnectionClosed() {
    AppLogger.info('Connection closed unexpectedly');
    _updateState(SshClientState.disconnected);

    if (config.autoReconnect && _reconnectAttempts < 5) {
      _scheduleReconnect(80, 24); // Default terminal size
    }
  }

  void _scheduleReconnect(int width, int height) {
    _cancelReconnect();

    _reconnectAttempts++;
    final delay = _calculateReconnectDelay();

    AppLogger.info('Scheduling reconnect attempt $_reconnectAttempts in ${delay.inSeconds}s');
    _updateState(SshClientState.reconnecting);

    _reconnectTimer = Timer(delay, () {
      if (!_isDisposed) {
        AppLogger.info('Attempting to reconnect...');
        connect(terminalWidth: width, terminalHeight: height).catchError((e) {
          AppLogger.error('Reconnect failed: $e');
        });
      }
    });
  }

  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  Duration _calculateReconnectDelay() {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
    final baseDelay = config.reconnectDelay;
    final exponentialDelay = baseDelay * (1 << (_reconnectAttempts - 1));
    final cappedDelay = exponentialDelay.clamp(baseDelay, 30000);
    return Duration(milliseconds: cappedDelay);
  }
}

/// SSH client state
enum SshClientState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
  disconnecting,
}
