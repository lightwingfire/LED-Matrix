import { defineConfig } from 'vite';

export default defineConfig({
  base: '/static/ui/',
  build: {
    outDir: 'static/ui',
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: 'frontend/main.jsx',
      output: { entryFileNames: 'app.js', assetFileNames: 'app.[ext]' },
    },
  },
  esbuild: { jsx: 'automatic' },
});
