/// Progress indicators for long-running home, pipeline, and explorer operations.
///
/// [TopProgressBar] sits under app bars; [OperationProgressOverlay] blocks
/// interaction during uploads, indexing, and repository loading.
library;
import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Thin indeterminate or determinate bar shown at the top of feature screens.
class TopProgressBar extends StatelessWidget {
  const TopProgressBar({
    super.key,
    required this.active,
    this.value,
  });

  /// When false, renders nothing.
  final bool active;

  /// Optional progress fraction (0–1); null shows indeterminate animation.
  final double? value;

  @override
  Widget build(BuildContext context) {
    if (!active) return const SizedBox.shrink();
    return ClipRRect(
      child: LinearProgressIndicator(
        value: value,
        minHeight: 3,
        backgroundColor: AppTheme.surfaceHigh,
        color: AppTheme.accent,
      ),
    );
  }
}

/// Modal overlay with progress bar and status [message] during blocking work.
class OperationProgressOverlay extends StatelessWidget {
  const OperationProgressOverlay({
    super.key,
    required this.visible,
    required this.message,
    this.progress,
  });

  /// When false, renders nothing.
  final bool visible;

  /// User-facing status text (e.g. upload or delete in progress).
  final String message;

  /// Optional progress fraction (0–1); null shows indeterminate animation.
  final double? progress;

  @override
  Widget build(BuildContext context) {
    if (!visible) return const SizedBox.shrink();
    return Stack(
      children: [
        ModalBarrier(
          dismissible: false,
          color: Colors.black.withValues(alpha: 0.45),
        ),
        Center(
          child: Material(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(12),
            elevation: 8,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minWidth: 280, maxWidth: 400),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: double.infinity,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: progress,
                          minHeight: 6,
                          backgroundColor: AppTheme.surfaceHigh,
                          color: AppTheme.accent,
                        ),
                      ),
                    ),
                    const SizedBox(height: 18),
                    Text(
                      message,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w500,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
