import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // Relative base so the build works both under `tqi serve` and at
  // https://jasondyck.github.io/chilliwack-tqi/.
  base: './',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/results.json': 'http://localhost:8080',
      '/api': 'http://localhost:8080',
    },
  },
  // Preview serves the static build with public/results.json, like Pages.
  preview: {
    proxy: {},
  },
})
