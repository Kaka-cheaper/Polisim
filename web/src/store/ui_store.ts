/**
 * uiStore —— 客户端 UI 状态（zustand + persist）。
 *
 * 字段定义见 mockup §11.8：
 *   - speed:               tick 间渲染延迟档位（§4.4.1 控制条）
 *   - sidePanelCollapsed:  副区折叠态（§4.4.2 MiniDashboard）
 *   - locale:              i18n 语言（§5.3）
 *   - prevSnapshotByRunId: EntityCard diff 计算用（§10.7 #41）
 *
 * 持久化策略：
 *   - **持久化** speed / sidePanelCollapsed / locale —— 跨 session 保留用户偏好
 *   - **非持久化** prevSnapshotByRunId —— Map 类型不可 JSON.stringify；且按 run 自然失效
 *     （新 run 开始时是空，跑中由 hooks 累积；session 重启从空开始合理）
 *
 * 单一真理纪律：
 *   - i18n 当前语言以本 store.locale 为准；i18n 启动后由 App 的 useEffect 同步
 *   - 业务组件直接 useUiStore selector，不要复制 state 到 props 链
 */
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type Speed = 0.5 | 1 | 2 | 4;
export type Locale = "zh" | "en";

// PR1 阶段 Snapshot 类型尚未从 server openapi 生成（types.gen.ts 由 PR2 落地）
// 用 unknown 占位，PR2+ 改 import { Snapshot } from "../api/types.gen"
type SnapshotShape = unknown;

interface UiStore {
  speed: Speed;
  sidePanelCollapsed: boolean;
  locale: Locale;
  prevSnapshotByRunId: Map<string, SnapshotShape>;
  setSpeed: (speed: Speed) => void;
  toggleSidePanel: () => void;
  setSidePanelCollapsed: (collapsed: boolean) => void;
  setLocale: (locale: Locale) => void;
  setPrevSnapshot: (runId: string, snapshot: SnapshotShape) => void;
  clearPrevSnapshot: (runId: string) => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      speed: 1,
      sidePanelCollapsed: false,
      locale: "zh",
      prevSnapshotByRunId: new Map<string, SnapshotShape>(),
      setSpeed: (speed) => set({ speed }),
      toggleSidePanel: () =>
        set((state) => ({ sidePanelCollapsed: !state.sidePanelCollapsed })),
      setSidePanelCollapsed: (sidePanelCollapsed) => set({ sidePanelCollapsed }),
      setLocale: (locale) => set({ locale }),
      setPrevSnapshot: (runId, snapshot) =>
        set((state) => {
          const next = new Map(state.prevSnapshotByRunId);
          next.set(runId, snapshot);
          return { prevSnapshotByRunId: next };
        }),
      clearPrevSnapshot: (runId) =>
        set((state) => {
          const next = new Map(state.prevSnapshotByRunId);
          next.delete(runId);
          return { prevSnapshotByRunId: next };
        }),
    }),
    {
      name: "polisim:ui-store",
      storage: createJSONStorage(() => localStorage),
      // 仅持久化 3 项基础偏好；prevSnapshotByRunId（Map）排除
      partialize: (state) => ({
        speed: state.speed,
        sidePanelCollapsed: state.sidePanelCollapsed,
        locale: state.locale,
      }),
    },
  ),
);
