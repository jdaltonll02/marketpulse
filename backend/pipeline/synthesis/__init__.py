"""
pipeline/synthesis — AI synthesis layer.

Modules
-------
rag.py          Vector memory: store and retrieve context per company (ChromaDB)
agent.py        Single-agent Claude synthesis
multi_agent.py  Multi-agent synthesis: 4 specialists + orchestrator
drift.py        Signal drift detection and explanation between runs

Public API
----------
    from pipeline.synthesis import synthesise_multi_agent, synthesise, detect_drift
    from pipeline.synthesis.rag import store_context, retrieve_context
"""
from pipeline.synthesis.multi_agent import synthesise_multi_agent
from pipeline.synthesis.agent       import synthesise
from pipeline.synthesis.drift       import detect_drift
from pipeline.synthesis.rag         import store_context, retrieve_context

__all__ = [
    "synthesise_multi_agent",
    "synthesise",
    "detect_drift",
    "store_context",
    "retrieve_context",
]
