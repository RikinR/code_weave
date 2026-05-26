/// Home screen: repository list, zip upload, and supported languages.
///
/// Entry point after app launch (`/`). Uploads zip archives via
/// `POST /api/repositories/upload` and navigates to the pipeline screen;
/// tapping a repository card opens the explorer for that indexed codebase.
library;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/layout/responsive.dart';
import '../../../core/network/api_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/accent_card.dart';
import '../../../core/widgets/app_logo.dart';
import '../../../core/widgets/operation_progress.dart';
import '../domain/repository_summary.dart';
import 'providers/repository_list_provider.dart';

/// Landing screen listing indexed repositories with upload and delete actions.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _uploading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<RepositoryListProvider>().load();
    });
  }

  Future<void> _uploadZip(BuildContext context) async {
    if (_uploading) return;
    final api = context.read<ApiClient>();

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['zip'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    final bytes = file.bytes;
    if (bytes == null) return;

    setState(() => _uploading = true);
    try {
      final data = await api.uploadZip(
        fileName: file.name,
        bytes: bytes,
        name: file.name.replaceAll('.zip', ''),
      );
      if (!context.mounted) return;
      context.go(
        '/pipeline/${data['job_id']}?name=${Uri.encodeComponent(data['repository_name'] as String)}',
      );
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Upload failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<RepositoryListProvider>();
    final compact = Responsive.isCompact(context);
    final showOverlay = _uploading || provider.isBusy;
    final overlayMessage = _uploading
        ? 'Uploading and starting index…'
        : provider.busyMessage;

    return Scaffold(
      backgroundColor: AppTheme.pageBackdrop,
      body: Stack(
        children: [
          SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TopProgressBar(active: showOverlay),
              _HomeHeader(
                compact: compact,
                uploading: _uploading,
                busy: provider.isBusy,
                onRefresh: provider.isBusy ? null : provider.load,
                onUpload: () => _uploadZip(context),
              ),
              Expanded(
                child: compact
                    ? ResponsiveBody(
                        child: ListView(
                          children: [
                            _RepositoryGrid(provider: provider),
                            const SizedBox(height: 16),
                            _LanguageNotice(languages: provider.supportedLanguages),
                          ],
                        ),
                      )
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            child: ResponsiveBody(
                              child: _RepositoryGrid(provider: provider),
                            ),
                          ),
                          Padding(
                            padding: EdgeInsets.fromLTRB(
                              0,
                              20,
                              Responsive.horizontalPadding(context),
                              20,
                            ),
                            child: SizedBox(
                              width: Responsive.isMedium(context) ? 260 : 300,
                              child: _LanguageNotice(languages: provider.supportedLanguages),
                            ),
                          ),
                        ],
                      ),
              ),
            ],
          ),
        ),
          OperationProgressOverlay(
            visible: showOverlay,
            message: overlayMessage,
          ),
        ],
      ),
    );
  }
}

class _HomeHeader extends StatelessWidget {
  const _HomeHeader({
    required this.compact,
    required this.onUpload,
    this.onRefresh,
    this.uploading = false,
    this.busy = false,
  });

  final bool compact;
  final VoidCallback? onRefresh;
  final VoidCallback onUpload;
  final bool uploading;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        Responsive.horizontalPadding(context),
        12,
        Responsive.horizontalPadding(context),
        8,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          HomeBrandHeader(compact: compact),
          const Spacer(),
          IconButton(
            onPressed: onRefresh,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh repositories',
          ),
          const SizedBox(width: 4),
          if (compact)
            IconButton.filled(
              onPressed: uploading ? null : onUpload,
              icon: const Icon(Icons.upload_file),
              tooltip: 'Upload repository',
            )
          else
            FilledButton.icon(
              onPressed: uploading ? null : onUpload,
              icon: const Icon(Icons.upload_file),
              label: Text(uploading ? 'Uploading…' : 'Upload repository'),
            ),
        ],
      ),
    );
  }
}

