import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/voice/domain/entities/voice_output.dart';
import 'package:paraclete/features/voice/presentation/providers/voice_provider.dart';

/// TTS playback controls widget
/// Play/pause, stop, and progress indicator for synthesized speech
class TtsControls extends ConsumerWidget {
  final String? textToSpeak;
  final VoidCallback? onPlaybackComplete;

  const TtsControls({
    super.key,
    this.textToSpeak,
    this.onPlaybackComplete,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isPlaying = ref.watch(isPlayingProvider);
    final voiceState = ref.watch(voiceStateProvider);
    final currentOutput = voiceState?.currentOutput;

    if (currentOutput == null && !isPlaying && textToSpeak == null) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? AppColors.cardDark
            : AppColors.cardLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Theme.of(context).brightness == Brightness.dark
              ? AppColors.borderDark
              : AppColors.borderLight,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.volume_up,
                size: 20,
                color: AppColors.textSecondaryLight,
              ),
              const SizedBox(width: 8),
              Text(
                'Audio Playback',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const Spacer(),
              _StatusBadge(status: currentOutput?.status),
            ],
          ),
          const SizedBox(height: 16),

          // Text being spoken
          if (currentOutput?.text != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).brightness == Brightness.dark
                    ? AppColors.neutral800
                    : AppColors.neutral100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                currentOutput!.text,
                style: Theme.of(context).textTheme.bodyMedium,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),

          const SizedBox(height: 16),

          // Controls
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Play/Pause button
              _ControlButton(
                icon: isPlaying ? Icons.pause : Icons.play_arrow,
                label: isPlaying ? 'Pause' : 'Play',
                onPressed: () {
                  if (isPlaying) {
                    ref.read(voiceNotifierProvider.notifier).pausePlayback();
                  } else if (currentOutput != null) {
                    ref.read(voiceNotifierProvider.notifier).resumePlayback();
                  } else if (textToSpeak != null) {
                    ref
                        .read(voiceNotifierProvider.notifier)
                        .speakText(textToSpeak!);
                  }
                },
              ),
              const SizedBox(width: 16),

              // Stop button
              _ControlButton(
                icon: Icons.stop,
                label: 'Stop',
                onPressed: () {
                  ref.read(voiceNotifierProvider.notifier).stopPlayback();
                  onPlaybackComplete?.call();
                },
                isSecondary: true,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Status badge for current playback status
class _StatusBadge extends StatelessWidget {
  final VoiceOutputStatus? status;

  const _StatusBadge({this.status});

  @override
  Widget build(BuildContext context) {
    if (status == null) return const SizedBox.shrink();

    final (color, text) = _getStatusInfo(status!);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  (Color, String) _getStatusInfo(VoiceOutputStatus status) {
    switch (status) {
      case VoiceOutputStatus.pending:
        return (AppColors.neutral500, 'Pending');
      case VoiceOutputStatus.playing:
        return (AppColors.primary, 'Playing');
      case VoiceOutputStatus.paused:
        return (AppColors.secondary, 'Paused');
      case VoiceOutputStatus.completed:
        return (AppColors.success, 'Completed');
      case VoiceOutputStatus.error:
        return (AppColors.error, 'Error');
    }
  }
}

/// Control button widget
class _ControlButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onPressed;
  final bool isSecondary;

  const _ControlButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.isSecondary = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor:
                isSecondary ? AppColors.neutral300 : AppColors.primary,
            foregroundColor: isSecondary ? AppColors.textPrimaryLight : Colors.white,
            shape: const CircleBorder(),
            padding: const EdgeInsets.all(16),
          ),
          child: Icon(icon, size: 28),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: AppColors.textSecondaryLight,
              ),
        ),
      ],
    );
  }
}

/// Simple TTS trigger button (for use in other screens)
class TtsTriggerButton extends ConsumerWidget {
  final String text;
  final String? label;

  const TtsTriggerButton({
    super.key,
    required this.text,
    this.label,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isPlaying = ref.watch(isPlayingProvider);

    return IconButton(
      icon: Icon(isPlaying ? Icons.stop : Icons.volume_up),
      onPressed: () {
        if (isPlaying) {
          ref.read(voiceNotifierProvider.notifier).stopPlayback();
        } else {
          ref.read(voiceNotifierProvider.notifier).speakText(text);
        }
      },
      tooltip: label ?? (isPlaying ? 'Stop' : 'Speak'),
    );
  }
}
