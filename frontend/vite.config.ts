import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// 手机版 BrowserRouter 路由列表（刷新时需要 fallback 到 index.html）
const MOBILE_ROUTES = [
  '/search/flights', '/search/trains', '/search/hotels',
  '/search/pois', '/search/foods', '/search/transport',
  '/plan', '/trips', '/settings',
]

export default defineConfig({
  plugins: [
    react(),
    // 自定义 SPA fallback：只对手机版路由回退到 index.html，PC 版 /pc.html 不受影响
    {
      name: 'spa-fallback',
      configureServer(server) {
        server.middlewares.use((req, _res, next) => {
          const url = req.url || ''
          // /pc.html 永不 fallback
          if (url === '/pc.html' || url.startsWith('/pc.html?')) return next()
          // 手机版已知路由 → fallback 到 index.html
          const clean = url.split('?')[0]
          if (MOBILE_ROUTES.includes(clean) || MOBILE_ROUTES.some(r => clean.startsWith(r + '/'))) {
            req.url = '/index.html'
          }
          next()
        })
      },
    },
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
        pc: path.resolve(__dirname, 'pc.html'),
      },
    },
  },
})
