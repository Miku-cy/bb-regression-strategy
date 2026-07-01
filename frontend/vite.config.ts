import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages 部署: base路径为仓库名
// 本地开发: base为 '/'
const isGithubPages = process.env.GITHUB_PAGES === 'true'

export default defineConfig({
  plugins: [react()],
  base: isGithubPages ? '/bb-regression-strategy/' : '/',
  build: {
    outDir: '../docs',
    emptyOutDir: true,
    assetsDir: 'assets',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
