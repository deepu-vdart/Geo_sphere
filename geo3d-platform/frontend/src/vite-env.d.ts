/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_CESIUM_TOKEN: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// CesiumJS global
declare const CESIUM_BASE_URL: string
