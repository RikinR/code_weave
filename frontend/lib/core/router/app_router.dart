import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/explorer/presentation/explorer_screen.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/pipeline/presentation/pipeline_screen.dart';

GoRouter createRouter() {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/pipeline/:jobId',
        builder: (context, state) {
          final jobId = state.pathParameters['jobId']!;
          final name = state.uri.queryParameters['name'];
          return PipelineScreen(jobId: jobId, repositoryName: name);
        },
      ),
      GoRoute(
        path: '/explorer/:repositoryId',
        builder: (context, state) {
          final repoId = state.pathParameters['repositoryId']!;
          final name = state.uri.queryParameters['name'];
          return ExplorerScreen(
            key: ValueKey(repoId),
            repositoryId: repoId,
            repositoryName: name,
          );
        },
      ),
    ],
  );
}
