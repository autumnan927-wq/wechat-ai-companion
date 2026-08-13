from collections import defaultdict, deque
from typing import Any


class SessionStore:
    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages
        self._sessions: dict[str, deque[dict[str, str]]] = defaultdict(deque)

    def get_history(self, user_id: str) -> list[dict[str, str]]:
        return list(self._sessions[user_id])

    def add_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        history = self._sessions[user_id]
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})
        while len(history) > self._max_messages:
            history.popleft()


def build_messages(
    settings: Any,
    history: list[dict[str, str]],
    user_text: str,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": settings.persona_prompt},
        *history,
        {"role": "user", "content": user_text},
    ]
