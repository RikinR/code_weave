/// Left-to-right tree layout algorithm for architecture graph nodes.
///
/// Computes pixel positions for hierarchy nodes rendered by
/// [ArchitectureGraphCanvas] in the explorer Architecture tab.
library;
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../domain/graph_models.dart';

/// Layout result with node positions, canvas size, and depth levels.
class FolderGraphLayout {
  FolderGraphLayout({
    required this.positions,
    required this.size,
    required this.levels,
  });

  final Map<String, Offset> positions;
  final Size size;
  final Map<String, int> levels;

  static const double nodeWidth = 140;
  static const double nodeHeight = 32;
  static const double levelGap = 52;
  static const double siblingGap = 14;
  static const double padding = 24;

  /// Computes a folder-tree layout rooted at [rootId] from flat [nodes].
  static FolderGraphLayout compute({
    required String rootId,
    required List<GraphNodeModel> nodes,
  }) {
    final byId = {for (final n in nodes) n.id: n};
    final children = <String, List<GraphNodeModel>>{};
    for (final n in nodes) {
      final parent = n.parentId;
      if (parent == null) continue;
      children.putIfAbsent(parent, () => []).add(n);
    }
    for (final list in children.values) {
      list.sort((a, b) {
        final typeOrder = _typeSortKey(a.type).compareTo(_typeSortKey(b.type));
        if (typeOrder != 0) return typeOrder;
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      });
    }

    final positions = <String, Offset>{};
    final levels = <String, int>{};

    double subtreeHeight(String id) {
      final kids = children[id] ?? const [];
      if (kids.isEmpty) return nodeHeight;
      var h = 0.0;
      for (var i = 0; i < kids.length; i++) {
        h += subtreeHeight(kids[i].id);
        if (i < kids.length - 1) h += siblingGap;
      }
      return h;
    }

    void place(String id, double top, int depth) {
      levels[id] = depth;
      final kids = children[id] ?? const [];
      final x = padding + depth * (nodeWidth + levelGap);
      if (kids.isEmpty) {
        positions[id] = Offset(x, top);
        return;
      }
      var cursor = top;
      final childCenters = <double>[];
      for (final child in kids) {
        final h = subtreeHeight(child.id);
        place(child.id, cursor, depth + 1);
        childCenters.add(cursor + h / 2);
        cursor += h + siblingGap;
      }
      final centerY = (childCenters.first + childCenters.last) / 2;
      positions[id] = Offset(x, centerY - nodeHeight / 2);
    }

    if (byId.containsKey(rootId)) {
      place(rootId, padding, 0);
    }

    if (positions.isEmpty) {
      return FolderGraphLayout(
        positions: const {},
        size: Size(nodeWidth + padding * 2, nodeHeight + padding * 2),
        levels: const {},
      );
    }

    var minY = double.infinity;
    var maxX = -double.infinity;
    var maxY = -double.infinity;
    for (final p in positions.values) {
      minY = math.min(minY, p.dy);
      maxX = math.max(maxX, p.dx + nodeWidth);
      maxY = math.max(maxY, p.dy + nodeHeight);
    }
    final shiftY = padding - minY;
    final shifted = <String, Offset>{};
    for (final e in positions.entries) {
      shifted[e.key] = Offset(e.value.dx, e.value.dy + shiftY);
    }
    final width = maxX + padding;
    final height = maxY - minY + padding * 2;
    return FolderGraphLayout(
      positions: shifted,
      size: Size(width, height),
      levels: levels,
    );
  }

  static int _typeSortKey(String type) {
    return switch (type) {
      'repository' => 0,
      'folder' => 1,
      'file' => 2,
      'class' => 3,
      'function' => 4,
      'method' => 5,
      _ => 9,
    };
  }
}
