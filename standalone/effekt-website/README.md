# Effekt portfolio

An image-led portfolio for selected pool, hammam, mosaic, and sauna work.

## Run locally

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

Production validation:

```bash
npm run build
npm run preview
```

## Deploy

The site deploys to Cloudflare Workers as static assets. `wrangler.jsonc` publishes `dist/` and enables the
single-page application fallback; with Workers Builds, use `npm run build` as the build command and
`npx wrangler deploy` as the deploy command. No build variables or custom API token are required.

Regenerate the responsive AVIF/WebP image set after changing project imagery:

```bash
npm run images:optimize
```

## Content and images

- Curated project copy, image groupings, labels, and alt text live in `src/data/projects.ts`.
- English, Azerbaijani, and Russian interface and portfolio copy live in `src/i18n/locales/`.
- The existing `portfolio_assets/` directory is Vite's public directory, so images are served without duplication.
- Generated, metadata-free AVIF and WebP variants live in `portfolio_assets/optimized/`; JPEG originals remain as fallbacks.
- Site photography and visualizations are labeled separately.
- The watermarked third-party sauna image and social/phone screenshots are intentionally excluded.

Project copy is descriptive: it names materials, systems, and visible outcomes, and does not claim client names, dates, or locations.

## Design system

- Basalt `#0B1010`
- Calcite `#E6EDE8`
- Waterline `#1A5B64`
- Mist `#8ECAD0`
- Cedar `#B87B4B`
- Display: Anybody
- Body: Manrope
- Utility labels: JetBrains Mono

The signature element is the “Hydraulic Resonance” introduction: a responsive
water field whose frequencies reveal project-derived outlines as the pointer
moves. Scroll changes the project family, while motion and static fallbacks
respect `prefers-reduced-motion`.
