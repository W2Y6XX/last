# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Type

This directory contains Python package installations, primarily the LangGraph library and its dependencies. This is **not** a development project directory but rather a Python environment/site-packages directory.

## Structure

- `langgraph/` - Main LangGraph package directory containing:
  - `graph/` - Core graph implementations (StateGraph, MessageGraph)
  - `checkpoint/` - Checkpointing functionality for persistence
  - `cache/` - Caching implementations (memory, Redis)
  - `channels/` - Communication channels between nodes
  - `prebuilt/` - Pre-built components and utilities
  - `store/` - Storage abstractions
  - `types.py` - Core type definitions
  - `config.py` - Configuration utilities

- Additional installed packages include:
  - `langchain_core/` - LangChain core functionality
  - `langsmith/` - LangSmith tracing and monitoring
  - `pydantic/` - Data validation and parsing
  - `httpx/`, `urllib3/` - HTTP client libraries
  - Various supporting libraries (yaml, jsonpatch, tenacity, etc.)

## Working with LangGraph

When working with LangGraph code in this environment:

1. **Import patterns**: Use `from langgraph.graph import StateGraph, START, END` for basic graph functionality
2. **State management**: Import `MessagesState, add_messages` for message-based state handling
3. **Checkpointing**: Use `from langgraph.checkpoint` modules for persistence
4. **Configuration**: Check `langgraph.config` for configuration utilities

## Notes

- This is a read-only package installation directory
- For development work, you would typically work in a different project directory that imports these packages
- The actual source code for development would be in a separate repository
- Package versions can be determined by checking the `.dist-info` directories