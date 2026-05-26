/// Scrollable canvas that paints the folder-tree architecture graph.
///
/// Lays out visible hierarchy nodes with [FolderGraphLayout], draws
/// parent-child edges, and renders interactive node chips in the explorer
/// Architecture tab. Selection syncs with the project tree and details panel.
library;
import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/graph_models.dart';
import '../../domain/graph_tree_visibility.dart';
import 'folder_graph_layout.dart';

/// Interactive graph canvas with pan/zoom scroll and node selection.
class ArchitectureGraphCanvas extends StatefulWidget {
  const ArchitectureGraphCanvas({
    super.key,
    required this.nodes,
    required this.allNodes,
    required this.rootId,
    required this.selectedId,
    required this.highlightedIds,
    required this.expandedNodeIds,
    required this.onSelect,
    required this.onToggleExpand,
  });

  /// Nodes currently eligible for layout (may be capped).
  final List<GraphNodeModel> nodes;

  /// Full node set used to detect children for expand chevrons.
  final List<GraphNodeModel> allNodes;

  final String rootId;
  final String? selectedId;
  final Set<String> highlightedIds;
  final Set<String> expandedNodeIds;
  final ValueChanged<String> onSelect;
  final ValueChanged<String> onToggleExpand;

  @override
  State<ArchitectureGraphCanvas> createState() => _ArchitectureGraphCanvasState();
}

class _ArchitectureGraphCanvasState extends State<ArchitectureGraphCanvas> {
  final ScrollController _horizontalController = ScrollController();
  final ScrollController _verticalController = ScrollController();

  @override
  void dispose() {
    _horizontalController.dispose();
    _verticalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final visibleNodes = filterVisibleTreeNodes(
      widget.nodes,
      widget.rootId,
      widget.expandedNodeIds,
    );
    final layout = FolderGraphLayout.compute(rootId: widget.rootId, nodes: visibleNodes);
    if (layout.positions.isEmpty) {
      return const Center(
        child: Text('No code structure to display', style: TextStyle(color: AppTheme.textMuted)),
      );
    }

    final byId = {for (final n in widget.nodes) n.id: n};
    final containsEdges = <(String, String)>[];
    for (final n in visibleNodes) {
      final parent = n.parentId;
      if (parent != null &&
          layout.positions.containsKey(parent) &&
          layout.positions.containsKey(n.id)) {
        containsEdges.add((parent, n.id));
      }
    }

    return Scrollbar(
      controller: _horizontalController,
      thumbVisibility: true,
      child: SingleChildScrollView(
        controller: _horizontalController,
        primary: false,
        scrollDirection: Axis.horizontal,
        child: Scrollbar(
          controller: _verticalController,
          thumbVisibility: true,
          child: SingleChildScrollView(
            controller: _verticalController,
            primary: false,
            scrollDirection: Axis.vertical,
            child: SizedBox(
              width: layout.size.width,
              height: layout.size.height,
              child: Stack(
                children: [
                  CustomPaint(
                    size: layout.size,
                    painter: _GraphEdgePainter(
                      edges: containsEdges,
                      positions: layout.positions,
                      nodeWidth: FolderGraphLayout.nodeWidth,
                      nodeHeight: FolderGraphLayout.nodeHeight,
                    ),
                  ),
                  ...layout.positions.entries.map((e) {
                    final node = byId[e.key];
                    if (node == null) return const SizedBox.shrink();
                    final hasChildren = nodeHasChildren(node.id, widget.allNodes);
                    final isExpanded = widget.expandedNodeIds.contains(node.id);
                    return Positioned(
                      left: e.value.dx,
                      top: e.value.dy,
                      child: _GraphNodeChip(
                        node: node,
                        selected: widget.selectedId == node.id,
                        highlighted: widget.highlightedIds.contains(node.id),
                        hasChildren: hasChildren,
                        isExpanded: isExpanded,
                        onTap: () => widget.onSelect(node.id),
                        onToggleExpand: hasChildren
                            ? () => widget.onToggleExpand(node.id)
                            : null,
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GraphEdgePainter extends CustomPainter {
  _GraphEdgePainter({
    required this.edges,
    required this.positions,
    required this.nodeWidth,
    required this.nodeHeight,
  });

  final List<(String, String)> edges;
  final Map<String, Offset> positions;
  final double nodeWidth;
  final double nodeHeight;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppTheme.border
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    for (final (parent, child) in edges) {
      final p = positions[parent];
      final c = positions[child];
      if (p == null || c == null) continue;

      final start = Offset(p.dx + nodeWidth, p.dy + nodeHeight / 2);
      final end = Offset(c.dx, c.dy + nodeHeight / 2);
      final midX = (start.dx + end.dx) / 2;
      final path = Path()
        ..moveTo(start.dx, start.dy)
        ..lineTo(midX, start.dy)
        ..lineTo(midX, end.dy)
        ..lineTo(end.dx, end.dy);
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _GraphEdgePainter oldDelegate) {
    return oldDelegate.edges != edges || oldDelegate.positions != positions;
  }
}

class _GraphNodeChip extends StatelessWidget {
  const _GraphNodeChip({
    required this.node,
    required this.selected,
    required this.highlighted,
    required this.hasChildren,
    required this.isExpanded,
    required this.onTap,
    this.onToggleExpand,
  });

  final GraphNodeModel node;
  final bool selected;
  final bool highlighted;
  final bool hasChildren;
  final bool isExpanded;
  final VoidCallback onTap;
  final VoidCallback? onToggleExpand;

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.nodeTypeColor(node.type);
    final borderColor = selected
        ? color
        : highlighted
            ? AppTheme.accent
            : AppTheme.border;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          width: FolderGraphLayout.nodeWidth,
          height: FolderGraphLayout.nodeHeight,
          padding: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: selected
                ? color.withValues(alpha: 0.18)
                : highlighted
                    ? AppTheme.accent.withValues(alpha: 0.12)
                    : AppTheme.surfaceHigh,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: borderColor,
              width: selected || highlighted ? 2 : 1,
            ),
            boxShadow: [
              if (selected || highlighted)
                BoxShadow(
                  color: borderColor.withValues(alpha: 0.25),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
            ],
          ),
          child: Row(
            children: [
              if (hasChildren)
                SizedBox(
                  width: 22,
                  height: 22,
                  child: IconButton(
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    icon: Icon(
                      isExpanded ? Icons.expand_more : Icons.chevron_right,
                      size: 16,
                      color: AppTheme.textMuted,
                    ),
                    onPressed: onToggleExpand,
                  ),
                )
              else
                const SizedBox(width: 6),
              Icon(_iconFor(node.type), size: 14, color: color),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  node.name,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    color: selected ? color : AppTheme.textPrimary,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _iconFor(String type) {
    return switch (type) {
      'repository' => Icons.folder_special,
      'folder' => Icons.folder,
      'file' => Icons.description,
      'class' => Icons.class_,
      'method' => Icons.build,
      'function' => Icons.functions,
      _ => Icons.circle,
    };
  }
}
