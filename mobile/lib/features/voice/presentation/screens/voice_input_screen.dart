import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/shared/widgets/base_scaffold.dart';

/// Voice input screen placeholder
class VoiceInputScreen extends ConsumerWidget {
  const VoiceInputScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return BaseScaffold(
      title: 'Voice Input',
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    AppColors.voiceWaveform.withOpacity(0.3),
                    AppColors.voiceWaveformActive.withOpacity(0.3),
                  ],
                ),
              ),
              child: const Icon(
                Icons.mic,
                size: 60,
                color: AppColors.voiceWaveform,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Voice Input',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Voice features will be implemented here',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 48),
            ElevatedButton.icon(
              onPressed: () {
                // Placeholder action
              },
              icon: const Icon(Icons.mic),
              label: const Text('Hold to Record'),
            ),
          ],
        ),
      ),
    );
  }
}