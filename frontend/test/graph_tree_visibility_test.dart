/// Unit tests for collapsible graph/tree visibility in the explorer.
library;
import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/features/explorer/domain/graph_models.dart';
import 'package:code_weave_frontend/features/explorer/domain/graph_tree_visibility.dart';

void main() {
  const nodes = [
    GraphNodeModel(id: 'r', type: 'repository', name: 'repo'),
    GraphNodeModel(id: 'f1', type: 'folder', name: 'src', parentId: 'r'),
    GraphNodeModel(id: 'file', type: 'file', name: 'main.py', parentId: 'f1'),
    GraphNodeModel(id: 'fn', type: 'function', name: 'main', parentId: 'file'),
  ];

  test('only root visible when only root is expanded', () {
    final visible = filterVisibleTreeNodes(nodes, 'r', {'r'});
    expect(visible.map((n) => n.id).toList(), ['r', 'f1']);
  });

  test('deep node hidden until ancestors expanded', () {
    expect(
      isTreeNodeVisible('fn', 'r', {for (final n in nodes) n.id: n}, {'r'}),
      isFalse,
    );
    expect(
      isTreeNodeVisible('fn', 'r', {for (final n in nodes) n.id: n}, {'r', 'f1', 'file'}),
      isTrue,
    );
  });

  test('expandPathToNode opens ancestors', () {
    final expanded = <String>{};
    expandPathToNode('fn', 'r', nodes, expanded);
    expect(expanded, {'r', 'f1', 'file'});
  });

  test('descendantNodeIds collects subtree', () {
    expect(descendantNodeIds('f1', nodes), {'file', 'fn'});
  });
}
