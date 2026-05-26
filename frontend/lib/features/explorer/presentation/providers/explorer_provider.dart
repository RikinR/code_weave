/// Provider for explorer graph, node details, and RAG chat state.
///
/// Holds hierarchy nodes, call-graph edges, selection, tree expansion, chat
/// messages, and node detail payloads. Calls `GET /api/repositories/{id}/hierarchy`,
/// `GET /api/repositories/{id}/graph`, `GET /api/nodes/{id}`,
/// `GET /api/repositories/{id}/chat/messages`, streaming
/// `POST /api/repositories/{id}/chat`, and fallback
/// `POST /api/repositories/{id}/chat/sync` via [ApiClient].
library;
import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/sse_client.dart';
import '../../domain/graph_models.dart';
import '../../domain/graph_tree_visibility.dart';

/// A single message in the explorer RAG chat panel.
class ChatMessage {
  ChatMessage({
    required this.role,
    required this.text,
    List<Map<String, dynamic>>? citations,
  }) : citations = citations ?? <Map<String, dynamic>>[];

  final String role;
  String text;
  final List<Map<String, dynamic>> citations;
}

/// ChangeNotifier backing [ExplorerScreen] tree, graph, details, and chat panels.
class ExplorerProvider extends ChangeNotifier {
  ExplorerProvider(this._api);

  final ApiClient _api;

  /// Currently loaded repository id from the route.
  String? repositoryId;

  /// Display name from route query or backend.
  String? repositoryName;

  /// Flat list of hierarchy nodes for tree and graph views.
  List<GraphNodeModel> nodes = [];

  /// Call-graph edges (used for future graph overlays).
  List<GraphEdgeModel> edges = [];

  /// Root hierarchy node id from backend.
  String? rootId;

  /// Id of the node selected for the details panel.
  String? selectedNodeId;

  /// Node ids with expanded children in tree and graph.
  Set<String> expandedNodeIds = {};

  /// Node ids highlighted by RAG citation responses.
  Set<String> highlightedNodeIds = {};

  /// Detail payload for [selectedNodeId] from `GET /api/nodes/{id}`.
  Map<String, dynamic>? nodeDetail;

  /// Active center tab index (architecture vs details) on medium+ layouts.
  int centerTabIndex = 0;

  /// True while hierarchy and graph are loading.
  bool loading = false;

  /// True while node detail is being fetched.
  bool detailLoading = false;

  /// Last load error, if any.
  String? error;

  /// When true, chat requests use simplified beginner-oriented prompts.
  bool beginnerMode = false;

  /// Updates beginner mode for subsequent chat queries.
  void setBeginnerMode(bool value) {
    beginnerMode = value;
    notifyListeners();
  }

  /// Switches the architecture/details tab on medium and expanded layouts.
  void setCenterTab(int index) {
    centerTabIndex = index;
    notifyListeners();
  }
  final List<ChatMessage> messages = [];
  bool chatStreaming = false;
  Timer? _highlightDebounce;

  @override
  void dispose() {
    _highlightDebounce?.cancel();
    super.dispose();
  }

