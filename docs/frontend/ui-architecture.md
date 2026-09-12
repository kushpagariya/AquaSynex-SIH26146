# UI Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Design System

- **CSS Framework**: Tailwind CSS
- **Typography**: Inter (Google Fonts) — loaded in Docker build, not at runtime from CDN
- **Color palette**: Slate-based dark mode with risk-level accent colors (red/orange/yellow/green)
- **Icon library**: Heroicons (included in npm package — no CDN)

## 2. Layout

```
┌─────────────────────────────────────────────────────┐
│  HEADER: Logo + Dataset selector + System status    │
├───────────┬─────────────────────────────────────────┤
│           │                                         │
│  SIDEBAR  │           MAIN CONTENT AREA             │
│  - Home   │   (Page-specific content)               │
│  - Datasets│                                        │
│  - Txns   │                                         │
│  - Addr   │                                         │
│  - Graph  │                                         │
│           │                                         │
└───────────┴─────────────────────────────────────────┘
```

## 3. Responsive Behavior

- Desktop-first (investigation tool — not optimized for mobile)
- Sidebar collapses on small screens
- Graph viewer requires minimum 800px width

## 4. Dark Mode

Default: Dark mode. The forensic/investigation context benefits from a dark theme.

Tailwind configuration: `darkMode: 'class'`, defaulting to dark.

## 5. Google Fonts Loading for Offline

Fonts must be **downloaded and self-hosted** in the Vite build to avoid CDN dependency at runtime:

```bash
# During npm install / Docker build
npm install fontsource-inter
```

Then in `main.tsx`:
```typescript
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
```

This ensures fonts are bundled and served from the Docker image without internet access.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Frontend Owner*
