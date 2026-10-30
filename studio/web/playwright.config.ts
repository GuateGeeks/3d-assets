import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'tests/browser',use:{baseURL:'http://127.0.0.1:5287',headless:true,launchOptions:{args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-webgl']}},webServer:{command:'npm run dev -- --port 5287 --strictPort',url:'http://127.0.0.1:5287',reuseExistingServer:true},reporter:'list'});
