import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/graph_models.dart';

class ExplorerTree extends StatefulWidget {
  const ExplorerTree({
    super.key,
    required this.rootId,
    required this.nodes,
    required this.selectedId,
    required this.onSelect,
    this.scrollController,
    this.showHeader = true,
  });

  final String? rootId;
  final List<GraphNodeModel> nodes;
  final String? selectedId;
  final ValueChanged<String> onSelect;
  final ScrollController? scrollController;
  final bool showHeader;

  @override
  State<ExplorerTree> createState() => _ExplorerTreeState();
}

class _ExplorerTreeState extends State<ExplorerTree> {
  final Set<String> expanded = {};
  late Map<String, GraphNodeModel> _nodesById;

  @override
  void initState() {
    super.initState();
    _nodesById = _indexNodes(widget.nodes);
  }

  @override
  void didUpdateWidget(ExplorerTree oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.nodes != widget.nodes) {
      _nodesById = _indexNodes(widget.nodes);
    }
  }

  Map<String, GraphNodeModel> _indexNodes(List<GraphNodeModel> nodes) {
    return {for (final n in nodes) n.id: n};
  }

  @override
  Widget build(BuildContext context) {
    if (widget.rootId == null) {
      return const Center(child: Text('No hierarchy'));
    }

    return Container(
      color: AppTheme.surface,
      child: ListView(
        controller: widget.scrollController,
        padding: const EdgeInsets.symmetric(vertical: 4),
        children: [
          if (widget.showHeader)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
              child: Text(
                'Project tree',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textMuted,
                    ),
              ),
            ),
          _buildNode(widget.rootId!, 0),
        ],
      ),
    );
  }

  Widget _buildNode(String id, int depth) {
    final node = _nodesById[id];
    if (node == null) return const SizedBox.shrink();

    final children = widget.nodes.where((n) => n.parentId == id).toList();
    final isExpanded = expanded.contains(id);
    final selected = widget.selectedId == id;
    final typeColor = AppTheme.nodeTypeColor(node.type);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Material(
          color: selected ? typeColor.withValues(alpha: 0.12) : Colors.transparent,
          child: InkWell(
            onTap: () => widget.onSelect(id),
            child: Container(
              padding: EdgeInsets.only(left: 8.0 + depth * 14, top: 5, bottom: 5, right: 8),
              decoration: selected
                  ? BoxDecoration(
                      border: Border(left: BorderSide(color: typeColor, width: 3)),
                    )
                  : null,
              child: Row(
                children: [
                  if (children.isNotEmpty)
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: IconButton(
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                        icon: Icon(
                          isExpanded ? Icons.expand_more : Icons.chevron_right,
                          size: 18,
                          color: AppTheme.textMuted,
                        ),
                        onPressed: () {
                          setState(() {
                            if (isExpanded) {
                              expanded.remove(id);
                            } else {
                              expanded.add(id);
                            }
                          });
                        },
                      ),
                    )
                  else
                    const SizedBox(width: 24),
                  Icon(_iconFor(node.type), size: 16, color: typeColor),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      node.name,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                        color: selected ? typeColor : AppTheme.textPrimary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        if (isExpanded) ...children.map((c) => _buildNode(c.id, depth + 1)),
      ],
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
