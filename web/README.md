# Gadget Panda web (Next.js + Cloudflare)

Site for https://gadgetpanda.app — Products · Store · PandaWorld · Lab · News · Support

Shares D1 database `gadgetpanda-license` with `../license-portal` (lib.gadgetpanda.app).

## Develop

```bash
npm install
npm run db:schema:local
npm run db:seed:local
npm run dev
```

## Deploy

```bash
npm run db:schema
npm run db:seed
npm run deploy
# optional
npx wrangler secret put GEMINI_API_KEY
```

Custom domains: `gadgetpanda.app` and `www.gadgetpanda.app` (see `wrangler.toml`).
