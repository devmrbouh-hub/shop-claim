"""Generate mod config.json for download."""

from __future__ import annotations

from typing import Any

from shop_claim_portal.config import get_settings


def build_mod_config(
    *,
    server_id: str,
    shop_server_id: int,
    api_token: str,
    theme_prefix: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    bridge_url = settings.bridge_public_url
    if not bridge_url.endswith("/"):
        bridge_url += "/"
    gui: dict[str, Any] = {}
    if theme_prefix:
        gui["theme_prefix"] = theme_prefix
    return {
        "bridge_url": bridge_url,
        "server_id": server_id,
        "api_token": api_token,
        "shop_server_id": shop_server_id,
        "claim_command": "shop",
        "enable_chat_commands": False,
        "container_class": "SeaChest",
        "container_empty_check_sec": 5,
        "abandoned_container_hours": 24,
        "vehicle_spawn_cooldown_sec": 30,
        "container_spawn_distance_m": 1.2,
        "container_spawn_max_slope_deg": 25,
        "container_spawn_check_radius_m": 0.8,
        "container_respawn_cooldown_sec": 30,
        "gui": gui,
        "messages": {
            "prefix": "[Магазин]",
            "no_purchases": "Нет незабранных покупок.",
            "container_active": "Сначала заберите предметы из ящика или нажмите «Пересоздать ящик».",
            "vehicle_no_space": "Нет места для техники. Отойдите в открытую область и попробуйте снова.",
            "delivered_container": "Ящик с покупкой создан рядом с вами.",
            "delivered_vehicle": "Техника выдана.",
            "service_unavailable": "Сервис магазина временно недоступен.",
            "please_wait": "Подождите…",
            "vehicle_not_available": "Выдача техники будет в следующем обновлении.",
            "invalid_index": "Неверный номер покупки.",
            "list_stale": "Обновите список покупок.",
            "claim_failed": "Не удалось выдать покупку.",
            "container_bad_surface": "Заберите покупку на суше, не у воды.",
            "container_respawn_ok": "Ящик пересоздан. Заберите оставшиеся предметы.",
            "container_respawn_none": "Нет активного ящика для пересоздания.",
            "container_nothing_left": "Все предметы уже получены.",
        },
    }
