"""
research_lab/chat — PDF Research Chat subpackage.

Provides a FastAPI APIRouter that adds PDF-grounded conversational chat
to the LabOS Research Analysis Engine. Mount with:

    from chat import chat_router
    app.include_router(chat_router)
"""

from .router import chat_router

__all__ = ["chat_router"]
