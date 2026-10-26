/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

// frame-ancestors não vale em <meta> (só em header HTTP, que o GitHub Pages não permite configurar), então fica de fora.
// Política de conteúdo: só o próprio site. O painel lê um JSON estático do mesmo
// domínio e não chama APIs em runtime, então connect-src fica em 'self'.
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'none'",
].join('; ');

// A CSP entra só no build de produção: o dev server injeta um preâmbulo inline do React Refresh.
function cspPlugin(): Plugin {
  return {
    name: 'radar-csp',
    apply: 'build',
    transformIndexHtml: {
      order: 'post',
      handler: (html) =>
        html.replace('<head>', `<head>\n    <meta http-equiv="Content-Security-Policy" content="${CSP}" />`),
    },
  };
}

// GitHub Pages serve em /<repo>/; em dev e preview a base é "/".
export default defineConfig({
  base: process.env.VITE_BASE ?? '/',
  plugins: [react(), tailwindcss(), cspPlugin()],
  server: { port: 5173, strictPort: false },
  build: { target: 'es2022', sourcemap: false, chunkSizeWarningLimit: 900 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
