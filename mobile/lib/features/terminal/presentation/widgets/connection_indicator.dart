import 'package:flutter/material.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/terminal/domain/entities/terminal_session.dart';

/// Connection status indicator widget
class ConnectionIndicator extends StatelessWidget {
  final TerminalSessionState state;

  const ConnectionIndicator({
    super.key,
    required this.state,
  });

  @override
  Widget build(BuildContext context) {
    final (color, icon, label) = _getStateInfo(state);

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 6),
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  (Color, IconData, String) _getStateInfo(TerminalSessionState state) {
    switch (state) {
      case TerminalSessionState.connected:
        return (AppColors.success, Icons.cloud_done, 'Connected');
      case TerminalSessionState.connecting:
        return (AppColors.warning, Icons.cloud_sync, 'Connecting');
      case TerminalSessionState.reconnecting:
        return (AppColors.warning, Icons.refresh, 'Reconnecting');
      case TerminalSessionState.disconnecting:
        return (AppColors.neutral500, Icons.cloud_off, 'Disconnecting');
      case TerminalSessionState.disconnected:
        return (AppColors.neutral500, Icons.cloud_off, 'Disconnected');
      case TerminalSessionState.error:
        return (AppColors.error, Icons.error, 'Error');
    }
  }
}

/// Compact connection indicator (just the dot and icon)
class CompactConnectionIndicator extends StatelessWidget {
  final TerminalSessionState state;

  const CompactConnectionIndicator({
    super.key,
    required this.state,
  });

  @override
  Widget build(BuildContext context) {
    final color = _getColor(state);

    return Container(
      width: 12,
      height: 12,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: state == TerminalSessionState.connected
            ? [
                BoxShadow(
                  color: color.withOpacity(0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                )
              ]
            : null,
      ),
    );
  }

  Color _getColor(TerminalSessionState state) {
    switch (state) {
      case TerminalSessionState.connected:
        return AppColors.success;
      case TerminalSessionState.connecting:
      case TerminalSessionState.reconnecting:
        return AppColors.warning;
      case TerminalSessionState.disconnecting:
      case TerminalSessionState.disconnected:
        return AppColors.neutral500;
      case TerminalSessionState.error:
        return AppColors.error;
    }
  }
}
