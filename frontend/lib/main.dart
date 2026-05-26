/// Application entry point for the Code Weave Flutter client.
///
/// Bootstraps a shared [ApiClient], registers feature providers for the
/// home, pipeline, and explorer flows, and mounts [CodeWeaveApp] with
/// dark theme and go_router navigation to the FastAPI backend.
library;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/brand/app_brand.dart';
import 'core/network/api_client.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/explorer/presentation/providers/explorer_provider.dart';
import 'features/home/presentation/providers/repository_list_provider.dart';
import 'features/pipeline/presentation/providers/pipeline_provider.dart';

/// Starts the app with global providers wired to the backend API client.
void main() {
  final api = ApiClient();
  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider(create: (_) => RepositoryListProvider(api)),
        ChangeNotifierProvider(create: (_) => PipelineProvider(api)),
        ChangeNotifierProvider(create: (_) => ExplorerProvider(api)),
      ],
      child: const CodeWeaveApp(),
    ),
  );
}

/// Root widget that configures theme, routing, and app branding.
class CodeWeaveApp extends StatelessWidget {
  const CodeWeaveApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: AppBrand.name,
      theme: AppTheme.dark(),
      routerConfig: createRouter(),
      debugShowCheckedModeBanner: false,
    );
  }
}
