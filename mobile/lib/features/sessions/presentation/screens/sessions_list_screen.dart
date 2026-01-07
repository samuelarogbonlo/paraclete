import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/shared/widgets/base_scaffold.dart';
import 'package:paraclete/shared/widgets/error_widget.dart';
import 'package:paraclete/shared/widgets/loading_indicator.dart';

/// Sessions list screen placeholder
class SessionsListScreen extends ConsumerWidget {
  const SessionsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return BaseScaffold(
      title: 'Sessions',
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          // Create new session
        },
        icon: const Icon(Icons.add),
        label: const Text('New Session'),
      ),
      body: Center(
        child: EmptyStateWidget(
          icon: Icons.folder_open_outlined,
          title: 'No Sessions Yet',
          message: 'Start a new coding session to get started',
          actionLabel: 'Create Session',
          onAction: () {
            // Create session action
          },
        ),
      ),
    );
  }
}