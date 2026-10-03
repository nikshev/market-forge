// @trace: REQ-WP-009
/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Where the read API lives. Empty in development, where Vite proxies to it.
  readonly VITE_API_BASE?: string;
  // A signed Telegram launch for development, written by `npm run dev:init` to
  // `.env.development.local`. Read only when `import.meta.env.DEV` (REQ-WP-080).
  readonly VITE_DEV_INITDATA?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
