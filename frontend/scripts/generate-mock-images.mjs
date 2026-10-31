// Рисует демо-картинки товаров и категорий в public/mock/ по данным src/lib/mock/catalog.json.
// Запуск: npm run mock:images. С реальным бэкендом картинки приходят из media/ Django.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const catalog = JSON.parse(readFileSync(join(root, "src/lib/mock/catalog.json"), "utf8"));
const outProducts = join(root, "public/mock/products");
const outCategories = join(root, "public/mock/categories");
mkdirSync(outProducts, { recursive: true });
mkdirSync(outCategories, { recursive: true });

const BACKGROUNDS = [
  ["#eef2ff", "#e0e7ff"],
  ["#ecfeff", "#cffafe"],
  ["#f0fdf4", "#dcfce7"],
  ["#fff7ed", "#ffedd5"],
  ["#fdf2f8", "#fce7f3"],
  ["#f5f3ff", "#ede9fe"],
  ["#f1f5f9", "#e2e8f0"],
  ["#fefce8", "#fef9c3"],
];
const GLOWS = ["#6366f1", "#06b6d4", "#22c55e", "#f97316", "#ec4899", "#8b5cf6", "#64748b", "#eab308"];

function shade(hex, amount) {
  const n = Number.parseInt(hex.slice(1), 16);
  const mix = (c) => {
    const target = amount < 0 ? 0 : 255;
    return Math.round(c + (target - c) * Math.abs(amount));
  };
  const r = mix(n >> 16);
  const g = mix((n >> 8) & 255);
  const b = mix(n & 255);
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
}

