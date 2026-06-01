"""
PRIS-JARVIS Agent — Núcleo del asistente IA omnipresente
==========================================================
Arquitectura base: Function Calling + RBAC + Contexto.
"""
from core.agent.pris_agent import PrisAgent, get_pris_context

__all__ = ['PrisAgent', 'get_pris_context']
