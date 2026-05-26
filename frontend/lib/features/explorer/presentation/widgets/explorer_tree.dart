/// Hierarchical project tree for the explorer left sidebar.
///
/// Renders repository folder/file/class/function nodes from backend hierarchy
/// data. On compact layouts it appears in a bottom sheet; on medium+ layouts
/// it sits beside the architecture graph and details tabs.
library;
import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/graph_models.dart';
import '../../domain/graph_tree_visibility.dart';

/// Expandable tree listing all visible hierarchy nodes under [rootId].
class ExplorerTree extends StatefulWidget {
  const ExplorerTree({
    super.key,
    required this.rootId,
    required this.nodes,
    required this.selectedId,
    required this.expandedNodeIds,
    required this.onSelect,
    required this.onToggleExpand,
    this.onCollapseAll,
    this.scrollController,
    this.showHeader = true,
  });

  final String? rootId;
  final List<GraphNodeModel> nodes;
  final String? selectedId;
  final Set<String> expandedNodeIds;
  final ValueChanged<String> onSelect;
  final ValueChanged<String> onToggleExpand;
  final VoidCallback? onCollapseAll;
  final ScrollController? scrollController;

  /// When false, hides the "Project tree" header row.
  final bool showHeader;

  @override
  State<ExplorerTree> createState() => _ExplorerTreeState();
}

class _ExplorerTreeState extends State<ExplorerTree> {
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
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      'Project tree',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textMuted,
                          ),
                    ),
                  ),
                  if (widget.onCollapseAll != null)
                    TextButton(
                      onPressed: widget.onCollapseAll,
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const Text(
                        'Collapse all',
                        style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                      ),
                    ),
                ],
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

    final rootId = widget.rootId!;
    if (!isTreeNodeVisible(id, rootId, _nodesById, widget.expandedNodeIds)) {
      return const SizedBox.shrink();
    }

    final children = widget.nodes.where((n) => n.parentId == id).toList()
      ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    final hasChildren = children.isNotEmpty;
    final isExpanded = widget.expandedNodeIds.contains(id);
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
                  if (hasChildren)
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
                        onPressed: () => widget.onToggleExpand(id),
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
        if (isExpanded)
          ...children.map((c) => _buildNode(c.id, depth + 1)),
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