function screen(x, y, w, h, rx) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="url(#screen)"/>
  <clipPath id="clip-${x}-${y}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/></clipPath>
  <g clip-path="url(#clip-${x}-${y})"><circle cx="${x + w * 0.7}" cy="${y + h * 0.3}" r="${Math.max(w, h) * 0.45}" fill="url(#glow)"/></g>`;
}

const DEVICES = {
  phone: (c) => `
  <rect x="270" y="130" width="260" height="540" rx="48" fill="${c}"/>
  ${screen(282, 142, 236, 516, 38)}
  <rect x="362" y="160" width="76" height="22" rx="11" fill="#000"/>`,
  laptop: (c) => `
  <rect x="170" y="190" width="460" height="300" rx="18" fill="${c}"/>
  ${screen(184, 204, 432, 272, 8)}
  <path d="M120 498 H680 L652 540 Q646 550 630 550 H170 Q154 550 148 540 Z" fill="${shade(c, 0.25)}"/>
  <rect x="360" y="498" width="80" height="10" rx="5" fill="${shade(c, -0.2)}"/>`,
  tablet: (c) => `
  <rect x="230" y="150" width="340" height="500" rx="36" fill="${c}"/>
  ${screen(246, 166, 308, 468, 24)}`,
  monitor: (c) => `
  <rect x="130" y="170" width="540" height="330" rx="14" fill="${c}"/>
  ${screen(142, 182, 516, 306, 6)}
  <rect x="378" y="500" width="44" height="88" fill="${shade(c, 0.2)}"/>
  <rect x="290" y="584" width="220" height="22" rx="11" fill="${shade(c, 0.2)}"/>`,
  headphones: (c) => `
  <path d="M252 430 V350 A148 148 0 0 1 548 350 V430" fill="none" stroke="${c}" stroke-width="34" stroke-linecap="round"/>
  <rect x="210" y="380" width="96" height="180" rx="44" fill="${c}"/>
  <rect x="494" y="380" width="96" height="180" rx="44" fill="${c}"/>
  <rect x="292" y="400" width="24" height="140" rx="12" fill="${shade(c, -0.35)}"/>
  <rect x="484" y="400" width="24" height="140" rx="12" fill="${shade(c, -0.35)}"/>`,
  earbuds: (c) => `
  <rect x="280" y="400" width="240" height="200" rx="72" fill="${c}"/>
  <path d="M286 462 H514" stroke="${shade(c, -0.15)}" stroke-width="4"/>
  <circle cx="400" cy="520" r="8" fill="${shade(c, -0.3)}"/>
  <circle cx="335" cy="250" r="50" fill="${c}"/><rect x="322" y="250" width="28" height="120" rx="14" fill="${c}"/>
  <circle cx="335" cy="250" r="22" fill="${shade(c, -0.25)}"/>
  <circle cx="465" cy="250" r="50" fill="${c}"/><rect x="450" y="250" width="28" height="120" rx="14" fill="${c}"/>
  <circle cx="465" cy="250" r="22" fill="${shade(c, -0.25)}"/>`,
  speaker: (c) => `
  <rect x="280" y="160" width="240" height="480" rx="72" fill="${c}"/>
  <circle cx="400" cy="320" r="84" fill="${shade(c, -0.3)}"/><circle cx="400" cy="320" r="40" fill="${shade(c, -0.5)}"/>
  <circle cx="400" cy="510" r="62" fill="${shade(c, -0.3)}"/><circle cx="400" cy="510" r="28" fill="${shade(c, -0.5)}"/>`,
  watch: (c) => `
  <rect x="332" y="100" width="136" height="600" rx="40" fill="${shade(c, -0.25)}"/>
  <rect x="290" y="270" width="220" height="260" rx="62" fill="${c}"/>
  ${screen(306, 286, 188, 228, 48)}
  <rect x="508" y="340" width="16" height="52" rx="6" fill="${c}"/>
  <text x="400" y="418" text-anchor="middle" font-family="Arial, sans-serif" font-size="52" font-weight="700" fill="#fff">10:09</text>`,
  camera: (c) => `
  <rect x="320" y="226" width="170" height="80" rx="18" fill="${c}"/>
  <rect x="160" y="280" width="480" height="290" rx="36" fill="${c}"/>
  <rect x="160" y="280" width="112" height="290" rx="36" fill="${shade(c, 0.12)}"/>
  <rect x="196" y="258" width="54" height="24" rx="8" fill="${shade(c, 0.2)}"/>
  <circle cx="440" cy="425" r="122" fill="${shade(c, 0.15)}"/>
  <circle cx="440" cy="425" r="96" fill="#0b0b0f"/>
  <circle cx="440" cy="425" r="62" fill="url(#lens)"/>
  <circle cx="414" cy="398" r="14" fill="#fff" opacity="0.45"/>`,
  actioncam: (c) => `
  <rect x="240" y="250" width="320" height="300" rx="40" fill="${c}"/>
  <rect x="380" y="290" width="150" height="150" rx="30" fill="#1f2937"/>
  <circle cx="455" cy="365" r="52" fill="url(#lens)"/>
  <circle cx="438" cy="348" r="12" fill="#fff" opacity="0.45"/>
  ${screen(270, 300, 90, 70, 10)}
  <rect x="300" y="236" width="60" height="16" rx="6" fill="#3b82f6"/>`,
  console: (c) => `
  <rect x="318" y="120" width="164" height="540" rx="34" fill="${c}"/>
  <rect x="384" y="120" width="32" height="540" fill="#0f172a" opacity="0.88"/>
  <rect x="288" y="650" width="224" height="26" rx="13" fill="${shade(c, -0.25)}"/>
  <circle cx="400" cy="200" r="8" fill="#60a5fa"/>`,
  gamepad: (c) => `
  <path d="M232 330 Q262 268 332 278 H468 Q538 268 568 330 L640 500 Q660 562 600 572 Q558 578 528 522 L500 472 H300 L272 522 Q242 578 200 572 Q140 562 160 500 Z" fill="${c}"/>
  <rect x="280" y="368" width="64" height="22" rx="5" fill="${shade(c, -0.4)}"/>
  <rect x="301" y="347" width="22" height="64" rx="5" fill="${shade(c, -0.4)}"/>
  <circle cx="500" cy="352" r="13" fill="#22c55e"/><circle cx="528" cy="380" r="13" fill="#ef4444"/>
  <circle cx="472" cy="380" r="13" fill="#3b82f6"/><circle cx="500" cy="408" r="13" fill="#eab308"/>
  <circle cx="352" cy="452" r="32" fill="${shade(c, -0.45)}"/><circle cx="448" cy="452" r="32" fill="${shade(c, -0.45)}"/>`,
};

// Три ракурса: общий вид, под углом, крупный план.
const VIEWS = [
  { rotate: 0, scale: 1, dx: 0, dy: 0 },
  { rotate: -14, scale: 0.9, dx: 0, dy: 10 },
  { rotate: 0, scale: 1.7, dx: 60, dy: 90 },
];

function svg({ kind, color, palette, view = VIEWS[0], label }) {
  const [bg1, bg2] = BACKGROUNDS[palette % BACKGROUNDS.length];
  const glow = GLOWS[palette % GLOWS.length];
  const device = DEVICES[kind](color);
  const transform = `translate(${400 + view.dx} ${400 + view.dy}) rotate(${view.rotate}) scale(${view.scale}) translate(-400 -400)`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-label="${label}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${bg1}"/><stop offset="1" stop-color="${bg2}"/></linearGradient>
    <linearGradient id="screen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#1e293b"/></linearGradient>
    <radialGradient id="glow"><stop offset="0" stop-color="${glow}" stop-opacity="0.85"/><stop offset="1" stop-color="${glow}" stop-opacity="0"/></radialGradient>
    <radialGradient id="lens" cx="0.4" cy="0.35"><stop offset="0" stop-color="#60a5fa"/><stop offset="0.6" stop-color="#1e3a8a"/><stop offset="1" stop-color="#0b1020"/></radialGradient>
    <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18"/></filter>
  </defs>
  <rect width="800" height="800" fill="url(#bg)"/>
  <circle cx="560" cy="230" r="220" fill="#fff" opacity="0.45"/>
  ${view.scale <= 1 ? `<ellipse cx="400" cy="700" rx="220" ry="26" fill="#0f172a" opacity="0.12" filter="url(#soft)"/>` : ""}
  <g transform="${transform}">${device}</g>
</svg>
`;
}

const escape = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

catalog.products.forEach((p, i) => {
  VIEWS.forEach((view, v) => {
    const file = join(outProducts, `${p.slug}-${v + 1}.svg`);
    writeFileSync(file, svg({ kind: p.kind, color: p.color, palette: i, view, label: escape(p.name) }));
  });
});

catalog.categories.forEach((c, i) => {
  const file = join(outCategories, `${c.slug}.svg`);
  writeFileSync(file, svg({ kind: c.kind, color: c.color, palette: i + 3, label: escape(c.name) }));
});

console.log(
  `Готово: ${catalog.products.length * VIEWS.length} картинок товаров, ${catalog.categories.length} категорий.`,
);
