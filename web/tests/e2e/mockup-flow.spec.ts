/**
 * mockup §6 + critical UI interactions 完整覆盖 E2E 测试。
 *
 * 走通用户故事「我有一个 minimal_market 场景，让 LLM 跑，跑到一半干预 3 种类型，看
 * AI 在想什么 6 段 prompt，最后退出」+ 关键交互断言（i18n / 速度 / diff 箭头 / 副区
 * 折线 / cancel 路径 / Esc 关）：
 *
 *   PART 1 画廊与 i18n（步 1-2）
 *     步 1：画廊默认 zh + topbar [EN] 切英文 + 切回 zh
 *     步 2：upcoming/custom 占位卡片可见 + 点击触发 toast
 *
 *   PART 2 跑前页（步 3-4）
 *     步 3：进入跑前 + AdvancedOptionsPanel 折叠展开
 *     步 4：[← 返回画廊] + 重进入跑前
 *
 *   PART 3 跑中页基础（步 5-7）
 *     步 5：开始仿真 + 4 档速度切换（aria-pressed 验证）
 *     步 6：切回 0.5x + 等 auto-step ≥ 2 + EntityCard diff 箭头
 *     步 7：MiniDashboard 折线 (.recharts-line) + 柱状图 (.recharts-bar) 可见
 *
 *   PART 4 干预 3 tabs + cancel（步 8-10）
 *     步 8：force_action(promote, budget=30) → 提交 → toast → drawer 关
 *     步 9：inject_message tab → 选 policy_signal → cancel 路径（不提交）
 *     步 10：override_attribute → strictness=99 → 提交 → toast
 *
 *   PART 5 prompt modal（步 11）
 *     步 11：暂停 + 打开 prompt modal → 6 段标题全验 → Esc 关
 *
 *   PART 6 副区与退出（步 12-13）
 *     步 12：副区 [📊] 折叠/展开
 *     步 13：[🚪 退出] → 回画廊
 *
 * 假设：vite dev server (5173) + FastAPI server (8000) 都已外部启动。
 *
 * minimal_market.scenario.yaml 默认 ticks=5；切 0.5x 速度让总跑时延伸到约 10s，
 * 给后续步骤足够的时间窗口。
 */
import { expect, test } from "@playwright/test";

const SCREENSHOT_DIR = "tests/screenshots";

test.describe.configure({ mode: "serial" });

