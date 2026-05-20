import 'package:flutter/material.dart';

class Responsive {
  static const double compactMax = 720;
  static const double mediumMax = 1100;

  static Size sizeOf(BuildContext context) => MediaQuery.sizeOf(context);

  static bool isCompact(BuildContext context) => sizeOf(context).width < compactMax;

  static bool isMedium(BuildContext context) {
    final w = sizeOf(context).width;
    return w >= compactMax && w < mediumMax;
  }

  static bool isExpanded(BuildContext context) => sizeOf(context).width >= mediumMax;

  static double horizontalPadding(BuildContext context) {
    if (isCompact(context)) return 12;
    if (isMedium(context)) return 16;
    return 24;
  }

  static int gridColumns(BuildContext context) {
    final w = sizeOf(context).width;
    if (w < 500) return 1;
    if (w < 900) return 2;
    if (w < 1400) return 3;
    return 4;
  }

  static double maxContentWidth(BuildContext context) {
    final w = sizeOf(context).width;
    return w > 1400 ? 1280 : w;
  }
}

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
