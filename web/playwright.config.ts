/**
 * Playwright 配置（mockup §6 全流程 E2E 测试）。
 *
 * 设计：
 *   - 假定 dev server（vite 5173）和 backend（FastAPI 8000）已外部启动
 *     —— 不用 webServer 自动起，避免覆盖已经在跑的 dev 进程
 *   - 单 worker 串行 —— 多 worker 并发会污染 server runtime registry
 *   - 失败时存截图 + trace + video，方便 debug
 *   - 仅 chromium 一个项目 —— 节约下载时间；如需多浏览器后续加
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  outputDir: "test-results/",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  expect: {
    timeout: 8_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
});
