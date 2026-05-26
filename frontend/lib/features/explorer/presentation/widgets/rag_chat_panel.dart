/// RAG chat sidebar for asking questions about the indexed repository.
///
/// Shown on the right of the explorer on medium+ layouts and as a tab on
/// compact layouts. Sends queries through [ExplorerProvider.sendChat] to
/// the backend streaming chat endpoint with citation chips linking to nodes.
library;
import 'package:flutter/material.dart';

import '../../../../core/layout/responsive.dart';
import '../../../../core/theme/app_theme.dart';
import '../providers/explorer_provider.dart';
import 'structured_chat_text.dart';

/// Chat panel with message history, beginner mode toggle, and query input.
class RagChatPanel extends StatefulWidget {
  const RagChatPanel({
    super.key,
    required this.messages,
    required this.streaming,
    required this.beginnerMode,
    required this.onBeginnerChanged,
    required this.onSend,
    required this.onCitationTap,
  });

  final List<ChatMessage> messages;
  final bool streaming;
  final bool beginnerMode;
  final ValueChanged<bool> onBeginnerChanged;
  final ValueChanged<String> onSend;
  final ValueChanged<String?> onCitationTap;

  @override
  State<RagChatPanel> createState() => _RagChatPanelState();
}

class _RagChatPanelState extends State<RagChatPanel> {
  final controller = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final maxBubbleWidth = Responsive.isCompact(context)
        ? MediaQuery.sizeOf(context).width * 0.85
        : 320.0;

    return Container(
      color: AppTheme.surface,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTheme.border)),
              color: AppTheme.surface,
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final showBeginnerLabel = constraints.maxWidth >= 300;
                return Row(
                  children: [
                    const Icon(Icons.chat_outlined, color: AppTheme.accent, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Row(
                        children: [
                          const Flexible(
                            child: Text(
                              'RAG Assistant',
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                          if (widget.beginnerMode) ...[
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppTheme.accentSoft,
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: const Text(
                                'Beginner',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (showBeginnerLabel)
                      const Text(
                        'Beginner mode',
                        style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                      ),
                    Tooltip(
                      message: 'Beginner mode',
                      child: Switch(
                        value: widget.beginnerMode,
                        onChanged: widget.onBeginnerChanged,
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
          Expanded(
            child: widget.messages.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        'Ask about functions, files, or architecture',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: AppTheme.textMuted),
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    itemCount: widget.messages.length,
                    itemBuilder: (context, index) {
                      final msg = widget.messages[index];
                      final isUser = msg.role == 'user';
                      return Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          constraints: BoxConstraints(maxWidth: maxBubbleWidth),
                          decoration: BoxDecoration(
                            color: isUser ? AppTheme.accentSoft : AppTheme.surfaceHigh,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isUser ? AppTheme.accentSoft : AppTheme.border,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              StructuredChatText(
                                text: msg.text.isEmpty && widget.streaming ? '…' : msg.text,
                                isUser: isUser,
                              ),
                              if (msg.citations.isNotEmpty) ...[
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 4,
                                  runSpacing: 4,
                                  children: msg.citations.map((c) {
                                    return ActionChip(
                                      label: Text(
                                        c['function_name']?.toString() ??
                                            c['file_path']?.toString() ??
                                            'ref',
                                        style: const TextStyle(fontSize: 10),
                                      ),
                                      onPressed: () =>
                                          widget.onCitationTap(c['node_id'] as String?),
                                    );
                                  }).toList(),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          Container(
            padding: EdgeInsets.all(Responsive.isCompact(context) ? 10 : 12),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppTheme.border)),
              color: AppTheme.surfaceHigh,
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: controller,
                    decoration: const InputDecoration(
                      hintText: 'Ask about this repository…',
                      isDense: true,
                    ),
                    onSubmitted: _submit,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: widget.streaming ? null : () => _submit(),
                  icon: widget.streaming
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.send, size: 18),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _submit([String? value]) {
    final text = (value ?? controller.text).trim();
    if (text.isEmpty || widget.streaming) return;
    controller.clear();
    widget.onSend(text);
  }
}