Future<void> _confirmDeleteRepository(BuildContext context, RepositorySummary repo) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('Delete repository?'),
      content: Text(
        'Remove "${repo.name}" and all indexed data (database rows, embeddings, '
        'and uploaded files)? This cannot be undone.',
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: AppTheme.danger),
          onPressed: () => Navigator.pop(ctx, true),
          child: const Text('Delete'),
        ),
      ],
    ),
  );
  if (confirmed != true || !context.mounted) return;

  final provider = context.read<RepositoryListProvider>();
  final ok = await provider.deleteRepository(repo.id);
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(
        ok ? 'Deleted ${repo.name}' : 'Delete failed: ${provider.error}',
      ),
      backgroundColor: ok ? AppTheme.success : AppTheme.danger,
    ),
  );
}

class _RepositoryGrid extends StatelessWidget {
  const _RepositoryGrid({required this.provider});

  final RepositoryListProvider provider;

  @override
  Widget build(BuildContext context) {
    if (provider.loading && provider.repositories.isEmpty) {
      return const SizedBox.shrink();
    }
    if (provider.error != null && provider.repositories.isEmpty) {
      return Center(child: Text(provider.error!, style: const TextStyle(color: AppTheme.danger)));
    }
    if (provider.repositories.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 48),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const AppLogo(height: 120),
            const SizedBox(height: 20),
            Text(
              'No indexed repositories yet',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text('Upload a .zip to start', style: TextStyle(color: AppTheme.textMuted)),
          ],
        ),
      );
    }

    final columns = Responsive.gridColumns(context);
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: columns,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        childAspectRatio: columns == 1 ? 2.4 : 1.55,
      ),
      itemCount: provider.repositories.length,
      itemBuilder: (context, index) {
        final repo = provider.repositories[index];
        return _RepositoryCard(
          repo: repo,
          deleteEnabled: !provider.isBusy,
          onDelete: () => _confirmDeleteRepository(context, repo),
        );
      },
    );
  }
}

class _RepositoryCard extends StatelessWidget {
  const _RepositoryCard({
    required this.repo,
    required this.onDelete,
    this.deleteEnabled = true,
  });

  final RepositorySummary repo;
  final VoidCallback onDelete;
  final bool deleteEnabled;

  @override
  Widget build(BuildContext context) {
    return AccentCard(
      fillHeight: true,
      padding: const EdgeInsets.fromLTRB(12, 12, 8, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.max,
        children: [
          Row(
            children: [
              Icon(Icons.storage_outlined, color: AppTheme.accent, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => context.go(
                    '/explorer/${repo.id}?name=${Uri.encodeComponent(repo.name)}',
                  ),
                  child: Text(
                    repo.name,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              IconButton(
                visualDensity: VisualDensity.compact,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                icon: const Icon(Icons.delete_outline, size: 20, color: AppTheme.danger),
                tooltip: 'Delete repository',
                onPressed: deleteEnabled ? onDelete : null,
              ),
            ],
          ),
          const Spacer(),
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: () => context.go(
              '/explorer/${repo.id}?name=${Uri.encodeComponent(repo.name)}',
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${repo.fileCount} files · ${repo.functionCount} functions',
                  style: const TextStyle(color: AppTheme.textMuted, fontSize: 13),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  '${repo.chunkCount} chunks indexed',
                  style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LanguageNotice extends StatelessWidget {
  const _LanguageNotice({required this.languages});

  final List<String> languages;

  @override
  Widget build(BuildContext context) {
    return AccentCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(Icons.code, color: AppTheme.accent, size: 20),
              const SizedBox(width: 8),
              Text(
                'Tree-sitter languages',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Parsing is Tree-sitter based. Unsupported files are skipped during ingestion.',
            style: TextStyle(color: AppTheme.textMuted, fontSize: 13),
          ),
          const SizedBox(height: 12),
          ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: Responsive.isCompact(context) ? 200 : 320,
            ),
            child: SingleChildScrollView(
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: languages
                    .map(
                      (lang) => Chip(
                        label: Text(lang),
                        visualDensity: VisualDensity.compact,
                        backgroundColor: AppTheme.surfaceHigh,
                      ),
                    )
                    .toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
