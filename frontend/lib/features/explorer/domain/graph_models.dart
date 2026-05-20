const kArchitectureGraphNodeTypes = {
  'repository',
  'folder',
  'file',
  'class',
  'function',
  'method',
};

const kMaxArchitectureGraphNodes = 400;

List<GraphNodeModel> architectureGraphNodes(List<GraphNodeModel> nodes) {
  return nodes.where((n) => kArchitectureGraphNodeTypes.contains(n.type)).toList();
}

List<GraphNodeModel> capArchitectureGraphNodes(
  List<GraphNodeModel> nodes,
  String rootId, {
  int maxNodes = kMaxArchitectureGraphNodes,
}) {
  if (nodes.length <= maxNodes) return nodes;
  final byId = {for (final n in nodes) n.id: n};
  final childIds = <String, List<String>>{};
  for (final n in nodes) {
    final parent = n.parentId;
    if (parent != null) {
      childIds.putIfAbsent(parent, () => []).add(n.id);
    }
  }
  final kept = <String>{};
  final queue = <String>[rootId];
  while (queue.isNotEmpty && kept.length < maxNodes) {
    final id = queue.removeAt(0);
    if (!byId.containsKey(id) || kept.contains(id)) continue;
    kept.add(id);
    for (final cid in childIds[id] ?? const []) {
      if (kept.length >= maxNodes) break;
      queue.add(cid);
    }
  }
  return nodes.where((n) => kept.contains(n.id)).toList();
}

class GraphNodeModel {
  const GraphNodeModel({
    required this.id,
    required this.type,
    required this.name,
    this.parentId,
    this.children = const [],
    this.filePath,
    this.language,
  });

  final String id;
  final String type;
  final String name;
  final String? parentId;
  final List<String> children;
  final String? filePath;
  final String? language;

  factory GraphNodeModel.fromJson(Map<String, dynamic> json) {
    return GraphNodeModel(
      id: json['id'] as String,
      type: json['type'] as String,
      name: json['name'] as String,
      parentId: json['parent_id'] as String?,
      children: (json['children'] as List<dynamic>? ?? []).cast<String>(),
      filePath: json['file_path'] as String?,
      language: json['language'] as String?,
    );
  }
}

class GraphEdgeModel {
  const GraphEdgeModel({
    required this.id,
    required this.source,
    required this.target,
    required this.kind,
  });

  final String id;
  final String source;
  final String target;
  final String kind;

  factory GraphEdgeModel.fromJson(Map<String, dynamic> json) {
    return GraphEdgeModel(
      id: json['id'] as String,
      source: json['source'] as String,
      target: json['target'] as String,
      kind: json['kind'] as String,
    );
  }
}
