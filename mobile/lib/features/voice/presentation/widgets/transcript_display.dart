import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:paraclete/core/theme/colors.dart';
import 'package:paraclete/features/voice/presentation/providers/voice_provider.dart';

/// Transcript display widget
/// Shows both interim and final transcription results with visual distinction
/// Auto-scrolls as new text appears
class TranscriptDisplay extends ConsumerStatefulWidget {
  final double maxHeight;
  final EdgeInsets padding;

  const TranscriptDisplay({
    super.key,
    this.maxHeight = 300,
    this.padding = const EdgeInsets.all(16),
  });

  @override
  ConsumerState<TranscriptDisplay> createState() => _TranscriptDisplayState();
}

class _TranscriptDisplayState extends ConsumerState<TranscriptDisplay> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final fullTranscript = ref.watch(fullTranscriptProvider);
    final interimTranscript = ref.watch(interimTranscriptProvider);
    final voiceState = ref.watch(voiceStateProvider);
    final hasError = voiceState?.error != null;

    // Auto-scroll when transcript changes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (fullTranscript.isNotEmpty || interimTranscript.isNotEmpty) {
        _scrollToBottom();
      }
    });

    return Container(
      constraints: BoxConstraints(maxHeight: widget.maxHeight),
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
          // Header
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.text_fields,
                      size: 20,
                      color: AppColors.textSecondaryLight,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Transcript',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ],
                ),
                if (fullTranscript.isNotEmpty)
                  IconButton(
                    icon: const Icon(Icons.clear, size: 20),
                    onPressed: () {
                      ref.read(voiceNotifierProvider.notifier).clearTranscripts();
                    },
                    tooltip: 'Clear transcript',
                  ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Transcript content
          Expanded(
            child: hasError
                ? _ErrorDisplay(error: voiceState!.error!)
                : (fullTranscript.isEmpty && interimTranscript.isEmpty)
                    ? _EmptyState()
                    : SingleChildScrollView(
                        controller: _scrollController,
                        padding: widget.padding,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Final transcript
                            if (fullTranscript.isNotEmpty)
                              SelectableText(
                                fullTranscript,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyLarge
                                    ?.copyWith(
                                      height: 1.5,
                                    ),
                              ),

                            // Interim transcript (with visual distinction)
                            if (interimTranscript.isNotEmpty) ...[
                              if (fullTranscript.isNotEmpty)
                                const SizedBox(height: 8),
                              SelectableText(
                                interimTranscript,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyLarge
                                    ?.copyWith(
                                      height: 1.5,
                                      color: AppColors.textSecondaryLight,
                                      fontStyle: FontStyle.italic,
                                    ),
                              ),
                            ],
                          ],
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

/// Empty state when no transcript is available
class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.mic_none,
              size: 48,
              color: AppColors.textTertiaryLight,
            ),
            const SizedBox(height: 16),
            Text(
              'Hold the button to start recording',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondaryLight,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Your speech will be transcribed in real-time',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textTertiaryLight,
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Error display
class _ErrorDisplay extends StatelessWidget {
  final String error;

  const _ErrorDisplay({required this.error});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: AppColors.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Transcription Error',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: AppColors.error,
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              error,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondaryLight,
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Compact transcript preview (for use in other screens)
class TranscriptPreview extends ConsumerWidget {
  final int maxLines;

  const TranscriptPreview({
    super.key,
    this.maxLines = 3,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final fullTranscript = ref.watch(fullTranscriptProvider);
    final interimTranscript = ref.watch(interimTranscriptProvider);

    final displayText = fullTranscript.isNotEmpty
        ? fullTranscript
        : (interimTranscript.isNotEmpty
            ? interimTranscript
            : 'No transcript available');

    return Text(
      displayText,
      style: Theme.of(context).textTheme.bodyMedium,
      maxLines: maxLines,
      overflow: TextOverflow.ellipsis,
    );
  }
}
