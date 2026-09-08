// @trace: REQ-WP-009
/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Where the read API lives. Empty in development, where Vite proxies to it.
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
