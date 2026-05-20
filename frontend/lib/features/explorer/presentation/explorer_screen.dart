import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/monokai-sublime.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../../core/layout/responsive.dart';
import '../../../core/theme/app_theme.dart';
import '../domain/graph_models.dart';
import 'providers/explorer_provider.dart';
import 'widgets/architecture_graph_view.dart';
import 'widgets/explorer_tree.dart';
import 'widgets/rag_chat_panel.dart';

class ExplorerScreen extends StatefulWidget {
  const ExplorerScreen({super.key, required this.repositoryId, this.repositoryName});

  final String repositoryId;
  final String? repositoryName;

  @override
  State<ExplorerScreen> createState() => _ExplorerScreenState();
}

class _ExplorerScreenState extends State<ExplorerScreen> with TickerProviderStateMixin {
  TabController? _mobileTabController;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<ExplorerProvider>().load(
            widget.repositoryId,
            name: widget.repositoryName,
          );
    });
  }

  @override
  void dispose() {
    _mobileTabController?.dispose();
    super.dispose();
  }

  TabController _mobileTabs() {
    return _mobileTabController ??= TabController(length: 3, vsync: this);
  }

  @override
  Widget build(BuildContext context) {
    final explorer = context.watch<ExplorerProvider>();
    final compact = Responsive.isCompact(context);

    if (explorer.loading) {
      return const Scaffold(
        backgroundColor: AppTheme.pageBackdrop,
        body: Center(child: CircularProgressIndicator(color: AppTheme.accent)),
      );
    }

    return _ExplorerLoadedBody(
      explorer: explorer,
      compact: compact,
      centerTabIndex: explorer.centerTabIndex,
      mobileTabController: compact ? _mobileTabs() : null,
      onOpenTree: compact ? (ctx, exp) => _openTreeDrawer(ctx, exp) : null,
    );
  }

  void _openTreeDrawer(BuildContext context, ExplorerProvider explorer) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppTheme.surface,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.65,
        minChildSize: 0.4,
        maxChildSize: 0.9,
        builder: (_, scrollController) => ExplorerTree(
          rootId: explorer.rootId,
          nodes: explorer.nodes,
          selectedId: explorer.selectedNodeId,
          onSelect: (id) {
            explorer.selectNode(id);
            Navigator.pop(sheetContext);
          },
          scrollController: scrollController,
        ),
      ),
    );
  }
}

class _ExplorerLoadedBody extends StatelessWidget {
  const _ExplorerLoadedBody({
    required this.explorer,
    required this.compact,
    required this.centerTabIndex,
    this.mobileTabController,
    this.onOpenTree,
  });

  final ExplorerProvider explorer;
  final bool compact;
  final int centerTabIndex;
  final TabController? mobileTabController;
  final void Function(BuildContext context, ExplorerProvider explorer)? onOpenTree;

  @override
  Widget build(BuildContext context) {
    final tree = ExplorerTree(
      rootId: explorer.rootId,
      nodes: explorer.nodes,
      selectedId: explorer.selectedNodeId,
      onSelect: explorer.selectNode,
    );

    final graphPanel = Selector<ExplorerProvider, _GraphPanelModel>(
        selector: (_, p) => _GraphPanelModel(
          nodes: p.nodes,
          edges: p.edges,
          rootId: p.rootId,
          selectedId: p.selectedNodeId,
          highlightedIds: p.highlightedNodeIds,
        ),
        builder: (context, model, _) => ArchitectureGraphView(
          nodes: model.nodes,
          edges: model.edges,
          rootId: model.rootId,
          selectedId: model.selectedId,
          highlightedIds: model.highlightedIds,
          onSelect: explorer.selectNode,
        ),
    );

    final detailsPanel = Selector<ExplorerProvider, Map<String, dynamic>?>(
      selector: (_, p) => p.nodeDetail,
      builder: (context, detail, _) => _NodeDetailsPanel(detail: detail),
    );

    final chatPanel = Selector<ExplorerProvider, _ChatPanelModel>(
      selector: (_, p) => _ChatPanelModel(
        messages: p.messages,
        streaming: p.chatStreaming,
        beginnerMode: p.beginnerMode,
      ),
      builder: (context, model, _) => RagChatPanel(
        messages: model.messages,
        streaming: model.streaming,
        beginnerMode: model.beginnerMode,
        onBeginnerChanged: explorer.setBeginnerMode,
        onSend: explorer.sendChat,
        onCitationTap: (nodeId) {
          if (nodeId != null) explorer.selectNode(nodeId);
        },
      ),
    );

    return Scaffold(
      backgroundColor: AppTheme.pageBackdrop,
      body: SafeArea(
          child: Column(
            children: [
              _ExplorerAppBar(
                title: explorer.repositoryName ?? 'Repository',
                compact: compact,
                onOpenTree: onOpenTree != null ? () => onOpenTree!(context, explorer) : null,
              ),
              Expanded(
                child: compact
                    ? _CompactExplorerLayout(
                        tabController: mobileTabController!,
                        activeTabIndex: centerTabIndex,
                        graphPanel: graphPanel,
                        detailsPanel: detailsPanel,
                        chatPanel: chatPanel,
                      )
                    : Responsive.isMedium(context)
                        ? Row(
                            children: [
                              SizedBox(width: 220, child: tree),
                              const VerticalDivider(width: 1, color: AppTheme.border),
                              Expanded(
                                child: _CenterTabs(
                                  activeTabIndex: centerTabIndex,
                                  onTabChanged: explorer.setCenterTab,
                                  graphPanel: graphPanel,
                                  detailsPanel: detailsPanel,
                                ),
                              ),
                              const VerticalDivider(width: 1, color: AppTheme.border),
                              SizedBox(width: 300, child: chatPanel),
                            ],
                          )
                        : Row(
                            children: [
                              SizedBox(width: 260, child: tree),
                              const VerticalDivider(width: 1, color: AppTheme.border),
                              Expanded(
                                child: _CenterTabs(
                                  activeTabIndex: centerTabIndex,
                                  onTabChanged: explorer.setCenterTab,
                                  graphPanel: graphPanel,
                                  detailsPanel: detailsPanel,
                                ),
                              ),
                              const VerticalDivider(width: 1, color: AppTheme.border),
                              SizedBox(width: 380, child: chatPanel),
                            ],
                          ),
              ),
            ],
          ),
        ),
    );
  }
}

