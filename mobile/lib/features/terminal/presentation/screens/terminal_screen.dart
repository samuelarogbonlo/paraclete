import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/shared/widgets/base_scaffold.dart';

/// Terminal screen placeholder
class TerminalScreen extends ConsumerWidget {
  const TerminalScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return BaseScaffold(
      title: 'Terminal',
      backgroundColor: AppColors.terminalBackground,
      body: Container(
        color: AppColors.terminalBackground,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Terminal',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: AppColors.terminalText,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'SSH terminal will be implemented here',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.terminalText,
                  ),
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.terminalGreen),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '> ssh user@server',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      color: AppColors.terminalGreen,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Connecting...',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      color: AppColors.terminalText,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}