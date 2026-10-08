# -*- coding: utf-8 -*-
"""Export offers.yaml + vehicle_profiles.yaml → offers-template.xlsx (обратный импорту).

  python export-offers-to-xlsx.py --offers path/to/offers.yaml --profiles path/to/vehicle_profiles.yaml

Requires: openpyxl, pyyaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SCRIPT_DIR = Path(__file__).resolve().parent


def style_sheet(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for col in range(1, sheet.max_column + 1):
        letter = get_column_letter(col)
        max_len = 12
        for row in sheet.iter_rows(
            min_row=1, max_row=sheet.max_row, min_col=col, max_col=col
        ):
            val = row[0].value
            if val is not None:
                max_len = max(max_len, min(len(str(val)) + 2, 60))
        sheet.column_dimensions[letter].width = max_len
    sheet.freeze_panes = "A2"


def _format_server_ids(raw: Any) -> str:
    if not raw:
        return ""
    if isinstance(raw, list):
        return ",".join(str(int(x)) for x in raw)
    return str(raw)


def _attachments_cell(attachments: Any) -> str:
    if not attachments:
        return ""
    if isinstance(attachments, list):
        return ",".join(str(a) for a in attachments)
    return str(attachments)


def _vehicle_give_key(vehicle_class: str, profiles: dict[str, Any]) -> str:
    prof = profiles.get(vehicle_class) or {}
    cargo = prof.get("cargo_items") or []
    for item in cargo:
        if isinstance(item, dict) and item.get("class") == "ExpansionCarKey":
            return "yes"
    return "yes"


def _spawn_cell(offer: dict[str, Any], key: str, yaml_key: str) -> Any:
    spawn = offer.get("spawn") or {}
    val = spawn.get(yaml_key)
    if val is None or val == "":
        return ""
    return val


def append_help_sheet(wb: Workbook) -> None:
    ws4 = wb.create_sheet("справка")
    for row in [
        ["Поле", "Источник", "Пояснение"],
        ["offer_id", "wargm ЛК", "ID предложения в магазине — ключ в offers.yaml"],
        ["name_wargm", "wargm ЛК", "Название для поля name в каталоге"],
        [
            "delivery_online",
            "wargm ЛК",
            "Должно быть yes; в ЛК тип доставки = online",
        ],
        [
            "shop_server_ids",
            "wargm ЛК",
            "Пусто = все сервера; иначе 10001,10002,10003 через запятую",
        ],
        ["type", "вы", "container или vehicle"],
        [
            "container_or_vehicle_class",
            "вы",
            "Container_Base или ClassName техники",
        ],
        ["give_key", "вы", "yes/no для vehicle → ExpansionCarKey в vehicle_profiles"],
        ["spawn_*", "вы", "только vehicle"],
        ["", "", ""],
        ["Серверы wargm (без Alteria)", "ID", "Карта"],
        ["demo_server_alpha", 10001, "Demo server alpha"],
        ["demo_server_beta", 10002, "Demo server beta"],
        ["demo_server_gamma", 10003, "Demo server gamma"],
    ]:
        ws4.append(row)
    style_sheet(ws4)


def export_to_xlsx(
    offers_path: Path,
    profiles_path: Path | None,
    output_path: Path,
) -> tuple[int, int, int]:
    offers_data = yaml.safe_load(offers_path.read_text(encoding="utf-8"))
    offers_map = offers_data.get("offers") or {}

    profiles: dict[str, Any] = {}
    if profiles_path and profiles_path.is_file():
        prof_data = yaml.safe_load(profiles_path.read_text(encoding="utf-8"))
        profiles = prof_data.get("profiles") or {}

    wb = Workbook()
    ws = wb.active
    ws.title = "offers"
    ws.append(
        [
            "offer_id",
            "name_wargm",
            "delivery_online",
            "shop_server_ids",
            "type",
            "container_or_vehicle_class",
            "give_key",
            "spawn_distance_m",
            "spawn_max_slope_deg",
            "spawn_check_radius_m",
            "spawn_min_clearance_m",
            "notes",
        ]
    )

    ws_items = wb.create_sheet("items")
    ws_items.append(["offer_id", "item_class", "qty", "attachments"])

    def sort_key(k: str) -> int:
        try:
            return int(k)
        except ValueError:
            return 0

    offer_count = 0
    item_rows = 0

    for offer_id_str in sorted(offers_map.keys(), key=sort_key):
        offer = offers_map[offer_id_str]
        if not isinstance(offer, dict):
            continue
        offer_id = int(offer_id_str)
        offer_count += 1
        otype = offer.get("type") or "container"
        name = offer.get("name") or f"Offer {offer_id}"
        server_ids = _format_server_ids(offer.get("shop_server_ids"))

        if otype == "vehicle":
            vehicle_class = offer.get("class") or ""
            give_key = _vehicle_give_key(str(vehicle_class), profiles)
            ws.append(
                [
                    offer_id,
                    name,
                    "yes",
                    server_ids,
                    "vehicle",
                    vehicle_class,
                    give_key,
                    _spawn_cell(offer, "distance_m", "distance_m"),
                    _spawn_cell(offer, "max_slope_deg", "max_slope_deg"),
                    _spawn_cell(offer, "check_radius_m", "check_radius_m"),
                    _spawn_cell(offer, "min_clearance_m", "min_clearance_above_m"),
                    "",
                ]
            )
            continue

        container = offer.get("container") or "SeaChest"
        items = offer.get("items") or []
        notes = ""
        if len(items) > 3:
            notes = f"{len(items)} предметов — лист items"
        ws.append(
            [
                offer_id,
                name,
                "yes",
                server_ids,
                "container",
                container,
                "",
                "",
                "",
                "",
                "",
                notes,
            ]
        )
        for item in items:
            if not isinstance(item, dict):
                continue
            iclass = item.get("class") or item.get("item_class")
            if not iclass:
                continue
            qty = item.get("qty", 1)
            att = _attachments_cell(item.get("attachments"))
            ws_items.append([offer_id, iclass, qty, att])
            item_rows += 1

    ws_vp = wb.create_sheet("vehicle_profiles")
    ws_vp.append(
        ["vehicle_class", "spawn_attachments", "fuel", "coolant", "notes"]
    )
    profile_count = 0
    for vehicle_class in sorted(profiles.keys()):
        prof = profiles[vehicle_class]
        if not isinstance(prof, dict):
            continue
        attachments = prof.get("spawn_attachments") or []
        att_str = ",".join(str(a) for a in attachments)
        fluids = prof.get("fluids") or {}
        fuel = fluids.get("fuel", "")
        coolant = fluids.get("coolant", "")
        notes = ""
        cargo = prof.get("cargo_items") or []
        if any(
            isinstance(c, dict) and c.get("class") == "ExpansionCarKey"
            for c in cargo
        ):
            notes = "ExpansionCarKey в cargo_items"
        ws_vp.append([vehicle_class, att_str, fuel, coolant, notes])
        profile_count += 1

    append_help_sheet(wb)

    for sheet in [ws, ws_items, ws_vp]:
        style_sheet(sheet)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return offer_count, item_rows, profile_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YAML catalog to Excel")
    parser.add_argument(
        "--offers",
        type=Path,
        default=SCRIPT_DIR.parent / "offers.yaml",
        help="Path to offers.yaml",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=SCRIPT_DIR.parent / "vehicle_profiles.yaml",
        help="Path to vehicle_profiles.yaml",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=SCRIPT_DIR / "offers-from-yaml.xlsx",
        help="Output .xlsx path",
    )
    args = parser.parse_args()

    if not args.offers.is_file():
        raise SystemExit(f"offers file not found: {args.offers}")

    profiles_path = args.profiles if args.profiles.is_file() else None
    n_offers, n_items, n_prof = export_to_xlsx(
        args.offers, profiles_path, args.output
    )
    print(
        f"Wrote {args.output} ({n_offers} offers, {n_items} item rows, "
        f"{n_prof} vehicle profiles)"
    )


if __name__ == "__main__":
    main()
