import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/features/explorer/domain/graph_models.dart';
import 'package:code_weave_frontend/features/explorer/presentation/widgets/folder_graph_layout.dart';

void main() {
  test('compute places root left of children (left-to-right)', () {
    const nodes = [
      GraphNodeModel(id: 'r', type: 'repository', name: 'my-repo'),
      GraphNodeModel(id: 'f', type: 'folder', name: 'app', parentId: 'r'),
      GraphNodeModel(
        id: 'file',
        type: 'file',
        name: 'main.py',
        parentId: 'f',
        filePath: 'app/main.py',
      ),
      GraphNodeModel(id: 'cls', type: 'class', name: 'Service', parentId: 'file'),
      GraphNodeModel(id: 'fn', type: 'function', name: 'run', parentId: 'file'),
    ];

    final layout = FolderGraphLayout.compute(rootId: 'r', nodes: nodes);
    expect(layout.positions.length, 5);
    expect(layout.positions['r']!.dx, lessThan(layout.positions['f']!.dx));
    expect(layout.positions['f']!.dx, lessThan(layout.positions['file']!.dx));
    expect(layout.positions['file']!.dx, lessThan(layout.positions['cls']!.dx));
    expect(layout.size.width, greaterThan(FolderGraphLayout.nodeWidth * 3));
  });

  test('architectureGraphNodes includes classes and functions', () {
    const nodes = [
      GraphNodeModel(id: 'r', type: 'repository', name: 'repo'),
      GraphNodeModel(id: 'file', type: 'file', name: 'a.py', parentId: 'r'),
      GraphNodeModel(id: 'cls', type: 'class', name: 'Foo', parentId: 'file'),
      GraphNodeModel(id: 'fn', type: 'function', name: 'bar', parentId: 'file'),
    ];
    final arch = architectureGraphNodes(nodes);
    expect(arch.map((n) => n.type).toSet(), containsAll(['repository', 'file', 'class', 'function']));
  });
}
