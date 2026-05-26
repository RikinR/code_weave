/// Smoke tests for shared domain models used by the pipeline UI.
library;
import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/features/pipeline/domain/pipeline_stage.dart';

void main() {
  test('PipelineStage parses backend payload', () {
    final stage = PipelineStage.fromJson({
      'key': 'zip_extraction',
      'label': 'ZIP extraction',
      'status': 'running',
      'progress': 42.5,
      'logs': ['Extracting archive'],
    });
    expect(stage.key, 'zip_extraction');
    expect(stage.status, 'running');
    expect(stage.logs.length, 1);
  });
}
