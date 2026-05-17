import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        host: '0.0.0.0',
        port: 5173,
        proxy: {
            // 開發模式下把 /api 轉到 backend（docker-compose 內網直連）
            '/api': {
                target: 'http://backend:8000',
                changeOrigin: true,
            },
        },
    },
});
