import json
from collections import defaultdict, deque
from pathlib import Path
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

    def load(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        for user_id, messages in data.items():
            if isinstance(messages, list):
                self._sessions[user_id] = deque(messages[-self._max_messages :], maxlen=self._max_messages)

    def save(self, file_path: str) -> None:
        path = Path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {user_id: list(messages) for user_id, messages in self._sessions.items()}
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


def build_messages(
    settings: Any,
    history: list[dict[str, str]],
    user_text: str,
) -> list[dict[str, str]]:
    system_parts = [settings.persona_prompt]
    style_examples = getattr(settings, "style_examples", "").strip()
    if style_examples:
        system_parts.append("\u8bf4\u8bdd\u98ce\u683c\u793a\u4f8b\uff1a\n" + style_examples)

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        *history,
        {"role": "user", "content": user_text},
    ]
