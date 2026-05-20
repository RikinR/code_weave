class PipelineStage {
  const PipelineStage({
    required this.key,
    required this.label,
    required this.status,
    required this.progress,
    required this.logs,
  });

  final String key;
  final String label;
  final String status;
  final double progress;
  final List<String> logs;

  factory PipelineStage.fromJson(Map<String, dynamic> json) {
    return PipelineStage(
      key: json['key'] as String,
      label: json['label'] as String,
      status: json['status'] as String,
      progress: (json['progress'] as num?)?.toDouble() ?? 0,
      logs: (json['logs'] as List<dynamic>? ?? []).cast<String>(),
    );
  }
}
