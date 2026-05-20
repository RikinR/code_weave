import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/graph_models.dart';
import 'folder_graph_layout.dart';

class ArchitectureGraphCanvas extends StatefulWidget {
  const ArchitectureGraphCanvas({
    super.key,
    required this.nodes,
    required this.rootId,
    required this.selectedId,
    required this.highlightedIds,
    required this.onSelect,
  });

  final List<GraphNodeModel> nodes;
  final String rootId;
  final String? selectedId;
  final Set<String> highlightedIds;
  final ValueChanged<String> onSelect;

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
    final layout = FolderGraphLayout.compute(rootId: widget.rootId, nodes: widget.nodes);
    if (layout.positions.isEmpty) {
      return const Center(
        child: Text('No code structure to display', style: TextStyle(color: AppTheme.textMuted)),
      );
    }

    final byId = {for (final n in widget.nodes) n.id: n};
    final containsEdges = <(String, String)>[];
    for (final n in widget.nodes) {
      final parent = n.parentId;
      if (parent != null && layout.positions.containsKey(parent) && layout.positions.containsKey(n.id)) {
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
                    return Positioned(
                      left: e.value.dx,
                      top: e.value.dy,
                      child: _GraphNodeChip(
                        node: node,
                        selected: widget.selectedId == node.id,
                        highlighted: widget.highlightedIds.contains(node.id),
                        onTap: () => widget.onSelect(node.id),
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
    required this.onTap,
  });

  final GraphNodeModel node;
  final bool selected;
  final bool highlighted;
  final VoidCallback onTap;

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
          padding: const EdgeInsets.symmetric(horizontal: 8),
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
              Icon(_iconFor(node.type), size: 14, color: color),
              const SizedBox(width: 6),
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