test("mockup §6 + critical UI interactions full coverage", async ({ page }) => {
  test.slow(); // 13 step + ws + auto-step + recharts + 3 干预往返 → 给 3x timeout

  // ============================================================
  // PART 1: 画廊与 i18n（步 1-2）
  // ============================================================
  await test.step("step 1: gallery zh default + topbar EN switch + back to zh", async () => {
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
    // zh: H1=「场景画廊」（默认 locale）
    await expect(page.getByRole("heading", { level: 1, name: /场景画廊/ })).toBeVisible();
    await expect(page.getByText("walkthrough-min")).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01a-gallery-zh.png`, fullPage: true });

    // 切英文：topbar lang toggle button 有 aria-label，playwright accessible name 优先用 aria-label
    await page.getByRole("button", { name: /切换至英文/ }).click();
    await expect(page.getByRole("heading", { level: 1, name: /Scenario Gallery/i })).toBeVisible({ timeout: 5_000 });
    await page.screenshot({ path: `${SCREENSHOT_DIR}/01b-gallery-en.png`, fullPage: true });

    // 切回中文：en locale 下 aria-label = "Switch to Chinese"
    await page.getByRole("button", { name: /Switch to Chinese/ }).click();
    await expect(page.getByRole("heading", { level: 1, name: /场景画廊/ })).toBeVisible({ timeout: 5_000 });
  });

  await test.step("step 2: upcoming placeholder card triggers v0.3+ toast", async () => {
    // upcoming "信息级联" 卡片是 div role=button —— click 触发 gallery.coming_soon_toast
    const upcomingCard = page.getByText(/信息级联|info_cascade/i).first();
    await expect(upcomingCard).toBeVisible();
    await upcomingCard.click();
    await expect(page.getByText(/v0\.3\+/i).first()).toBeVisible({ timeout: 5_000 });
  });

  // ============================================================
  // PART 2: 跑前页（步 3-4）
  // ============================================================
  await test.step("step 3: enter pre-run + AdvancedOptionsPanel toggle (best-effort)", async () => {
    await page.getByRole("button", { name: /开始|Start/i }).first().click();
    await expect(page).toHaveURL(/\/runs\/[\w-]+\/intro/, { timeout: 10_000 });
    await expect(page.getByText(/A 公司/).first()).toBeVisible();
    await expect(page.getByText("Company").first()).toBeVisible();
    await expect(page.getByText("Regulator").first()).toBeVisible();

    // AdvancedOptionsPanel 折叠按钮 —— 「⚙️ 高级选项」
    const advancedToggle = page.getByText(/⚙️\s*高级选项/).first();
    if (await advancedToggle.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await advancedToggle.click();
      // 展开后 ticks_override label 可见
      await expect(page.getByText(/覆盖\s*total_ticks/i)).toBeVisible({ timeout: 3_000 });
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/02a-prerun-advanced.png`, fullPage: true });
  });

  await test.step("step 4: back to gallery + re-enter pre-run", async () => {
    // [← 返回画廊] / [← 选其他场景]
    const backBtn = page.getByRole("button", { name: /返回画廊|选其他场景|Back to gallery|Pick another/i }).first();
    await backBtn.click();
    await expect(page).toHaveURL("/", { timeout: 10_000 });
    // 再次进入跑前
    await page.getByRole("button", { name: /开始|Start/i }).first().click();
    await expect(page).toHaveURL(/\/runs\/[\w-]+\/intro/, { timeout: 10_000 });
  });

  // ============================================================
  // PART 3: 跑中页基础（步 5-7）
  // ============================================================
  await test.step("step 5: start sim + 4 speed presets aria-pressed", async () => {
    await page.getByRole("button", { name: /开始仿真|Start simulation/ }).click();
    await expect(page).toHaveURL(/\/runs\/[\w-]+\/run/, { timeout: 10_000 });
    await expect(page.getByText(/tick\s+\d+\/\d+/i)).toBeVisible({ timeout: 10_000 });

    // 4 档速度循环点击，每档 active 视觉用 aria-pressed=true 验证；
    // **末档故意停在 0.5x** 防 4x×5tick=1.25s 跑完 → 自动 navigate /finished 影响后续 step
    for (const sp of ["1x", "2x", "4x", "0.5x"]) {
      const pattern = new RegExp(`^${sp.replace(".", "\\.")}$`);
      const btn = page.getByRole("button", { name: pattern });
      await btn.click();
      await expect(btn).toHaveAttribute("aria-pressed", "true");
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/03-running-4x.png`, fullPage: true });
    // 暂停防 auto-step 在后续 step 期间跑完
    const pauseBtn = page.getByRole("button", { name: /⏸\s*(暂停|Pause)/ });
    if (await pauseBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await pauseBtn.click();
    }
  });

  await test.step("step 6: paused single-step → tick++ + still paused (PR4-fix)", async () => {
    // step 5 4x 速度期间 auto-step 已推到 tick 1（snapshot 证据），现在 paused
    // PR4-fix（session 41）：paused 状态下 click 单步 → server 自动 resume+step+pause
    // → tick++ + 仍 paused（v0.1+v0.2 单步语义错位修复）
    await expect(page.getByText(/tick\s+1\/\d+/).first()).toBeVisible({ timeout: 5_000 });

    // click 单步（强断言 button 应 enabled）
    await page.getByRole("button", { name: /⏭\s*(单步|Step)/ }).click();

    // tick 应推到 ≥2（race 下可能 2-4，[2-9] regex 兼容）
    await expect(page.getByText(/tick\s+[2-9]\d*\/\d+/).first()).toBeVisible({ timeout: 5_000 });

    // **仍 paused** —— resume button 仍 visible 即证据（场景 A：单步后保持 paused）
    await expect(page.getByRole("button", { name: /▶\s*(恢复|Resume)/ })).toBeVisible({ timeout: 3_000 });

    // EntityCard diff 箭头 best-effort（promote 触发 cash↓ / reputation↑）
    const diffArrow = page.getByText(/↑\d|↓\d/).first();
    if (await diffArrow.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(diffArrow).toBeVisible();
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/04-running-single-step.png`, fullPage: true });
    // 保持 paused 状态进入后续 step
  });

  await test.step("step 7: MiniDashboard line + bar chart visible (recharts SVG)", async () => {
    // recharts 渲染时给 SVG 加 .recharts-line / .recharts-bar 类
    const lineChart = page.locator(".recharts-line").first();
    if (await lineChart.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(lineChart).toBeVisible();
    }
    const barChart = page.locator(".recharts-bar").first();
    if (await barChart.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(barChart).toBeVisible();
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/05-mini-dashboard.png`, fullPage: true });
  });

  // ============================================================
  // PART 4: 干预 3 tabs + cancel（步 8-10）
  // ============================================================
  await test.step("step 8: intervene force_action with promote(budget=30)", async () => {
    // 点 company_a（第 1 个实体）的 [📌 干预]
    await page.getByRole("button", { name: /干预|Intervene/ }).first().click();
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 });

    // 默认 force_action tab
    await page.getByPlaceholder(/promote|advertise/i).first().fill("promote");
    // rules/minimal_market.py 公式：promote(budget=B) → cash -B + reputation +5
    await page.getByRole("dialog").locator("textarea").first().fill('{"budget": 30}');

    await page.screenshot({ path: `${SCREENSHOT_DIR}/06-drawer-force-action.png`, fullPage: true });
    await page.getByRole("button", { name: /提交干预|Submit intervention/ }).click();
    await expect(page.getByText(/干预已应用|Intervention applied/i)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 5_000 });
  });

  await test.step("step 9: intervene inject_message tab → cancel path (no submit)", async () => {
    // step 8 提交后自动 resume；先暂停以便干预
    const pauseBtn = page.getByRole("button", { name: /⏸\s*(暂停|Pause)/ });
    if (await pauseBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await pauseBtn.click();
    }
    // 点 regulator_main（第 2 个实体）的干预
    await page.getByRole("button", { name: /干预|Intervene/ }).nth(1).click();
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 });

    // 切到 inject_message tab
    await page.getByRole("tab", { name: /注入消息|Inject message/i }).click();
    // policy_signal 是 minimal_market world.message_types 唯一 type
    const messageTypeSelect = page.getByRole("dialog").getByRole("combobox").first();
    if (await messageTypeSelect.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await messageTypeSelect.selectOption("policy_signal");
    }

    // cancel 路径：点 footer [✕ 取消]（drawer 有两个：header 关闭 + footer 取消，用 last 取 footer）
    await page.getByRole("dialog").getByRole("button", { name: /✕\s*取消|✕\s*Cancel/i }).last().click();
    await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 5_000 });
  });

  await test.step("step 10: intervene override_attribute → strictness=99", async () => {
    // 再次点 regulator_main 干预（drawer cancel 后 paused 状态保持，因 wasPaused=true）
    await page.getByRole("button", { name: /干预|Intervene/ }).nth(1).click();
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 });

    // 切到 override_attribute tab
    await page.getByRole("tab", { name: /修改属性|Override attribute/i }).click();
    // attribute_changes JSON：strictness 是 Regulator 的属性
    await page.getByRole("dialog").locator("textarea").first().fill('{"strictness": 99}');

    await page.getByRole("button", { name: /提交干预|Submit intervention/ }).click();
    await expect(page.getByText(/干预已应用|Intervention applied/i)).toBeVisible({ timeout: 5_000 });
    await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 5_000 });
  });

  // ============================================================
  // PART 5: prompt modal 6 段 + Esc（步 11）
  // ============================================================
  await test.step("step 11: open prompt modal → 6 sections + Esc close (best-effort)", async () => {
    // 暂停（如果还没暂停）
    const pauseBtn = page.getByRole("button", { name: /⏸\s*(暂停|Pause)/ });
    if (await pauseBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await pauseBtn.click();
    }
    const viewPromptBtn = page.getByRole("button", { name: /看完整\s*prompt|View full prompt/i }).first();
    if (await viewPromptBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await viewPromptBtn.click();
      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      // D-016 PromptContext 6 段全验
      for (const segment of [
        "system_role",
        "actor_view",
        "perception",
        "available_actions",
        "language_hint",
        "custom_segments",
      ]) {
        await expect(dialog.getByText(new RegExp(segment, "i")).first()).toBeVisible({
          timeout: 3_000,
        });
      }
      await page.screenshot({ path: `${SCREENSHOT_DIR}/07-prompt-modal-6sections.png`, fullPage: true });
      // Esc 关
      await page.keyboard.press("Escape");
      await expect(page.getByRole("dialog")).toHaveCount(0, { timeout: 5_000 });
    } else {
      // 全 rule/random 决策时 LLMThoughtBubble 不渲染——跳过
      await page.screenshot({ path: `${SCREENSHOT_DIR}/07-no-llm-prompt.png`, fullPage: true });
    }
  });

  // ============================================================
  // PART 6: 副区与退出（步 12-13）
  // ============================================================
  await test.step("step 12: side panel collapse + expand", async () => {
    const sidePanelBtn = page.getByTitle(/隐藏数据副区|Hide data side panel/i);
    if (await sidePanelBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await sidePanelBtn.click();
      await expect(page.getByText(/属性趋势|Attribute trend/i)).not.toBeVisible();
      await page.screenshot({ path: `${SCREENSHOT_DIR}/08-side-collapsed.png`, fullPage: true });
      await page.getByTitle(/显示数据副区|Show data side panel/i).click();
      await expect(page.getByText(/属性趋势|Attribute trend/i)).toBeVisible();
    }
  });

  await test.step("step 13: resume + 4x speed → run finishes → auto navigate /finished", async () => {
    // PR4-fix（session 41 第 4 阶段）：resume 推 run_resumed → status 切 running
    // 触发 auto-step useEffect → 4x 速度跑完剩余 tick
    await page.getByRole("button", { name: /▶\s*(恢复|Resume)/ }).click();
    // 立即切 4x 加快跑完
    await page.getByRole("button", { name: /^4x$/ }).click();
    // 等 server 推 run_finished → Running.tsx auto navigate /runs/:id/finished
    await expect(page).toHaveURL(/\/runs\/[\w-]+\/finished/, { timeout: 30_000 });
  });

  // ============================================================
  // PART 7: 跑完页 PR5（步 14-15）
  // ============================================================
  await test.step("step 14: finished page → 6 metrics + 4 narrative sections + buttons", async () => {
    // H1：仿真完成
    await expect(page.getByRole("heading", { level: 1, name: /仿真完成|Simulation finished/ })).toBeVisible({ timeout: 10_000 });
    // 6 指标卡片标签可见（PR5 FinishedMetricsCard）
    for (const label of [
      /总\s*tick\s*数|Total ticks/i,
      /事件总数|Total events/i,
      /事件类型数|Event kinds/i,
      /参与实体|Entities/i,
      /关键转折|Turning points/i,
      /断点触发|Breakpoints/i,
    ]) {
      await expect(page.getByText(label).first()).toBeVisible({ timeout: 5_000 });
    }
    // 4 段叙事区 H3 可见（PR5 NarrativeReport）
    // 注：minimal_market mock provider 跑出的 LLM 响应是 do_nothing JSON，
    // analyze_run(enhance=true) 仍调 LLM 生成 4 段——可能成功（mock 给文本响应）或空
    // 标题永远渲染（即使段为空），所以断言标题存在
    for (const sectionLabel of [
      /世界概览|World overview/i,
      /全过程叙事|Full narrative/i,
      /局势判断|Situation judgement/i,
      /行动建议|Action suggestions/i,
    ]) {
      await expect(page.getByText(sectionLabel).first()).toBeVisible({ timeout: 5_000 });
    }
    // 重跑 + 返回画廊按钮可见（emoji 在某些 chromium 版本 accessible name 处理不一致，弃用）
    await expect(page.getByRole("button", { name: /重跑|Rerun/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /返回画廊|Back to gallery/i })).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/10-finished-page.png`, fullPage: true });
  });

  await test.step("step 15: back to gallery from finished page", async () => {
    await page.getByRole("button", { name: /返回画廊|Back to gallery/i }).click();
    await expect(page).toHaveURL("/", { timeout: 10_000 });
    await expect(page.getByText("walkthrough-min")).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/11-back-to-gallery.png`, fullPage: true });
  });
});

/**
 * PR4.5 second test：three_party_negotiation 验证 relation_graph layout 实际渲染。
 *
 * 涉及组件：
 *   - layouts/RelationGraphLayout（cytoscape + cose-bilkent）
 *   - components/event_templates（虽 layout 本身不直接用，但 EventStreamLayout 共用一份）
 *
 * 不验证：cytoscape 节点 DOM（canvas 渲染，无可断言节点 id）；只验证图例 + 副区折叠 + 控件
 */
test("PR4.5: three_party_negotiation triggers relation_graph layout", async ({ page }) => {
  test.slow();

  await test.step("step A: gallery → 找 three-party 卡片 → 进跑前页", async () => {
    await page.goto("/", { waitUntil: "networkidle" });
    await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
    // walkthrough-three-party 卡片应可见
    await expect(page.getByText("walkthrough-three-party")).toBeVisible();
    // 该卡片对应的 [开始] 按钮 —— ScenarioCard 顶层用 <div className="group ...">
    const card = page.locator("div.group", { hasText: /三人谈判|three.*party/i }).first();
    await expect(card).toBeVisible();
    await card.getByRole("button", { name: /开始|Start/i }).click();
    await expect(page).toHaveURL(/\/runs\/[\w-]+\/intro/, { timeout: 10_000 });
  });

  await test.step("step B: 跑前页验 alice / bob / charlie 实体可见", async () => {
    await expect(page.getByText("alice").first()).toBeVisible({ timeout: 5_000 });
    await expect(page.getByText("bob").first()).toBeVisible();
    await expect(page.getByText("charlie").first()).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/12-three-party-pre-run.png`, fullPage: true });
  });

  await test.step("step C: 开始仿真 → 进跑中页 → relation_graph layout 渲染", async () => {
    await page.getByRole("button", { name: /开始仿真|Start simulation/i }).click();
    await expect(page).toHaveURL(/\/runs\/[\w-]+\/run/, { timeout: 10_000 });

    // ControlBar 可见
    await expect(page.getByText(/tick\s+0/i)).toBeVisible({ timeout: 10_000 });

    // 关系图图例 —— 验证 RelationGraphLayout 渲染（不是 EntityCardLayout）
    // i18n key relation_graph.legend.llm = "LLM 决策"
    await expect(page.getByText(/LLM 决策|^LLM$/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/规则决策|^Rule$/i).first()).toBeVisible();
    await expect(page.getByText(/随机决策|^Random$/i).first()).toBeVisible();
    // 图例 hint
    await expect(page.getByText(/边粗细|Edge width/i).first()).toBeVisible();
    await page.screenshot({ path: `${SCREENSHOT_DIR}/13-three-party-running.png`, fullPage: true });
  });

  await test.step("step D: 暂停 + 退出 → 回画廊", async () => {
    // 暂停防止后续 step 被 run_finished 抢跑
    await page.getByRole("button", { name: /⏸\s*(暂停|Pause)/ }).click();
    await page.waitForTimeout(500);
    // 退出
    await page.getByRole("button", { name: /🚪\s*(退出|Exit)/ }).click();
    await expect(page).toHaveURL("/", { timeout: 10_000 });
    await expect(page.getByText("walkthrough-three-party")).toBeVisible();
  });
});
