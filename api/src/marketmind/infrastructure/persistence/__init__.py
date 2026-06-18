"""Persistence adapters: repositories and vector stores.

In-memory implementations are the offline defaults; the SQLAlchemy / pgvector
implementations are selected when ``provider_mode == "real"`` with a real
database configured. ORM models live separately from domain entities and never
leak across the boundary — mappers translate both directions.
"""