class _ExplorerAppBar extends StatelessWidget {
  const _ExplorerAppBar({
    required this.title,
    required this.compact,
    this.onOpenTree,
  });

  final String title;
  final bool compact;
  final VoidCallback? onOpenTree;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: Responsive.horizontalPadding(context),
        vertical: 8,
      ),
      decoration: BoxDecoration(
        color: AppTheme.surface.withValues(alpha: 0.9),
        border: const Border(bottom: BorderSide(color: AppTheme.border)),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.go('/'),
          ),
          if (compact && onOpenTree != null) ...[
            IconButton(
              icon: const Icon(Icons.account_tree),
              onPressed: onOpenTree,
              color: AppTheme.accent,
              tooltip: 'Project tree',
            ),
          ],
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _CenterTabs extends StatefulWidget {
  const _CenterTabs({
    required this.activeTabIndex,
    required this.onTabChanged,
    required this.graphPanel,
    required this.detailsPanel,
  });

  final int activeTabIndex;
  final ValueChanged<int> onTabChanged;
  final Widget graphPanel;
  final Widget detailsPanel;

  @override
  State<_CenterTabs> createState() => _CenterTabsState();
}

class _CenterTabsState extends State<_CenterTabs> with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.activeTabIndex.clamp(0, 1),
    );
    _tabs.addListener(_onTabChanged);
  }

  @override
  void didUpdateWidget(_CenterTabs oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.activeTabIndex != _tabs.index && !_tabs.indexIsChanging) {
      _tabs.animateTo(widget.activeTabIndex.clamp(0, 1));
    }
  }

  void _onTabChanged() {
    if (_tabs.indexIsChanging) return;
    widget.onTabChanged(_tabs.index);
    setState(() {});
  }

  @override
  void dispose() {
    _tabs.removeListener(_onTabChanged);
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TabBar(
          controller: _tabs,
          tabs: const [
            Tab(icon: Icon(Icons.hub, size: 18), text: 'Architecture'),
            Tab(icon: Icon(Icons.info_outline, size: 18), text: 'Details'),
          ],
        ),
        Expanded(
          child: _tabs.index == 0 ? widget.graphPanel : widget.detailsPanel,
        ),
      ],
    );
  }
}

class _CompactExplorerLayout extends StatefulWidget {
  const _CompactExplorerLayout({
    required this.tabController,
    required this.activeTabIndex,
    required this.graphPanel,
    required this.detailsPanel,
    required this.chatPanel,
  });

  final TabController tabController;
  final int activeTabIndex;
  final Widget graphPanel;
  final Widget detailsPanel;
  final Widget chatPanel;

  @override
  State<_CompactExplorerLayout> createState() => _CompactExplorerLayoutState();
}

class _CompactExplorerLayoutState extends State<_CompactExplorerLayout> {
  @override
  void initState() {
    super.initState();
    widget.tabController.addListener(_onTabChanged);
  }

  @override
  void dispose() {
    widget.tabController.removeListener(_onTabChanged);
    super.dispose();
  }

  @override
  void didUpdateWidget(_CompactExplorerLayout oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.activeTabIndex != widget.tabController.index &&
        !widget.tabController.indexIsChanging) {
      widget.tabController.animateTo(widget.activeTabIndex.clamp(0, 2));
    }
  }

  void _onTabChanged() {
    if (widget.tabController.indexIsChanging) return;
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final index = widget.tabController.index;
    final body = switch (index) {
      0 => widget.graphPanel,
      1 => widget.detailsPanel,
      _ => widget.chatPanel,
    };

    return Column(
      children: [
        TabBar(
          controller: widget.tabController,
          tabs: const [
            Tab(icon: Icon(Icons.hub), text: 'Graph'),
            Tab(icon: Icon(Icons.info_outline), text: 'Details'),
            Tab(icon: Icon(Icons.chat_bubble_outline), text: 'Chat'),
          ],
        ),
        Expanded(child: body),
      ],
    );
  }
}

