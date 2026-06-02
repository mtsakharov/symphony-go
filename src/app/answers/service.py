"""Service entrypoint for grounded answers."""

from __future__ import annotations

from typing import cast

from app.answers.contracts import AnswerChatModel, AnswerRetriever
from app.answers.flow import AnswerFlowSettings, AnswerFlowState, build_answer_graph
from app.answers.schemas import AnswerResponse


class AnswerService:
    """Execute the LangGraph answer flow."""

    def __init__(self, flow_settings: AnswerFlowSettings | None = None) -> None:
        self.flow_settings = flow_settings or AnswerFlowSettings()
        self._graph = build_answer_graph()

    def answer_question(
        self,
        *,
        user_id: str,
        question: str,
        retriever: AnswerRetriever,
        model: AnswerChatModel,
    ) -> AnswerResponse:
        """Answer a question using retrieved post evidence."""

        result = cast(
            AnswerFlowState,
            self._graph.invoke(
                {
                    "user_id": user_id,
                    "question": question,
                    "retriever": retriever,
                    "model": model,
                    "settings": self.flow_settings,
                }
            ),
        )
        answer = result["answer"]
        is_fallback = answer == self.flow_settings.fallback_message
        return AnswerResponse(
            answer=answer,
            is_fallback=is_fallback,
            citations=[] if is_fallback else result.get("citations", []),
        )
