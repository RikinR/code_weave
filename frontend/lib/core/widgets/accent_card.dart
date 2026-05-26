/// Card container with a colored left accent stripe.
///
/// Used on the home repository grid, pipeline stage tiles, and sidebar panels.
library;
import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Surface card with optional [accentColor] stripe and tap handler.
class AccentCard extends StatelessWidget {
  const AccentCard({
    super.key,
    required this.child,
    this.accentColor,
    this.onTap,
    this.padding = const EdgeInsets.all(16),
    this.fillHeight = false,
  });

  final Widget child;
  final Color? accentColor;
  final VoidCallback? onTap;
  final EdgeInsets padding;

  /// When true, expands to fill available height in grid layouts.
  final bool fillHeight;

  @override
  Widget build(BuildContext context) {
    final accent = accentColor ?? AppTheme.accent;

    Widget inner = Padding(padding: padding, child: child);
    if (fillHeight) {
      inner = SizedBox(width: double.infinity, height: double.infinity, child: inner);
    }

    final card = Container(
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.border),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Row(
          crossAxisAlignment:
              fillHeight ? CrossAxisAlignment.stretch : CrossAxisAlignment.start,
          children: [
            Container(width: 3, color: accent.withValues(alpha: 0.85)),
            Expanded(child: inner),
          ],
        ),
      ),
    );

    if (onTap == null) return card;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: card,
    );
  }
}
