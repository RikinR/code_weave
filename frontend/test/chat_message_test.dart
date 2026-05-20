import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/features/explorer/presentation/providers/explorer_provider.dart';

void main() {
  test('ChatMessage citations list accepts addAll', () {
    final msg = ChatMessage(role: 'assistant', text: '');
    msg.citations.add({'file_path': 'app/main.py'});
    expect(msg.citations.length, 1);
  });
}
