import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:paraclete/core/config/routes.dart';
import 'package:paraclete/shared/providers/core_providers.dart';
import 'package:paraclete/shared/widgets/base_scaffold.dart';

/// Settings screen
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appSettings = ref.watch(appSettingsProvider);

    return BaseScaffold(
      title: 'Settings',
      body: ListView(
        children: [
          // Appearance section
          _SettingsSection(
            title: 'Appearance',
            children: [
              SwitchListTile(
                title: const Text('Dark Mode'),
                subtitle: const Text('Use dark theme'),
                value: appSettings.isDarkMode,
                onChanged: (value) {
                  ref.read(appSettingsProvider.notifier).toggleDarkMode();
                },
              ),
            ],
          ),

          // API Keys section
          _SettingsSection(
            title: 'API Keys',
            children: [
              ListTile(
                leading: const Icon(Icons.key),
                title: const Text('Manage API Keys'),
                subtitle: const Text('Configure your AI provider keys'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push(Routes.apiKeys),
              ),
            ],
          ),

          // Voice settings
          _SettingsSection(
            title: 'Voice',
            children: [
              ListTile(
                leading: const Icon(Icons.language),
                title: const Text('Language'),
                subtitle: Text(appSettings.voiceLanguage),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // Show language selector
                },
              ),
              ListTile(
                leading: const Icon(Icons.record_voice_over),
                title: const Text('Voice Model'),
                subtitle: Text(appSettings.voiceModel),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // Show model selector
                },
              ),
            ],
          ),

          // Notifications
          _SettingsSection(
            title: 'Notifications',
            children: [
              SwitchListTile(
                title: const Text('Push Notifications'),
                subtitle: const Text('Receive notifications for agent tasks'),
                value: appSettings.notificationsEnabled,
                onChanged: (value) {
                  ref
                      .read(appSettingsProvider.notifier)
                      .setNotificationsEnabled(value);
                },
              ),
            ],
          ),

          // About section
          _SettingsSection(
            title: 'About',
            children: [
              ListTile(
                leading: const Icon(Icons.info_outline),
                title: const Text('Version'),
                subtitle: const Text('1.0.0 (Build 1)'),
              ),
              ListTile(
                leading: const Icon(Icons.code),
                title: const Text('Source Code'),
                subtitle: const Text('View on GitHub'),
                trailing: const Icon(Icons.open_in_new),
                onTap: () {
                  // Open GitHub
                },
              ),
            ],
          ),

          // Sign out
          const SizedBox(height: 24),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: OutlinedButton.icon(
              onPressed: () async {
                await ref.read(authProvider.notifier).logout();
                if (context.mounted) {
                  context.go(Routes.login);
                }
              },
              icon: const Icon(Icons.logout),
              label: const Text('Sign Out'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red,
                side: const BorderSide(color: Colors.red),
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _SettingsSection({
    required this.title,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.bold,
                ),
          ),
        ),
        ...children,
        const Divider(height: 1),
      ],
    );
  }
}