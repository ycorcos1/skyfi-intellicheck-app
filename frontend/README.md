# SkyFi IntelliCheck Frontend

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```
2. Copy environment variables template and fill in the values provided by the infrastructure team:
   ```bash
   cp .env.local.example .env.local
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Open http://localhost:3000 to view the app.

## Project Structure

- `src/app` – Next.js App Router entry points.
- `src/components` – Reusable UI components.
- `src/styles` – Global design tokens and shared styles.
- `src/lib/config.ts` – Frontend configuration derived from environment variables.

## Design System

- Brand colors, typography, spacing, and shadows are defined in `src/styles/tokens.css`.
- Global reset and base styles are defined in `src/app/globals.css`.
- Fonts are loaded via `next/font` (Bebas Neue, IBM Plex Sans, JetBrains Mono).
- `BaseLayout` constrains content to the 1440px grid and applies page padding.

## Environment Variables

The following variables are required in `.env.local`:

- `NEXT_PUBLIC_COGNITO_REGION`
- `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- `NEXT_PUBLIC_COGNITO_CLIENT_ID`
- `NEXT_PUBLIC_API_URL`

## Scripts

- `npm run dev` – Start the development server.
- `npm run build` – Create an optimized production build.
- `npm run start` – Run the production server.
- `npm run lint` – Run ESLint.
# Frontend deployment trigger
