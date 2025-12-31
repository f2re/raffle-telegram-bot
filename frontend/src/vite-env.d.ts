/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_BOT_USERNAME: string
  readonly VITE_TON_WALLET_ADDRESS: string
  readonly VITE_TON_CONNECT_MANIFEST_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Buffer polyfill for TON libraries
interface Window {
  Buffer: typeof import('buffer').Buffer
}
