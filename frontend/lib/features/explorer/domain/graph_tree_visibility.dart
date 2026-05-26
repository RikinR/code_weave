/// Tree expand/collapse and visibility helpers for explorer hierarchy views.
///
/// Shared by [ExplorerTree], [ArchitectureGraphCanvas], and [ExplorerProvider]
/// to keep project tree and graph canvas expansion state in sync.
library;
import 'graph_models.dart';

/// Returns whether [id] is visible given ancestor expansion state.
bool isTreeNodeVisible(
  String id,
  String rootId,
  Map<String, GraphNodeModel> byId,
  Set<String> expandedNodeIds,
) {
  if (id == rootId) return true;
  final node = byId[id];
  if (node == null) return false;
  final parentId = node.parentId;
  if (parentId == null) return false;
  if (!isTreeNodeVisible(parentId, rootId, byId, expandedNodeIds)) return false;
  return expandedNodeIds.contains(parentId);
}

/// Filters [nodes] to those visible in the expanded tree under [rootId].
List<GraphNodeModel> filterVisibleTreeNodes(
  List<GraphNodeModel> nodes,
  String rootId,
  Set<String> expandedNodeIds,
) {
  final byId = {for (final n in nodes) n.id: n};
  return nodes
      .where((n) => isTreeNodeVisible(n.id, rootId, byId, expandedNodeIds))
      .toList();
}

/// Collects all descendant node ids below [id].
Set<String> descendantNodeIds(
  String id,
  List<GraphNodeModel> nodes,
) {
  final childrenByParent = <String, List<String>>{};
  for (final n in nodes) {
    final parent = n.parentId;
    if (parent != null) {
      childrenByParent.putIfAbsent(parent, () => []).add(n.id);
    }
  }
  final out = <String>{};
  final queue = <String>[id];
  while (queue.isNotEmpty) {
    final current = queue.removeAt(0);
    for (final childId in childrenByParent[current] ?? const []) {
      if (out.add(childId)) queue.add(childId);
    }
  }
  return out;
}

/// Expands all ancestors of [nodeId] so it becomes visible in the tree.
void expandPathToNode(
  String nodeId,
  String rootId,
  List<GraphNodeModel> nodes,
  Set<String> expandedNodeIds,
) {
  final byId = {for (final n in nodes) n.id: n};
  expandedNodeIds.add(rootId);
  var current = byId[nodeId];
  while (current != null) {
    final parentId = current.parentId;
    if (parentId == null) break;
    expandedNodeIds.add(parentId);
    current = byId[parentId];
  }
}

/// Returns true if [id] has at least one child in [nodes].
bool nodeHasChildren(String id, List<GraphNodeModel> nodes) {
  return nodes.any((n) => n.parentId == id);
}