  /// Loads hierarchy, graph, and chat history for repository [repoId].
  Future<void> load(String repoId, {String? name}) async {
    repositoryId = repoId;
    repositoryName = name;
    loading = true;
    error = null;
    nodes = [];
    edges = [];
    rootId = null;
    selectedNodeId = null;
    expandedNodeIds = {};
    highlightedNodeIds = {};
    nodeDetail = null;
    messages.clear();
    chatStreaming = false;
    notifyListeners();
    try {
      final hierarchy = await _api.getHierarchy(repoId);
      final graph = await _api.getGraph(repoId);
      rootId = hierarchy['root_id'] as String?;
      nodes = (hierarchy['nodes'] as List<dynamic>)
          .map((e) => GraphNodeModel.fromJson(e as Map<String, dynamic>))
          .toList();
      edges = (graph['edges'] as List<dynamic>)
          .map((e) => GraphEdgeModel.fromJson(e as Map<String, dynamic>))
          .toList();
      if (rootId != null) {
        expandedNodeIds = {rootId!};
      }
      try {
        final chatHistory = await _api.getChatMessages(repoId);
        messages.addAll(
          chatHistory.map(
            (row) => ChatMessage(
              role: row['role'] as String,
              text: row['content'] as String? ?? '',
              citations: (row['citations'] as List<dynamic>? ?? [])
                  .cast<Map<String, dynamic>>(),
            ),
          ),
        );
      } catch (_) {
      }
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Toggles expand/collapse for [nodeId] in tree and graph views.
  void toggleNodeExpanded(String nodeId) {
    if (expandedNodeIds.contains(nodeId)) {
      expandedNodeIds.remove(nodeId);
      expandedNodeIds.removeAll(descendantNodeIds(nodeId, nodes));
    } else {
      expandedNodeIds.add(nodeId);
    }
    notifyListeners();
  }

  /// Collapses all nodes except the repository root.
  void collapseAllTreeNodes() {
    if (rootId != null) {
      expandedNodeIds = {rootId!};
    } else {
      expandedNodeIds = {};
    }
    notifyListeners();
  }

  /// Selects [nodeId], expands its path, and loads detail from the backend.
  Future<void> selectNode(String nodeId) async {
    selectedNodeId = nodeId;
    if (rootId != null) {
      expandPathToNode(nodeId, rootId!, nodes, expandedNodeIds);
    }
    centerTabIndex = 1;
    detailLoading = true;
    nodeDetail = null;
    notifyListeners();
    try {
      nodeDetail = await _api.getNodeDetail(nodeId);
    } catch (e) {
      nodeDetail = {'error': e.toString()};
    } finally {
      detailLoading = false;
      notifyListeners();
    }
  }

  /// Highlights [ids] from RAG citations with debounced UI updates.
  void highlightNodes(Set<String> ids) {
    highlightedNodeIds = ids;
    _highlightDebounce?.cancel();
    _highlightDebounce = Timer(const Duration(milliseconds: 80), () {
      _highlightDebounce = null;
      notifyListeners();
    });
  }

  void _applyChatMeta(Map<String, dynamic> data, ChatMessage assistant) {
    final citations =
        (data['citations'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    assistant.citations.addAll(citations);
    final highlights =
        (data['highlight_node_ids'] as List<dynamic>? ?? []).cast<String>();
    highlightNodes(highlights.toSet());
  }

  /// Sends a RAG [query] via SSE with sync fallback and updates [messages].
  Future<void> sendChat(String query) async {
    if (repositoryId == null || query.trim().isEmpty) return;
    final userMsg = ChatMessage(role: 'user', text: query);
    final assistant = ChatMessage(role: 'assistant', text: '');
    messages.add(userMsg);
    messages.add(assistant);
    chatStreaming = true;
    notifyListeners();

    var streamed = false;
    try {
      await listenSse(
        '/api/repositories/$repositoryId/chat',
        method: 'POST',
        body: {
          'query': query,
          'top_k': 5,
          'beginner_mode': beginnerMode,
        },
        onEvent: (event, data) {
          if (event == 'meta') {
            _applyChatMeta(data, assistant);
            notifyListeners();
          } else if (event == 'token') {
            final token = data['token'] as String? ?? '';
            if (token.isNotEmpty) {
              streamed = true;
              assistant.text += token;
              notifyListeners();
            }
          } else if (event == 'answer') {
            final answer = data['answer'] as String? ?? '';
            if (answer.isNotEmpty) {
              assistant.text = answer;
              notifyListeners();
            }
          } else if (event == 'error') {
            assistant.text = data['error']?.toString() ?? 'Chat failed';
            notifyListeners();
          }
        },
      );
    } catch (_) {
      streamed = false;
    }

    if (!streamed || assistant.text.isEmpty) {
      try {
        final data = await _api.chatSync(
          repositoryId: repositoryId!,
          query: query,
          beginnerMode: beginnerMode,
        );
        _applyChatMeta(data, assistant);
        assistant.text = data['answer'] as String? ?? '';
      } catch (e) {
        assistant.text = assistant.text.isEmpty
            ? 'Chat failed: $e'
            : '${assistant.text}\n\n(stream interrupted: $e)';
      }
    }

    if (assistant.text.isEmpty) {
      assistant.text = 'No response from the assistant. Check GROQ_API_KEY in backend/.env.';
    }

    chatStreaming = false;
    notifyListeners();
  }

  /// Looks up a node by [id] in the loaded [nodes] list.
  GraphNodeModel? nodeById(String id) {
    for (final n in nodes) {
      if (n.id == id) return n;
    }
    return null;
  }

  /// Returns direct children of [id] in the hierarchy.
  List<GraphNodeModel> childrenOf(String id) {
    return nodes.where((n) => n.parentId == id).toList();
  }
}
