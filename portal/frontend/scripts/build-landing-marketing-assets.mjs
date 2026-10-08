#!/usr/bin/env node
/**
 * PNG (marketing/yandex-direct) -> WebP (public/landing).
 * Preserves aspect ratio; do not use marketing/yandex-direct/optimized/.
 */
import { mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../../..");
const srcDir = path.join(repoRoot, "marketing/yandex-direct");
const outDir = path.join(__dirname, "../public/landing");

const ASSETS = [
  { src: "01-hero-banner-16x9.png", out: "hero-banner.webp", maxW: 1280 },
  { src: "04-steps-4-16x9.png", out: "steps-how.webp", maxW: 1120 },
  { src: "03-before-after-1x1.png", out: "before-after.webp", maxW: 960 },
  { src: "05-pricing-offer-1x1.png", out: "pricing-free-year.webp", maxW: 800 },
  { src: "02-hero-square-1x1.png", out: "og-square.webp", maxW: 1200 },
];

await mkdir(outDir, { recursive: true });

for (const { src, out, maxW } of ASSETS) {
  const input = path.join(srcDir, src);
  const output = path.join(outDir, out);
  if (!existsSync(input)) {
    console.warn(`skip ${out}: missing ${input}`);
    continue;
  }
  const meta = await sharp(input).metadata();
  const result = await sharp(input)
    .resize({ width: maxW, withoutEnlargement: true })
    .webp({ quality: 82 })
    .toFile(output);
  console.log(
    `${out}: ${meta.width}x${meta.height} -> ${result.width}x${result.height} (${Math.round(result.size / 1024)} KB)`,
  );
}

console.log(`Done -> ${outDir}`);
