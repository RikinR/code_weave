/// Reusable branding widgets for logos and titled headers.
///
/// Used on the home screen hero, pipeline app bar, and explorer navigation.
library;
import 'package:flutter/material.dart';

import '../brand/app_brand.dart';

/// Full Code Weave logo scaled to [height].
class AppLogo extends StatelessWidget {
  const AppLogo({
    super.key,
    this.height = 72,
    this.semanticLabel = AppBrand.name,
  });

  final double height;
  final String semanticLabel;

  @override
  Widget build(BuildContext context) {
    final width = height * AppBrand.logoAspectRatio;
    return Image.asset(
      AppBrand.logoAsset,
      height: height,
      width: width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      semanticLabel: semanticLabel,
    );
  }
}

/// Square logo icon for compact app bars and title rows.
class AppLogoMark extends StatelessWidget {
  const AppLogoMark({
    super.key,
    this.size = 36,
  });

  final double size;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      AppBrand.logoIconAsset,
      width: size,
      height: size,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      semanticLabel: AppBrand.name,
    );
  }
}

/// Horizontal row pairing [AppLogoMark] with a screen [title].
class AppBrandTitleRow extends StatelessWidget {
  const AppBrandTitleRow({
    super.key,
    required this.title,
    this.logoSize = 36,
  });

  final String title;
  final double logoSize;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        AppLogoMark(size: logoSize),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

/// Home screen header showing the full logo, sized for [compact] layouts.
class HomeBrandHeader extends StatelessWidget {
  const HomeBrandHeader({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: AppLogo(height: compact ? 64 : 88),
    );
  }
}
