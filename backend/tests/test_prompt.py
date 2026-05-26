"""Verify RAG prompt construction and chat temperature by experience mode.

Covers ``application.retrieval.prompt.build_rag_messages`` and
``chat_temperature`` for beginner tutor prompts versus structured default prompts.
"""

from application.retrieval.prompt import build_rag_messages, chat_temperature

def test_beginner_mode_uses_tutor_prompt():
    messages = build_rag_messages('what is foo?', [], beginner_mode=True)
    system = messages[0]['content']
    user = messages[1]['content']
    assert 'tutor' in system.lower()
    assert 'Steps:' in system
    assert 'learning to code' in user

def test_default_mode_uses_structured_prompt():
    messages = build_rag_messages('what is foo?', [], beginner_mode=False)
    system = messages[0]['content']
    assert 'Summary:' in system
    assert 'How it works:' in system
    assert 'Do not wrap identifiers' in system

def test_beginner_mode_has_higher_temperature():
    assert chat_temperature(beginner_mode=True) > chat_temperature(beginner_mode=False)
