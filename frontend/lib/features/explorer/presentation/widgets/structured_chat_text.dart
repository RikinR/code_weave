/// Structured rendering for RAG assistant responses in the explorer chat panel.
///
/// Parses section headers and bullet lists from backend answer text so
/// [RagChatPanel] can display formatted assistant messages.
library;
import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

/// Renders plain user text or structured assistant sections and lists.
class StructuredChatText extends StatelessWidget {
  const StructuredChatText({
    super.key,
    required this.text,
    required this.isUser,
  });

  final String text;
  final bool isUser;

  static final _sectionPattern = RegExp(
    r'^(Summary|How it works|Steps|Key idea|Relevant chunks):',
    caseSensitive: false,
  );

  @override
  Widget build(BuildContext context) {
    if (isUser || !text.contains(':')) {
      return Text(
        text,
        style: TextStyle(
          color: isUser ? Colors.white : AppTheme.textPrimary,
          fontSize: 14,
          height: 1.45,
        ),
      );
    }

    final lines = text.split('\n');
    final children = <Widget>[];

    for (final line in lines) {
      final trimmed = line.trimRight();
      if (trimmed.isEmpty) {
        children.add(const SizedBox(height: 6));
        continue;
      }

      final isSection = _sectionPattern.hasMatch(trimmed);
      final isBullet = trimmed.startsWith('- ') || trimmed.startsWith('• ');
      final isNumbered = RegExp(r'^\d+\.\s').hasMatch(trimmed);

      children.add(
        Padding(
          padding: EdgeInsets.only(
            top: isSection ? 8 : 2,
            bottom: 2,
            left: isBullet || isNumbered ? 8 : 0,
          ),
          child: Text(
            trimmed,
            style: TextStyle(
              color: AppTheme.textPrimary,
              fontSize: isSection ? 13.5 : 14,
              height: 1.45,
              fontWeight: isSection ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: children,
    );
  }
}
