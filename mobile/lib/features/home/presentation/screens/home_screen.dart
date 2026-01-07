import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:paraclete/core/config/routes.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/shared/widgets/base_scaffold.dart';

/// Home screen - main dashboard
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return BaseScaffold(
      title: 'Paraclete',
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Welcome card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome to Paraclete',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Mobile-first AI coding platform',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Quick actions grid
            Expanded(
              child: GridView.count(
                crossAxisCount: 2,
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                children: [
                  _QuickActionCard(
                    icon: Icons.mic,
                    label: 'Voice Input',
                    color: AppColors.voiceWaveform,
                    onTap: () => context.push(Routes.voice),
                  ),
                  _QuickActionCard(
                    icon: Icons.terminal,
                    label: 'Terminal',
                    color: AppColors.terminalGreen,
                    onTap: () => context.push(Routes.terminal),
                  ),
                  _QuickActionCard(
                    icon: Icons.smart_toy,
                    label: 'AI Agents',
                    color: AppColors.supervisorColor,
                    onTap: () => context.push(Routes.agents),
                  ),
                  _QuickActionCard(
                    icon: Icons.folder_open,
                    label: 'Sessions',
                    color: AppColors.primary,
                    onTap: () => context.push(Routes.sessions),
                  ),
                  _QuickActionCard(
                    icon: Icons.code,
                    label: 'Git & PRs',
                    color: AppColors.accent,
                    onTap: () => context.push(Routes.git),
                  ),
                  _QuickActionCard(
                    icon: Icons.settings,
                    label: 'Settings',
                    color: AppColors.neutral600,
                    onTap: () => context.push(Routes.settings),
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

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                size: 32,
                color: color,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              label,
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}