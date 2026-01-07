import 'dart:async';
import 'dart:convert';

import 'package:logger/logger.dart';
import 'package:paraclete/core/config/app_config.dart';
import 'package:paraclete/core/config/env_config.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket connection state
enum WebSocketState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

/// WebSocket message types
class WebSocketMessage {
  final String type;
  final Map<String, dynamic> data;
  final DateTime timestamp;

  WebSocketMessage({
    required this.type,
    required this.data,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory WebSocketMessage.fromJson(Map<String, dynamic> json) {
    return WebSocketMessage(
      type: json['type'] as String,
      data: json['data'] as Map<String, dynamic>,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'type': type,
        'data': data,
        'timestamp': timestamp.toIso8601String(),
      };
}

/// WebSocket client for real-time communication
class WebSocketClient {
  final SecureStorageService _secureStorage;
  final Logger _logger = Logger();

  WebSocketChannel? _channel;
  StreamController<WebSocketMessage>? _messageController;
  StreamController<WebSocketState>? _stateController;
  Timer? _reconnectTimer;
  Timer? _pingTimer;

  int _reconnectAttempts = 0;
  WebSocketState _currentState = WebSocketState.disconnected;
  String? _sessionId;
  String? _accessToken;

  // Public streams
  Stream<WebSocketMessage> get messages =>
      (_messageController ??= StreamController<WebSocketMessage>.broadcast())
          .stream;

  Stream<WebSocketState> get state =>
      (_stateController ??= StreamController<WebSocketState>.broadcast())
          .stream;

  WebSocketState get currentState => _currentState;
  bool get isConnected => _currentState == WebSocketState.connected;

  WebSocketClient({required SecureStorageService secureStorage})
      : _secureStorage = secureStorage;

  /// Connect to WebSocket server
  Future<void> connect({
    required String sessionId,
    Map<String, dynamic>? params,
  }) async {
    if (_currentState == WebSocketState.connected ||
        _currentState == WebSocketState.connecting) {
      _logger.w('WebSocket already connected or connecting');
      return;
    }

    _sessionId = sessionId;
    _reconnectAttempts = 0;
    await _connectInternal(params: params);
  }

  Future<void> _connectInternal({Map<String, dynamic>? params}) async {
    try {
      _updateState(WebSocketState.connecting);

      // Get access token
      _accessToken = await _secureStorage.getAccessToken();
      if (_accessToken == null) {
        _logger.e('Cannot connect: No access token available');
        _updateState(WebSocketState.error);
        return;
      }

      // Build WebSocket URL with query parameters (NO TOKEN in query params)
      final queryParams = {
        'session_id': _sessionId,
        ...?params,
      };

      final uri = Uri.parse('${EnvConfig.wsBaseUrl}/ws/stream').replace(
        queryParameters: queryParams,
      );

      _logger.d('Connecting to WebSocket: ${uri.toString()}');

      // Create WebSocket channel
      _channel = WebSocketChannel.connect(uri);

      // Listen to messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDisconnect,
        cancelOnError: false,
      );

      // Send auth message immediately after connection
      sendMessage(
        WebSocketMessage(
          type: 'auth',
          data: {
            'token': _accessToken,
          },
        ),
      );

      // Send handshake after auth
      sendMessage(
        WebSocketMessage(
          type: 'handshake',
          data: {
            'session_id': _sessionId,
            'client_version': AppConfig.appVersion,
            'platform': 'mobile',
          },
        ),
      );

      _updateState(WebSocketState.connected);
      _startPingTimer();
      _reconnectAttempts = 0;

      _logger.i('WebSocket connected successfully');
    } catch (e, stackTrace) {
      _logger.e('WebSocket connection error', error: e, stackTrace: stackTrace);
      _updateState(WebSocketState.error);
      _scheduleReconnect();
    }
  }

  /// Send a message through WebSocket
  void sendMessage(WebSocketMessage message) {
    if (!isConnected) {
      _logger.w('Cannot send message: WebSocket not connected');
      return;
    }

    try {
      final json = jsonEncode(message.toJson());
      _channel?.sink.add(json);
      _logger.d('Sent message: ${message.type}');
    } catch (e) {
      _logger.e('Error sending message: $e');
      _handleError(e);
    }
  }

  /// Send voice input
  void sendVoiceInput(String transcript) {
    sendMessage(
      WebSocketMessage(
        type: 'voice_input',
        data: {
          'transcript': transcript,
          'timestamp': DateTime.now().toIso8601String(),
        },
      ),
    );
  }

  /// Send approval response
  void sendApproval(String actionId, bool approved) {
    sendMessage(
      WebSocketMessage(
        type: 'approval',
        data: {
          'action_id': actionId,
          'approved': approved,
        },
      ),
    );
  }

  /// Cancel current task
  void cancelTask(String reason) {
    sendMessage(
      WebSocketMessage(
        type: 'cancel',
        data: {'reason': reason},
      ),
    );
  }

  /// Disconnect from WebSocket
  Future<void> disconnect() async {
    _logger.d('Disconnecting WebSocket');
    _cancelTimers();
    _reconnectAttempts = 0;

    if (_channel != null) {
      // Send disconnect message
      try {
        sendMessage(
          WebSocketMessage(
            type: 'disconnect',
            data: {'reason': 'client_disconnect'},
          ),
        );
      } catch (_) {
        // Ignore errors when disconnecting
      }

      await _channel!.sink.close();
      _channel = null;
    }

    _updateState(WebSocketState.disconnected);
  }

  /// Reconnect with exponential backoff
  void _scheduleReconnect() {
    if (_reconnectAttempts >= AppConfig.wsMaxReconnectAttempts) {
      _logger.e('Max reconnect attempts reached');
      _updateState(WebSocketState.error);
      return;
    }

    _updateState(WebSocketState.reconnecting);

    final delay = AppConfig.wsReconnectDelay * (1 << _reconnectAttempts);
    _logger.d('Scheduling reconnect in ${delay.inSeconds} seconds');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () async {
      _reconnectAttempts++;
      await _connectInternal();
    });
  }

  /// Handle incoming messages
  void _handleMessage(dynamic data) {
    try {
      final Map<String, dynamic> json;
      if (data is String) {
        json = jsonDecode(data) as Map<String, dynamic>;
      } else {
        json = data as Map<String, dynamic>;
      }

      final message = WebSocketMessage.fromJson(json);
      _logger.d('Received message: ${message.type}');

      // Handle ping/pong
      if (message.type == 'ping') {
        sendMessage(WebSocketMessage(type: 'pong', data: {}));
        return;
      }

      // Emit message to listeners
      _messageController?.add(message);
    } catch (e) {
      _logger.e('Error handling message: $e');
    }
  }

  /// Handle WebSocket errors
  void _handleError(dynamic error) {
    _logger.e('WebSocket error: $error');
    _updateState(WebSocketState.error);
    _scheduleReconnect();
  }

  /// Handle WebSocket disconnect
  void _handleDisconnect() {
    _logger.w('WebSocket disconnected');
    _cancelTimers();
    _channel = null;
    _updateState(WebSocketState.disconnected);

    // Only reconnect if we didn't explicitly disconnect
    if (_sessionId != null) {
      _scheduleReconnect();
    }
  }

  /// Update connection state
  void _updateState(WebSocketState newState) {
    if (_currentState != newState) {
      _currentState = newState;
      _stateController?.add(newState);
      _logger.i('WebSocket state changed to: $newState');
    }
  }

  /// Start ping timer to keep connection alive
  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(AppConfig.wsPingInterval, (_) {
      if (isConnected) {
        sendMessage(WebSocketMessage(type: 'ping', data: {}));
      }
    });
  }

  /// Cancel all timers
  void _cancelTimers() {
    _reconnectTimer?.cancel();
    _pingTimer?.cancel();
    _reconnectTimer = null;
    _pingTimer = null;
  }

  /// Clean up resources
  void dispose() {
    disconnect();
    _messageController?.close();
    _stateController?.close();
    _messageController = null;
    _stateController = null;
  }
}