import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/terminal/domain/entities/ssh_connection.dart';
import 'package:paraclete/features/terminal/presentation/providers/terminal_controller.dart';
import 'package:paraclete/features/terminal/presentation/providers/terminal_providers.dart';
import 'package:paraclete/features/terminal/presentation/widgets/connection_indicator.dart';
import 'package:paraclete/features/terminal/presentation/widgets/mobile_keyboard.dart';
import 'package:xterm/xterm.dart';
import 'package:xterm/flutter.dart';

/// Terminal screen with xterm.dart integration
class TerminalScreen extends ConsumerStatefulWidget {
  final SshConnection? connection;

  const TerminalScreen({
    super.key,
    this.connection,
  });

  @override
  ConsumerState<TerminalScreen> createState() => _TerminalScreenState();
}

class _TerminalScreenState extends ConsumerState<TerminalScreen>
    with WidgetsBindingObserver {
  late final Terminal _terminal;
  final TerminalController _terminalController = TerminalController();
  bool _showMobileKeyboard = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // Initialize xterm terminal
    _terminal = Terminal(
      maxLines: 10000,
    );

    // Auto-connect if connection provided
    if (widget.connection != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _connect();
      });
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _disconnect();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Handle app lifecycle changes for reconnection
    if (state == AppLifecycleState.resumed) {
      final controllerState = ref.read(terminalControllerProvider);
      if (controllerState.currentSession != null &&
          !controllerState.currentSession!.isConnected) {
        _reconnect();
      }
    }
  }

  Future<void> _connect() async {
    if (widget.connection == null) return;

    try {
      final controller = ref.read(terminalControllerProvider.notifier);
      await controller.connect(widget.connection!);

      // Listen to terminal output and write to xterm
      final sessionId = ref.read(terminalControllerProvider).currentSession?.id;
      if (sessionId != null) {
        ref.listen(terminalOutputProvider(sessionId), (previous, next) {
          next.when(
            data: (output) {
              _terminal.write(output);
            },
            loading: () {},
            error: (error, stack) {
              _terminal.write('Error: $error\n');
            },
          );
        });

        // Listen to terminal input and send to SSH
        _terminal.onOutput = (data) {
          controller.sendInput(data);
        };

        // Handle terminal resize
        _terminal.onResize = (width, height, pixelWidth, pixelHeight) {
          controller.resize(width, height);
        };
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection failed: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  Future<void> _disconnect() async {
    final controller = ref.read(terminalControllerProvider.notifier);
    await controller.disconnect();
  }

  Future<void> _reconnect() async {
    if (widget.connection != null) {
      await _connect();
    }
  }

  void _toggleMobileKeyboard() {
    setState(() {
      _showMobileKeyboard = !_showMobileKeyboard;
    });
  }

  @override
  Widget build(BuildContext context) {
    final controllerState = ref.watch(terminalControllerProvider);
    final session = controllerState.currentSession;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.connection?.name ?? 'Terminal'),
        actions: [
          // Connection indicator
          if (session != null)
            Padding(
              padding: const EdgeInsets.only(right: 8.0),
              child: ConnectionIndicator(state: session.state),
            ),
          // Keyboard toggle
          IconButton(
            icon: Icon(_showMobileKeyboard ? Icons.keyboard_hide : Icons.keyboard),
            onPressed: _toggleMobileKeyboard,
            tooltip: _showMobileKeyboard ? 'Hide keyboard' : 'Show keyboard',
          ),
          // Settings menu
          PopupMenuButton<String>(
            onSelected: (value) {
              switch (value) {
                case 'reconnect':
                  _reconnect();
                  break;
                case 'disconnect':
                  _disconnect();
                  Navigator.of(context).pop();
                  break;
                case 'clear':
                  _terminal.buffer.clear();
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'reconnect',
                child: Row(
                  children: [
                    Icon(Icons.refresh),
                    SizedBox(width: 8),
                    Text('Reconnect'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'clear',
                child: Row(
                  children: [
                    Icon(Icons.clear_all),
                    SizedBox(width: 8),
                    Text('Clear terminal'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'disconnect',
                child: Row(
                  children: [
                    Icon(Icons.close),
                    SizedBox(width: 8),
                    Text('Disconnect'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // Error message banner
          if (controllerState.errorMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              color: AppColors.errorLight,
              child: Row(
                children: [
                  const Icon(Icons.error, color: AppColors.error),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      controllerState.errorMessage!,
                      style: const TextStyle(color: AppColors.error),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: () {
                      ref.read(terminalControllerProvider.notifier).clearError();
                    },
                  ),
                ],
              ),
            ),

          // Terminal view
          Expanded(
            child: controllerState.isLoading
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Connecting...'),
                      ],
                    ),
                  )
                : session == null
                    ? const Center(
                        child: Text('Not connected'),
                      )
                    : TerminalView(
                        _terminal,
                        controller: _terminalController,
                        autofocus: true,
                        backgroundOpacity: 1.0,
                        padding: const EdgeInsets.all(8),
                        theme: TerminalTheme(
                          cursor: AppColors.primary,
                          selection: AppColors.primaryLight.withOpacity(0.3),
                          foreground: AppColors.textPrimaryDark,
                          background: AppColors.backgroundDark,
                          black: AppColors.neutral900,
                          red: AppColors.error,
                          green: AppColors.success,
                          yellow: AppColors.warning,
                          blue: AppColors.info,
                          magenta: AppColors.accent,
                          cyan: AppColors.secondary,
                          white: AppColors.neutral100,
                          brightBlack: AppColors.neutral700,
                          brightRed: AppColors.errorLight,
                          brightGreen: AppColors.successLight,
                          brightYellow: AppColors.warningLight,
                          brightBlue: AppColors.infoLight,
                          brightMagenta: AppColors.accentLight,
                          brightCyan: AppColors.secondaryLight,
                          brightWhite: AppColors.neutral50,
                        ),
                      ),
          ),

          // Mobile keyboard
          if (_showMobileKeyboard && session != null)
            MobileKeyboard(
              onInput: (text) {
                ref.read(terminalControllerProvider.notifier).sendInput(text);
              },
              onCommand: (command) {
                ref.read(terminalControllerProvider.notifier).sendInput('$command\n');
              },
            ),
        ],
      ),
    );
  }
}