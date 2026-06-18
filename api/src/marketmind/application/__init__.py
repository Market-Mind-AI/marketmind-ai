"""Application layer — use cases, outbound ports, DTOs.

Framework-free: stdlib + domain only. No FastAPI, LangGraph, or SQLAlchemy
imports anywhere under this package. The use cases orchestrate the domain via
the outbound ports defined in ``application.ports``.
"""