class _NodeDetailsPanel extends StatelessWidget {
  const _NodeDetailsPanel({this.detail});

  final Map<String, dynamic>? detail;

  @override
  Widget build(BuildContext context) {
    if (detail == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.touch_app, size: 48, color: AppTheme.accent.withValues(alpha: 0.5)),
            const SizedBox(height: 12),
            Text(
              'Select a node to view details',
              style: TextStyle(color: AppTheme.textMuted),
            ),
          ],
        ),
      );
    }
    if (detail!['error'] != null) {
      return Center(
        child: Text(detail!['error'].toString(), style: const TextStyle(color: AppTheme.danger)),
      );
    }

    final code = detail!['code'] as String?;
    final language = (detail!['language'] as String?) ?? 'plaintext';
    final nodeType = detail!['type'] as String? ?? '';
    final typeColor = AppTheme.nodeTypeColor(nodeType);

    return ListView(
      padding: EdgeInsets.all(Responsive.horizontalPadding(context)),
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: typeColor.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: typeColor.withValues(alpha: 0.5)),
          ),
          child: Text(
            nodeType,
            style: TextStyle(color: typeColor, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          detail!['name']?.toString() ?? '',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(
          detail!['file_path']?.toString() ?? '',
          style: const TextStyle(color: AppTheme.accent, fontFamily: 'monospace', fontSize: 13),
        ),
        if (detail!['start_line'] != null)
          Text(
            'Lines ${detail!['start_line']}–${detail!['end_line']}',
            style: const TextStyle(color: AppTheme.textMuted),
          ),
        const SizedBox(height: 12),
        Text(detail!['explanation']?.toString() ?? ''),
        const SizedBox(height: 16),
        if (code != null && code.isNotEmpty)
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.border),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: HighlightView(
                code,
                language: _highlightLang(language),
                theme: monokaiSublimeTheme,
                padding: const EdgeInsets.all(12),
                textStyle: const TextStyle(fontFamily: 'monospace', fontSize: 13),
              ),
            ),
          ),
        const SizedBox(height: 16),
        _CallSection(title: 'Incoming calls', items: detail!['incoming_calls'] as List<dynamic>?),
        _CallSection(title: 'Outgoing calls', items: detail!['outgoing_calls'] as List<dynamic>?),
      ],
    );
  }

  String _highlightLang(String lang) {
    const map = {
      'python': 'python',
      'javascript': 'javascript',
      'typescript': 'typescript',
      'tsx': 'typescript',
      'go': 'go',
      'rust': 'rust',
      'java': 'java',
      'c': 'c',
      'cpp': 'cpp',
      'c_sharp': 'csharp',
      'ruby': 'ruby',
      'php': 'php',
      'kotlin': 'kotlin',
      'swift': 'swift',
    };
    return map[lang] ?? 'plaintext';
  }
}

class _GraphPanelModel {
  const _GraphPanelModel({
    required this.nodes,
    required this.edges,
    required this.rootId,
    required this.selectedId,
    required this.highlightedIds,
  });

  final List<GraphNodeModel> nodes;
  final List<GraphEdgeModel> edges;
  final String? rootId;
  final String? selectedId;
  final Set<String> highlightedIds;

  @override
  bool operator ==(Object other) {
    return other is _GraphPanelModel &&
        identical(nodes, other.nodes) &&
        identical(edges, other.edges) &&
        rootId == other.rootId &&
        selectedId == other.selectedId &&
        setEquals(highlightedIds, other.highlightedIds);
  }

  @override
  int get hashCode => Object.hash(nodes, edges, rootId, selectedId, highlightedIds);
}

class _ChatPanelModel {
  const _ChatPanelModel({
    required this.messages,
    required this.streaming,
    required this.beginnerMode,
  });

  final List<ChatMessage> messages;
  final bool streaming;
  final bool beginnerMode;

  @override
  bool operator ==(Object other) {
    if (other is! _ChatPanelModel) return false;
    if (streaming != other.streaming || beginnerMode != other.beginnerMode) {
      return false;
    }
    if (messages.length != other.messages.length) return false;
    for (var i = 0; i < messages.length; i++) {
      if (messages[i].text != other.messages[i].text) return false;
    }
    return true;
  }

  @override
  int get hashCode {
    var h = Object.hash(streaming, beginnerMode, messages.length);
    for (final m in messages) {
      h = Object.hash(h, m.text);
    }
    return h;
  }
}

class _CallSection extends StatelessWidget {
  const _CallSection({required this.title, this.items});

  final String title;
  final List<dynamic>? items;

  @override
  Widget build(BuildContext context) {
    final list = items ?? [];
    if (list.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.accent)),
        ...list.map(
          (item) => ListTile(
            dense: true,
            leading: const Icon(Icons.call_made, size: 16, color: AppTheme.textMuted),
            title: Text(item['name']?.toString() ?? ''),
            subtitle: Text(item['file_path']?.toString() ?? ''),
          ),
        ),
      ],
    );
  }
}
