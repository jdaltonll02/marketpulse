"""
pipeline — Public entry point for the MarketPulse intelligence pipeline.

Sub-packages
------------
scrapers/       Fetch raw data from external sources (Bright Data, SEC, Yahoo Finance)
signals/        Convert raw data into typed signal objects (news, hiring)
synthesis/      AI layer: single-agent, multi-agent, RAG, drift detection
schema.py       Pydantic models for all data structures

Usage
-----
    from pipeline import run_pipeline

    obj = run_pipeline("AAPL", "Apple Inc.")
    print(obj.composite_signal, obj.confidence)
"""
from pipeline.run import run_pipeline

__all__ = ["run_pipeline"]
