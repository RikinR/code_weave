import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/network/api_client.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/explorer/presentation/providers/explorer_provider.dart';
import 'features/home/presentation/providers/repository_list_provider.dart';
import 'features/pipeline/presentation/providers/pipeline_provider.dart';

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

class CodeWeaveApp extends StatelessWidget {
  const CodeWeaveApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Code Weave',
      theme: AppTheme.dark(),
      routerConfig: createRouter(),
      debugShowCheckedModeBanner: false,
    );
  }
}
