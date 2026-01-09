import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/storage/secure_storage.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/voice/domain/entities/voice_state.dart';
import 'package:paraclete/features/voice/presentation/providers/voice_provider.dart';
import 'package:paraclete/features/voice/presentation/widgets/hold_to_record_button.dart';
import 'package:paraclete/features/voice/presentation/widgets/transcript_display.dart';
import 'package:paraclete/features/voice/presentation/widgets/tts_controls.dart';
import 'package:paraclete/features/voice/presentation/widgets/waveform_visualizer.dart';

/// Voice input screen with complete voice interaction UI
class VoiceInputScreen extends ConsumerStatefulWidget {
  const VoiceInputScreen({super.key});

  @override
  ConsumerState<VoiceInputScreen> createState() => _VoiceInputScreenState();
}

class _VoiceInputScreenState extends ConsumerState<VoiceInputScreen> {
  @override
  void initState() {
    super.initState();
    _checkApiKeys();
  }

  Future<void> _checkApiKeys() async {
    final secureStorage = ref.read(secureStorageProvider);
    final deepgramKey = await secureStorage.getApiKey(
      SecureStorageKey.deepgramKey,
    );
    final elevenLabsKey = await secureStorage.getApiKey(
      SecureStorageKey.elevenLabsKey,
    );

    if (deepgramKey == null || elevenLabsKey == null) {
      if (mounted) {
        _showApiKeyDialog();
      }
    }
  }

  void _showApiKeyDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('API Keys Required'),
        content: const Text(
          'Voice features require Deepgram and ElevenLabs API keys. '
          'Please configure them in Settings.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Later'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
            },
            child: const Text('Go to Settings'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(voiceNotifierProvider);
    final voiceState = asyncState.valueOrNull;
    final isRecording = voiceState?.isRecording ?? false;
    final isPlaying = voiceState?.isPlaying ?? false;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Voice Input'),
        actions: [
          _StatusIndicator(status: voiceState?.status),
          const SizedBox(width: 8),
          if (isRecording || isPlaying)
            IconButton(
              icon: const Icon(Icons.cancel),
              onPressed: () {
                ref.read(voiceNotifierProvider.notifier).cancelOperation();
              },
              tooltip: 'Cancel',
            ),
        ],
      ),
      body: SafeArea(
        child: asyncState.when(
          data: (state) => _buildContent(context, state),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, stack) => _buildError(context, error),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, VoiceState state) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const WaveformVisualizer(height: 80, barCount: 30),
          const SizedBox(height: 32),
          const HoldToRecordButton(),
          const SizedBox(height: 16),
          const RecordingInstructions(),
          const SizedBox(height: 32),
          const TranscriptDisplay(maxHeight: 300),
          const SizedBox(height: 24),
          if (state.currentOutput != null || state.isPlaying)
            const TtsControls(),
          if (ref.watch(fullTranscriptProvider).isNotEmpty &&
              !state.isPlaying) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () {
                final transcript = ref.read(fullTranscriptProvider);
                ref.read(voiceNotifierProvider.notifier).speakText(transcript);
              },
              icon: const Icon(Icons.volume_up),
              label: const Text('Test TTS with Transcript'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildError(BuildContext context, Object error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: AppColors.error),
            const SizedBox(height: 16),
            Text('Voice Error',
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(color: AppColors.error, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(error.toString(),
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center),
            const SizedBox(height: 24),
            ElevatedButton(
                onPressed: () => ref.invalidate(voiceNotifierProvider),
                child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

class _StatusIndicator extends StatelessWidget {
  final VoiceStatus? status;
  const _StatusIndicator({this.status});

  @override
  Widget build(BuildContext context) {
    if (status == null || status == VoiceStatus.idle) return const SizedBox.shrink();
    final (color, text) = _getStatusInfo(status!);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Text(text, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  (Color, String) _getStatusInfo(VoiceStatus status) {
    switch (status) {
      case VoiceStatus.idle: return (AppColors.neutral500, 'Idle');
      case VoiceStatus.initializing: return (AppColors.secondary, 'Initializing');
      case VoiceStatus.recording: return (AppColors.error, 'Recording');
      case VoiceStatus.processing: return (AppColors.secondary, 'Processing');
      case VoiceStatus.speaking: return (AppColors.primary, 'Speaking');
      case VoiceStatus.error: return (AppColors.error, 'Error');
    }
  }
}
