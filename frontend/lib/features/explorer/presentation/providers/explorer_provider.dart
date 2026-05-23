import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/sse_client.dart';
import '../../domain/graph_models.dart';

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

class ExplorerProvider extends ChangeNotifier {
  ExplorerProvider(this._api);

  final ApiClient _api;

  String? repositoryId;
  String? repositoryName;
  List<GraphNodeModel> nodes = [];
  List<GraphEdgeModel> edges = [];
  String? rootId;
  String? selectedNodeId;
  Set<String> highlightedNodeIds = {};
  Map<String, dynamic>? nodeDetail;
  int centerTabIndex = 0;
  bool loading = false;
  String? error;

  bool beginnerMode = false;

  void setBeginnerMode(bool value) {
    beginnerMode = value;
    notifyListeners();
  }

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

  Future<void> load(String repoId, {String? name}) async {
    repositoryId = repoId;
    repositoryName = name;
    loading = true;
    error = null;
    nodes = [];
    edges = [];
    rootId = null;
    selectedNodeId = null;
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

  Future<void> selectNode(String nodeId) async {
    selectedNodeId = nodeId;
    centerTabIndex = 1;
    notifyListeners();
    try {
      nodeDetail = await _api.getNodeDetail(nodeId);
    } catch (e) {
      nodeDetail = {'error': e.toString()};
    }
    notifyListeners();
  }

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

  GraphNodeModel? nodeById(String id) {
    for (final n in nodes) {
      if (n.id == id) return n;
    }
    return null;
  }

  List<GraphNodeModel> childrenOf(String id) {
    return nodes.where((n) => n.parentId == id).toList();
  }
}
