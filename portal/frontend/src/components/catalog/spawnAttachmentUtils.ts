import type { SpawnAttachmentRow } from "@/types/catalog";
import { MAX_SPAWN_EXPANDED } from "@/types/catalog";

export function groupSpawnAttachments(flat: string[]): SpawnAttachmentRow[] {
  const rows: SpawnAttachmentRow[] = [];
  const indexByClass = new Map<string, number>();

  for (const raw of flat) {
    const cls = raw.trim();
    if (!cls) continue;
    const existing = indexByClass.get(cls);
    if (existing !== undefined) {
      rows[existing] = { class: cls, qty: rows[existing].qty + 1 };
    } else {
      indexByClass.set(cls, rows.length);
      rows.push({ class: cls, qty: 1 });
    }
  }
  return rows;
}

export function expandSpawnAttachments(rows: SpawnAttachmentRow[]): string[] {
  const out: string[] = [];
  for (const row of rows) {
    const cls = row.class.trim();
    if (!cls) continue;
    const qty = Math.max(1, Math.floor(Number(row.qty) || 1));
    for (let i = 0; i < qty; i++) out.push(cls);
  }
  return out;
}

export function expandedSpawnCount(rows: SpawnAttachmentRow[]): number {
  return rows.reduce((sum, row) => {
    if (!row.class.trim()) return sum;
    return sum + Math.max(1, Math.floor(Number(row.qty) || 1));
  }, 0);
}

export function spawnOverLimit(rows: SpawnAttachmentRow[], max = MAX_SPAWN_EXPANDED): boolean {
  return expandedSpawnCount(rows) > max;
}
