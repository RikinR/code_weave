import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/features/explorer/domain/graph_models.dart';

void main() {
  test('architectureGraphNodes keeps repo tree through callables', () {
    const nodes = [
      GraphNodeModel(id: 'r', type: 'repository', name: 'repo'),
      GraphNodeModel(id: 'f1', type: 'folder', name: 'src', parentId: 'r'),
      GraphNodeModel(id: 'file', type: 'file', name: 'main.py', parentId: 'f1'),
      GraphNodeModel(id: 'fn', type: 'function', name: 'main', parentId: 'file'),
      GraphNodeModel(id: 'cls', type: 'class', name: 'Foo', parentId: 'file'),
    ];

    final arch = architectureGraphNodes(nodes);
    expect(
      arch.map((n) => n.type).toList(),
      ['repository', 'folder', 'file', 'function', 'class'],
    );
    expect(arch.length, 5);
  });
}
