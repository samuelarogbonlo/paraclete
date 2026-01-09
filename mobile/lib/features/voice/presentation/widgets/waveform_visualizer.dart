import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/voice/presentation/providers/voice_provider.dart';

/// Waveform visualization widget during recording
/// Shows real-time audio level display with smooth animation
class WaveformVisualizer extends ConsumerStatefulWidget {
  final double height;
  final int barCount;

  const WaveformVisualizer({
    super.key,
    this.height = 80,
    this.barCount = 30,
  });

  @override
  ConsumerState<WaveformVisualizer> createState() =>
      _WaveformVisualizerState();
}

class _WaveformVisualizerState extends ConsumerState<WaveformVisualizer>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  final List<double> _barHeights = [];
  final math.Random _random = math.Random();

  @override
  void initState() {
    super.initState();

    // Initialize bar heights
    _barHeights.addAll(List.generate(widget.barCount, (_) => 0.1));

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    )..addListener(() {
        if (mounted) {
          setState(() {
            _updateBarHeights();
          });
        }
      });
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _updateBarHeights() {
    final isRecording = ref.read(isRecordingProvider);
    final audioLevel = ref.read(voiceStateProvider)?.audioLevel ?? 0.0;

    if (isRecording) {
      // Simulate audio level changes (in production, use actual audio levels)
      final baseLevel = audioLevel > 0 ? audioLevel : _random.nextDouble() * 0.8;

      for (int i = 0; i < _barHeights.length; i++) {
        final randomVariation = _random.nextDouble() * 0.3;
        final targetHeight = (baseLevel + randomVariation).clamp(0.1, 1.0);

        // Smooth transition
        _barHeights[i] += (targetHeight - _barHeights[i]) * 0.3;
      }
    } else {
      // Fade out when not recording
      for (int i = 0; i < _barHeights.length; i++) {
        _barHeights[i] *= 0.9;
        if (_barHeights[i] < 0.1) _barHeights[i] = 0.1;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isRecording = ref.watch(isRecordingProvider);

    // Start/stop animation based on recording state
    if (isRecording && !_animationController.isAnimating) {
      _animationController.repeat();
    } else if (!isRecording && _animationController.isAnimating) {
      _animationController.stop();
    }

    return Container(
      height: widget.height,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: List.generate(
          widget.barCount,
          (index) => _WaveformBar(
            height: widget.height * _barHeights[index],
            color: isRecording ? AppColors.primary : AppColors.neutral300,
          ),
        ),
      ),
    );
  }
}

/// Individual waveform bar
class _WaveformBar extends StatelessWidget {
  final double height;
  final Color color;

  const _WaveformBar({
    required this.height,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 100),
      width: 3,
      height: height,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }
}

/// Audio level indicator (simple version)
class AudioLevelIndicator extends ConsumerWidget {
  final double size;

  const AudioLevelIndicator({
    super.key,
    this.size = 200,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isRecording = ref.watch(isRecordingProvider);
    final audioLevel = ref.watch(voiceStateProvider)?.audioLevel ?? 0.0;

    if (!isRecording) {
      return const SizedBox.shrink();
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.primary.withOpacity(0.1),
        border: Border.all(
          color: AppColors.primary.withOpacity(0.3),
          width: 2,
        ),
      ),
      child: Center(
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 100),
          width: size * audioLevel.clamp(0.2, 1.0),
          height: size * audioLevel.clamp(0.2, 1.0),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.primary.withOpacity(0.3),
          ),
        ),
      ),
    );
  }
}
