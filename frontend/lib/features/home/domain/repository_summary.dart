class RepositorySummary {
  const RepositorySummary({
    required this.id,
    required this.name,
    this.rootPath,
    this.description,
    this.createdAt,
    this.fileCount = 0,
    this.functionCount = 0,
    this.chunkCount = 0,
  });

  final String id;
  final String name;
  final String? rootPath;
  final String? description;
  final String? createdAt;
  final int fileCount;
  final int functionCount;
  final int chunkCount;

  factory RepositorySummary.fromJson(Map<String, dynamic> json) {
    return RepositorySummary(
      id: json['id'] as String,
      name: json['name'] as String,
      rootPath: json['root_path'] as String?,
      description: json['description'] as String?,
      createdAt: json['created_at'] as String?,
      fileCount: (json['file_count'] as num?)?.toInt() ?? 0,
      functionCount: (json['function_count'] as num?)?.toInt() ?? 0,
      chunkCount: (json['chunk_count'] as num?)?.toInt() ?? 0,
    );
  }
}
