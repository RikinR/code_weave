/// Responsive layout breakpoints and content constraints.
///
/// Used by home, pipeline, and explorer screens to adapt grids, side panels,
/// and padding for compact, medium, and expanded viewports.
library;
import 'package:flutter/material.dart';

/// Breakpoint helpers for adaptive layouts across feature screens.
class Responsive {
  /// Maximum width treated as compact (phone) layout.
  static const double compactMax = 720;

  /// Maximum width treated as medium (tablet) layout.
  static const double mediumMax = 1100;

  /// Returns the current viewport size.
  static Size sizeOf(BuildContext context) => MediaQuery.sizeOf(context);

  /// True when viewport width is below [compactMax].
  static bool isCompact(BuildContext context) => sizeOf(context).width < compactMax;

  /// True when viewport width is between [compactMax] and [mediumMax].
  static bool isMedium(BuildContext context) {
    final w = sizeOf(context).width;
    return w >= compactMax && w < mediumMax;
  }

  /// True when viewport width is at or above [mediumMax].
  static bool isExpanded(BuildContext context) => sizeOf(context).width >= mediumMax;

  /// Horizontal page padding scaled by breakpoint.
  static double horizontalPadding(BuildContext context) {
    if (isCompact(context)) return 12;
    if (isMedium(context)) return 16;
    return 24;
  }

  /// Column count for the home repository grid.
  static int gridColumns(BuildContext context) {
    final w = sizeOf(context).width;
    if (w < 500) return 1;
    if (w < 900) return 2;
    if (w < 1400) return 3;
    return 4;
  }

  /// Maximum content width for centered layouts (e.g. pipeline stages).
  static double maxContentWidth(BuildContext context) {
    final w = sizeOf(context).width;
    return w > 1400 ? 1280 : w;
  }
}

/// Centers [child] with responsive horizontal padding and optional [maxWidth].
class ResponsiveBody extends StatelessWidget {
  const ResponsiveBody({
    super.key,
    required this.child,
    this.maxWidth = 1280,
  });

  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: Responsive.horizontalPadding(context),
            vertical: Responsive.isCompact(context) ? 12 : 20,
          ),
          child: child,
        ),
      ),
    );
  }
}
