import 'package:flutter/material.dart';
import 'package:paraclete/core/theme/colors.dart';

/// Mobile keyboard widget for terminal input
class MobileKeyboard extends StatefulWidget {
  final Function(String) onInput;
  final Function(String) onCommand;

  const MobileKeyboard({
    super.key,
    required this.onInput,
    required this.onCommand,
  });

  @override
  State<MobileKeyboard> createState() => _MobileKeyboardState();
}

class _MobileKeyboardState extends State<MobileKeyboard> {
  bool _ctrlPressed = false;
  int _selectedCommandIndex = 0;

  // Common dev commands
  final List<String> _commonCommands = [
    'ls -la',
    'cd',
    'pwd',
    'git status',
    'git pull',
    'git push',
    'vim',
    'nano',
    'cat',
    'grep',
    'find',
    'docker ps',
    'npm install',
    'python',
    'clear',
    'exit',
  ];

  void _sendKey(String key) {
    if (_ctrlPressed) {
      // Send Ctrl+key combination
      final ctrlCode = key.codeUnitAt(0) - 64; // Ctrl+A = 1, Ctrl+B = 2, etc.
      widget.onInput(String.fromCharCode(ctrlCode));
      setState(() {
        _ctrlPressed = false;
      });
    } else {
      widget.onInput(key);
    }
  }

  void _sendEscape() {
    widget.onInput('\x1b');
  }

  void _sendTab() {
    widget.onInput('\t');
  }

  void _sendArrow(String direction) {
    final escapeSequences = {
      'up': '\x1b[A',
      'down': '\x1b[B',
      'right': '\x1b[C',
      'left': '\x1b[D',
    };
    widget.onInput(escapeSequences[direction]!);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? AppColors.surfaceDark
            : AppColors.surfaceLight,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).brightness == Brightness.dark
                ? AppColors.borderDark
                : AppColors.borderLight,
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Common commands row
          SizedBox(
            height: 48,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              itemCount: _commonCommands.length,
              itemBuilder: (context, index) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: ActionChip(
                    label: Text(
                      _commonCommands[index],
                      style: const TextStyle(fontSize: 13),
                    ),
                    onPressed: () {
                      widget.onCommand(_commonCommands[index]);
                    },
                    backgroundColor: _selectedCommandIndex == index
                        ? AppColors.primaryLight
                        : null,
                  ),
                );
              },
            ),
          ),

          const Divider(height: 1),

          // Special keys row
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                // Ctrl key (toggle)
                _KeyButton(
                  label: 'Ctrl',
                  isActive: _ctrlPressed,
                  onPressed: () {
                    setState(() {
                      _ctrlPressed = !_ctrlPressed;
                    });
                  },
                ),
                const SizedBox(width: 4),

                // Esc key
                _KeyButton(
                  label: 'Esc',
                  onPressed: _sendEscape,
                ),
                const SizedBox(width: 4),

                // Tab key
                _KeyButton(
                  label: 'Tab',
                  onPressed: _sendTab,
                ),
                const SizedBox(width: 4),

                const Spacer(),

                // Arrow keys
                Column(
                  children: [
                    _IconKeyButton(
                      icon: Icons.keyboard_arrow_up,
                      onPressed: () => _sendArrow('up'),
                    ),
                    Row(
                      children: [
                        _IconKeyButton(
                          icon: Icons.keyboard_arrow_left,
                          onPressed: () => _sendArrow('left'),
                        ),
                        _IconKeyButton(
                          icon: Icons.keyboard_arrow_down,
                          onPressed: () => _sendArrow('down'),
                        ),
                        _IconKeyButton(
                          icon: Icons.keyboard_arrow_right,
                          onPressed: () => _sendArrow('right'),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Additional control keys
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
            child: Row(
              children: [
                Expanded(
                  child: _KeyButton(
                    label: 'Ctrl+C',
                    onPressed: () {
                      widget.onInput('\x03'); // Ctrl+C
                    },
                  ),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: _KeyButton(
                    label: 'Ctrl+D',
                    onPressed: () {
                      widget.onInput('\x04'); // Ctrl+D
                    },
                  ),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: _KeyButton(
                    label: 'Ctrl+Z',
                    onPressed: () {
                      widget.onInput('\x1a'); // Ctrl+Z
                    },
                  ),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: _KeyButton(
                    label: 'Ctrl+L',
                    onPressed: () {
                      widget.onInput('\x0c'); // Ctrl+L (clear)
                    },
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 4),
        ],
      ),
    );
  }
}

/// Custom key button widget
class _KeyButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;
  final bool isActive;

  const _KeyButton({
    required this.label,
    required this.onPressed,
    this.isActive = false,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        minimumSize: const Size(0, 36),
        backgroundColor: isActive ? AppColors.primary : null,
        foregroundColor: isActive ? Colors.white : null,
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 13),
      ),
    );
  }
}

/// Icon-based key button
class _IconKeyButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onPressed;

  const _IconKeyButton({
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(icon, size: 20),
      onPressed: onPressed,
      padding: EdgeInsets.zero,
      constraints: const BoxConstraints(
        minWidth: 32,
        minHeight: 32,
      ),
    );
  }
}
