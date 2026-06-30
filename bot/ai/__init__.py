# -*- coding: utf-8 -*-
"""Astrum AI module.

Core AI system for AstrumManager with support for:
- Multiple model providers (OpenAI, Claude, Ollama, local LLMs)
- Knowledge base (file-driven, categorized, searchable)
- Conversation memory (per-user, TTL-managed)
- RAG-ready architecture
- Extensible for future AI capabilities

Designed to be completely independent from Telegram handlers.
Can be reused in Web, Mobile, REST API contexts.
"""
