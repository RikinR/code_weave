import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/graph_models.dart';
import 'architecture_graph_canvas.dart';

class ArchitectureGraphView extends StatelessWidget {
  const ArchitectureGraphView({
    super.key,
    required this.nodes,
    required this.edges,
    required this.rootId,
    required this.selectedId,
    required this.highlightedIds,
    required this.onSelect,
  });

  final List<GraphNodeModel> nodes;
  final List<GraphEdgeModel> edges;
  final String? rootId;
  final String? selectedId;
  final Set<String> highlightedIds;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    final displayNodes = architectureGraphNodes(nodes);
    final capped = displayNodes.length > kMaxArchitectureGraphNodes;
    final graphNodes = capped && rootId != null
        ? capArchitectureGraphNodes(displayNodes, rootId!)
        : displayNodes;

    if (rootId == null || graphNodes.isEmpty) {
      return const Center(
        child: Text('No graph data', style: TextStyle(color: AppTheme.textMuted)),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: Row(
            children: [
              Icon(Icons.hub, size: 18, color: AppTheme.accent),
              const SizedBox(width: 8),
              Text(
                'Architecture (files, classes & functions)',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textMuted,
                    ),
              ),
              const Spacer(),
              Text(
                capped
                    ? '${graphNodes.length} of ${displayNodes.length} nodes'
                    : '${graphNodes.length} nodes',
                style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
              ),
            ],
          ),
        ),
        if (capped)
          const Padding(
            padding: EdgeInsets.fromLTRB(12, 0, 12, 4),
            child: Text(
              'Graph capped at $kMaxArchitectureGraphNodes nodes — use the project tree for full navigation.',
              style: TextStyle(color: AppTheme.textMuted, fontSize: 11),
            ),
          ),
        const Divider(height: 1, color: AppTheme.border),
        Expanded(
          child: ArchitectureGraphCanvas(
            nodes: graphNodes,
            rootId: rootId!,
            selectedId: selectedId,
            highlightedIds: highlightedIds,
            onSelect: onSelect,
          ),
        ),
      ],
    );
  }
}
