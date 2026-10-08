"""In-memory game server registry from config."""

from __future__ import annotations

from shop_claim_bridge.models import GameServerConfig


class ServerRegistry:
    def __init__(self, servers: list[GameServerConfig]) -> None:
        self._by_id: dict[str, GameServerConfig] = {}
        self._by_token: dict[str, GameServerConfig] = {}
        for s in servers:
            if not s.enabled:
                continue
            self._by_id[s.server_id] = s
            self._by_token[s.api_token] = s

    def get(self, server_id: str) -> GameServerConfig | None:
        return self._by_id.get(server_id)

    def get_by_token(self, token: str) -> GameServerConfig | None:
        return self._by_token.get(token)

    def list_servers(self) -> list[GameServerConfig]:
        return list(self._by_id.values())
