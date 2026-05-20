import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:code_weave_frontend/core/widgets/accent_card.dart';

void main() {
  testWidgets('AccentCard lays out inside ListView without infinite height error', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: const [
              AccentCard(child: Text('Processing')),
            ],
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('Processing'), findsOneWidget);
  });
}
