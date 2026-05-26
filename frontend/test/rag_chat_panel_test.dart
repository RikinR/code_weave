/// Widget tests for the RAG chat panel (streaming UI, citations).
library;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/features/explorer/presentation/widgets/rag_chat_panel.dart';

void main() {
  testWidgets('RAG chat header fits medium-layout panel width without overflow', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 300,
            height: 400,
            child: RagChatPanel(
              messages: const [],
              streaming: false,
              beginnerMode: true,
              onBeginnerChanged: (_) {},
              onSend: (_) {},
              onCitationTap: (_) {},
            ),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('RAG Assistant'), findsOneWidget);
    expect(find.byType(Switch), findsOneWidget);
  });
}
