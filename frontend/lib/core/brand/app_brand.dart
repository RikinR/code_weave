/// Shared branding constants for logos, product name, and tagline.
///
/// Used across home, pipeline, and explorer screens for consistent identity.
library;
class AppBrand {
  AppBrand._();

  /// Full-width logo asset shown on the home empty state and headers.
  static const logoAsset = 'assets/images/app_logo.png';

  /// Square icon asset used in compact app bars and title rows.
  static const logoIconAsset = 'assets/images/app_logo_icon.png';

  /// Product display name.
  static const name = 'Code Weave';

  /// Short marketing tagline shown near branding elements.
  static const tagline = 'AI Powered Code Intelligence';

  /// Width-to-height ratio of the full logo image.
  static const double logoAspectRatio = 587 / 458;
}
