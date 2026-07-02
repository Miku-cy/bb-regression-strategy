import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { copyFileSync, mkdirSync, readdirSync, existsSync } from 'fs'
import { join } from 'path'

// GitHub Pages 部署: base路径为仓库名
// 本地开发: base为 '/'
const isGithubPages = process.env.GITHUB_PAGES === 'true'

// 复制CSV数据文件到构建输出目录的data/子目录
function copyCsvData() {
  return {
    name: 'copy-csv-data',
    closeBundle() {
      const srcDir = join(__dirname, '..', 'docs', 'data')
      const outDir = join(__dirname, '..', 'docs', 'data')
      // 确保data目录存在（构建后emptyOutDir会清空docs，需要重新复制）
      if (!existsSync(srcDir)) return
      // data目录已经在docs下，不需要额外复制
      // 这个插件保留用于未来扩展
    }
  }
}

export default defineConfig({
  plugins: [react()],
  base: isGithubPages ? '/bb-regression-strategy/' : '/',
  build: {
    outDir: '../docs',
    emptyOutDir: false, // 不清空输出目录，保留data/和.nojekyll
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
