import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/voice/presentation/providers/voice_provider.dart';

/// Hold-to-record button with visual feedback
/// Haptic feedback on interaction, color and scale changes while recording
class HoldToRecordButton extends ConsumerStatefulWidget {
  final VoidCallback? onRecordingStart;
  final VoidCallback? onRecordingStop;

  const HoldToRecordButton({
    super.key,
    this.onRecordingStart,
    this.onRecordingStop,
  });

  @override
  ConsumerState<HoldToRecordButton> createState() =>
      _HoldToRecordButtonState();
}

class _HoldToRecordButtonState extends ConsumerState<HoldToRecordButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _pulseAnimation;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );

    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeInOut,
      ),
    );

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeInOut,
      ),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _handlePressStart() {
    if (_isPressed) return;

    _isPressed = true;
    _animationController.forward();
    _animationController.repeat(reverse: true);

    // Haptic feedback
    HapticFeedback.mediumImpact();

    // Start recording
    widget.onRecordingStart?.call();
    ref.read(voiceNotifierProvider.notifier).startRecording();
  }

  void _handlePressEnd() {
    if (!_isPressed) return;

    _isPressed = false;
    _animationController.stop();
    _animationController.reverse();

    // Haptic feedback
    HapticFeedback.lightImpact();

    // Stop recording
    widget.onRecordingStop?.call();
    ref.read(voiceNotifierProvider.notifier).stopRecording();
  }

  @override
  Widget build(BuildContext context) {
    final isRecording = ref.watch(isRecordingProvider);
    final voiceState = ref.watch(voiceStateProvider);
    final isProcessing = voiceState?.status.name == 'processing';

    return GestureDetector(
      onLongPressStart: (_) => _handlePressStart(),
      onLongPressEnd: (_) => _handlePressEnd(),
      child: AnimatedBuilder(
        animation: _animationController,
        builder: (context, child) {
          return Transform.scale(
            scale: _isPressed ? _scaleAnimation.value : 1.0,
            child: Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _isPressed ? AppColors.error : AppColors.primary,
                boxShadow: [
                  BoxShadow(
                    color: (_isPressed ? AppColors.error : AppColors.primary)
                        .withOpacity(0.3 * _pulseAnimation.value),
                    blurRadius: 20 * _pulseAnimation.value,
                    spreadRadius: 5 * _pulseAnimation.value,
                  ),
                ],
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Outer pulse ring when recording
                  if (isRecording)
                    Transform.scale(
                      scale: _pulseAnimation.value,
                      child: Container(
                        width: 100,
                        height: 100,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: Colors.white.withOpacity(0.5),
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                  // Icon
                  Icon(
                    isProcessing
                        ? Icons.hourglass_empty
                        : (isRecording ? Icons.stop : Icons.mic),
                    size: 48,
                    color: Colors.white,
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Text instructions below the button
class RecordingInstructions extends ConsumerWidget {
  const RecordingInstructions({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isRecording = ref.watch(isRecordingProvider);
    final voiceState = ref.watch(voiceStateProvider);
    final recordingDuration = voiceState?.recordingDuration;

    return Column(
      children: [
        Text(
          isRecording ? 'Release to stop' : 'Hold to record',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: AppColors.textSecondaryLight,
              ),
        ),
        if (isRecording && recordingDuration != null) ...[
          const SizedBox(height: 8),
          Text(
            _formatDuration(recordingDuration),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: AppColors.error,
                  fontWeight: FontWeight.bold,
                ),
          ),
        ],
      ],
    );
  }

  String _formatDuration(Duration duration) {
    final minutes = duration.inMinutes.toString().padLeft(2, '0');
    final seconds = (duration.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }
}
