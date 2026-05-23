import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/layout/responsive.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/accent_card.dart';
import '../domain/pipeline_stage.dart';
import 'providers/pipeline_provider.dart';

class PipelineScreen extends StatefulWidget {
  const PipelineScreen({super.key, required this.jobId, this.repositoryName});

  final String jobId;
  final String? repositoryName;

  @override
  State<PipelineScreen> createState() => _PipelineScreenState();
}

class _PipelineScreenState extends State<PipelineScreen> with SingleTickerProviderStateMixin {
  late final AnimationController _spinController;
  bool _navigatedToExplorer = false;

  @override
  void initState() {
    super.initState();
    _spinController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();

    context.read<PipelineProvider>().prepareForJob(
          widget.jobId,
          repoName: widget.repositoryName,
        );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<PipelineProvider>().start(
            widget.jobId,
            repoName: widget.repositoryName,
          );
    });
  }

  @override
  void dispose() {
    _spinController.dispose();
    super.dispose();
  }

  void _maybeNavigateToExplorer(PipelineProvider provider) {
    if (_navigatedToExplorer) return;
    if (provider.jobId != widget.jobId) return;
    if (provider.status != 'completed' || provider.repositoryId == null) return;
    _navigatedToExplorer = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.go(
        '/explorer/${provider.repositoryId}?name=${Uri.encodeComponent(provider.repositoryName ?? '')}',
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<PipelineProvider>();
    _maybeNavigateToExplorer(provider);

    final isActive = provider.status == 'running' || provider.status == 'pending';

    return Scaffold(
      backgroundColor: AppTheme.pageBackdrop,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: EdgeInsets.symmetric(
                horizontal: Responsive.horizontalPadding(context),
                vertical: 12,
              ),
              child: Row(
                children: [
                  IconButton(
                    onPressed: () => context.go('/'),
                    icon: const Icon(Icons.arrow_back),
                  ),
                  Expanded(
                    child: Text(
                      'Indexing ${widget.repositoryName ?? ''}',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ResponsiveBody(
                maxWidth: 720,
                child: ListView(
                  children: [
                    if (isActive)
                      _ProcessingBanner(provider: provider, spin: _spinController),
                    if (provider.status == 'failed' && provider.error != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _FailedJobBanner(provider: provider),
                      ),
                    ...provider.stages.map(
                      (stage) => _StageTile(
                        key: ValueKey(stage.key),
                        stage: stage,
                        jobFailed: provider.status == 'failed',
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FailedJobBanner extends StatelessWidget {
  const _FailedJobBanner({required this.provider});

  final PipelineProvider provider;

  @override
  Widget build(BuildContext context) {
    final interrupted = provider.isInterrupted;

    return AccentCard(
      accentColor: AppTheme.danger,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            interrupted ? 'Indexing interrupted' : 'Indexing failed',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: AppTheme.danger,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            provider.error!,
            style: const TextStyle(color: AppTheme.danger),
          ),
          if (interrupted) ...[
            const SizedBox(height: 8),
            const Text(
              'The backend restarted while this job was running (common with '
              'uvicorn --reload). Completed steps stay checked; anything still '
              'spinning was not actually running.',
              style: TextStyle(color: AppTheme.textMuted, fontSize: 13),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (provider.canRetry)
                FilledButton.icon(
                  onPressed: () => provider.retry(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry indexing'),
                ),
              OutlinedButton(
                onPressed: () => context.go('/'),
                child: const Text('Back to home'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ProcessingBanner extends StatelessWidget {
  const _ProcessingBanner({required this.provider, required this.spin});

  final PipelineProvider provider;
  final AnimationController spin;

  @override
  Widget build(BuildContext context) {
    final running = provider.runningStage;
    final label = provider.activeStageLabel;
    final progress = running != null ? running.progress / 100 : null;

    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: AccentCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                RotationTransition(
                  turns: spin,
                  child: const Icon(Icons.sync, color: AppTheme.accent, size: 24),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Processing your codebase',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        label,
                        style: const TextStyle(color: AppTheme.accent, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),
                Text(
                  provider.elapsedLabel,
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontFamily: 'monospace',
                    fontSize: 13,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (progress != null && progress > 0)
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 6,
                  backgroundColor: AppTheme.surfaceHigh,
                  color: AppTheme.accent,
                ),
              )
            else
              const ClipRRect(
                borderRadius: BorderRadius.all(Radius.circular(4)),
                child: LinearProgressIndicator(
                  minHeight: 6,
                  backgroundColor: AppTheme.surfaceHigh,
                  color: AppTheme.accent,
                ),
              ),
            const SizedBox(height: 12),
            Text(
              provider.activityHint,
              style: const TextStyle(color: AppTheme.textMuted, fontSize: 13),
            ),
            if (provider.lastLog != null) ...[
              const SizedBox(height: 8),
              Text(
                provider.lastLog!,
                style: const TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: AppTheme.textMuted,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StageTile extends StatefulWidget {
  const _StageTile({super.key, required this.stage, this.jobFailed = false});

  final PipelineStage stage;
  final bool jobFailed;

  @override
  State<_StageTile> createState() => _StageTileState();
}

class _StageTileState extends State<_StageTile> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    _expanded = widget.stage.status == 'running' || widget.stage.status == 'failed';
  }

  @override
  void didUpdateWidget(_StageTile oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.stage.status == 'running' && !_expanded) {
      _expanded = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    final stage = widget.stage;
    final displayStatus =
        widget.jobFailed && stage.status == 'running' ? 'failed' : stage.status;
    final isRunning = displayStatus == 'running';
    final color = switch (displayStatus) {
      'completed' => AppTheme.success,
      'running' => AppTheme.accent,
      'failed' => AppTheme.danger,
      _ => AppTheme.textMuted,
    };

    Widget leading;
    if (isRunning) {
      leading = SizedBox(
        width: 24,
        height: 24,
        child: CircularProgressIndicator(strokeWidth: 2, color: color),
      );
    } else {
      leading = Icon(_iconFor(displayStatus), color: color, size: 22);
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: AccentCard(
        accentColor: color,
        padding: EdgeInsets.zero,
        child: Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            key: ValueKey('${stage.key}-${stage.status}'),
            initiallyExpanded: _expanded,
            onExpansionChanged: (value) => setState(() => _expanded = value),
            leading: leading,
            title: Text(
              stage.label,
              style: TextStyle(fontWeight: isRunning ? FontWeight.w600 : FontWeight.normal),
            ),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 8, bottom: 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LinearProgressIndicator(
                    value: isRunning && stage.progress <= 0
                        ? null
                        : (stage.progress > 0 ? stage.progress / 100 : null),
                    minHeight: 5,
                    backgroundColor: AppTheme.surfaceHigh,
                    color: color,
                  ),
                  if (isRunning)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        stage.logs.isNotEmpty ? stage.logs.last : 'In progress…',
                        style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
              ),
            ),
            children: stage.logs
                .map(
                  (log) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Text(
                      log,
                      style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: AppTheme.textMuted),
                    ),
                  ),
                )
                .toList(),
          ),
        ),
      ),
    );
  }

  IconData _iconFor(String status) {
    return switch (status) {
      'completed' => Icons.check_circle_outline,
      'running' => Icons.autorenew,
      'failed' => Icons.error_outline,
      _ => Icons.radio_button_unchecked,
    };
  }
}
