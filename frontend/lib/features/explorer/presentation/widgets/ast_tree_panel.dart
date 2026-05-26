/// Tree-sitter parse tree viewer for node detail payloads.
///
/// Renders the `ast_tree` field from `GET /api/nodes/{id}` in the explorer
/// Details tab when the backend includes a truncated AST snapshot.
library;
import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

/// Expandable panel showing a Tree-sitter AST returned by the backend.
class AstTreePanel extends StatelessWidget {
  const AstTreePanel({super.key, required this.astTree});

  /// AST payload map with `root`, `truncated`, and `node_count` keys.
  final Map<String, dynamic>? astTree;

  @override
  Widget build(BuildContext context) {
    if (astTree == null) {
      return Semantics(
        label: 'Parse tree unavailable',
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppTheme.border),
          ),
          child: const Text(
            'Parse tree is not available for this file.',
            style: TextStyle(color: AppTheme.textMuted, fontSize: 13),
          ),
        ),
      );
    }

    final root = astTree!['root'];
    final truncated = astTree!['truncated'] == true;
    final nodeCount = astTree!['node_count'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (truncated)
          Semantics(
            liveRegion: true,
            label: 'Parse tree truncated',
            child: Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.warning.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.warning.withValues(alpha: 0.4)),
              ),
              child: Text(
                'Tree truncated for display'
                '${nodeCount != null ? ' ($nodeCount nodes shown)' : ''}. '
                'Open the source file for the full structure.',
                style: const TextStyle(fontSize: 12, height: 1.35),
              ),
            ),
          ),
        Semantics(
          label: 'Parse tree',
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.border),
            ),
            child: root is Map<String, dynamic>
                ? _AstTreeNodeTile(node: root, depth: 0)
                : const Padding(
                    padding: EdgeInsets.all(10),
                    child: Text('Invalid parse tree payload.', style: TextStyle(color: AppTheme.danger)),
                  ),
          ),
        ),
      ],
    );
  }
}

class _AstTreeNodeTile extends StatelessWidget {
  const _AstTreeNodeTile({required this.node, required this.depth});

  final Map<String, dynamic> node;
  final int depth;

  @override
  Widget build(BuildContext context) {
    final type = node['type']?.toString() ?? 'unknown';
    final start = node['start_line'];
    final end = node['end_line'];
    final lineLabel = start != null && end != null ? 'lines $start–$end' : '';
    final semanticsLabel = lineLabel.isEmpty ? type : '$type, $lineLabel';
    final children = node['children'];
    final childMaps = children is List
        ? children.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList()
        : <Map<String, dynamic>>[];

    if (childMaps.isEmpty) {
      return Semantics(
        label: semanticsLabel,
        child: ListTile(
          dense: true,
          visualDensity: VisualDensity.compact,
          contentPadding: EdgeInsets.only(left: 12.0 + depth * 14.0, right: 8),
          title: Text(
            type,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          ),
          subtitle: lineLabel.isEmpty
              ? null
              : Text(lineLabel, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
        ),
      );
    }

    return Semantics(
      label: '$semanticsLabel, expandable',
      child: ExpansionTile(
        tilePadding: EdgeInsets.only(left: 4.0 + depth * 10.0, right: 8),
        childrenPadding: EdgeInsets.zero,
        initiallyExpanded: depth < 2,
        title: Text(
          type,
          style: const TextStyle(fontFamily: 'monospace', fontSize: 12, fontWeight: FontWeight.w500),
        ),
        subtitle: lineLabel.isEmpty
            ? null
            : Text(lineLabel, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
        children: [
          for (final child in childMaps) _AstTreeNodeTile(node: child, depth: depth + 1),
        ],
      ),
    );
  }
}
