# 问题记录

> 本文档按 problem rules 维护：每次解决一个问题后追加一段记录。

---

问题1：用 CodeSee scan-heavy 流程为 Polisim 项目生成 features.json，并把产物放在 .codesee/ 目录下
解决方案：按 .codesee/prompts/scan-heavy.md 四阶段执行——
1. 阶段 1 建索引：读 README / pyproject / 顶层目录 / 路由入口 / 前端路由判定为 heavy 项目，划 10 个 epic（scenario-gallery、run-lifecycle、simulation-control、state-snapshot、intervention、stream-realtime、analysis-report、cli-runtime、server-meta、ui-shell），列出 40 个 feature 骨架
2. 阶段 2 分块深入：按 feature 数从少到多依次处理 server-meta、ui-shell、scenario-gallery、run-lifecycle、simulation-control、state-snapshot、intervention、stream-realtime、analysis-report、cli-runtime 共 10 个 epic；每个 feature 写 4-10 步 step + flow + file refs，错误分支用 kind=error 标注
3. 阶段 3 交叉关系：根据已读代码梳理 41 条 cross_feature 关系（publishes / triggers / depends_on）
4. 阶段 4 自检：写一次性 lint 脚本检查 step 数量越界 / flow 死路 / 孤儿 step / step.name 含代码标识符 / cross_feature 引用 / 路由覆盖，发现 25 处代码标识符 + 10 处 flow 死路，全部回补后再次自检全 0 命中
修改的代码文件：.codesee/features.json（新建）
应当达成的效果：
- 不看代码的人能在画布上理解 Polisim 项目的 40 个用户/业务可感知功能
- 描述的是语义流程（动作链）而非调用链
- 每个 step 至少挂 1 条 file ref，可点击跳转源码
- 错误分支显式标注 kind=error，覆盖 503 / 4xx / 5xx / WebSocket 4004 4500 等真实失败路径
- cross_feature 41 条均有可指明的代码线索（不写模糊关系）
- server 所有 HTTP/WS 路由均被 feature.triggers 覆盖（路由覆盖 lint 0 命中）
用户反馈：途中要求把 features.json 移到 .codesee 目录（之前误建到 codesee/ 与 web/public/），按指令调整完毕

---

问题2：按评审清单自检后重新执行扫描，补上 epic_flow 并修正所有评审问题
解决方案：基于评审反馈完全重写 features.json——
1. 补 PreRun 介绍页 feature（f-pre-run-page）
2. 合并 f-thought-bubble / f-mini-dashboard 为 f-running-page 的 step（不再平级立 feature）
3. 合并三种干预为单个 f-intervene（后端只有一个 endpoint）
4. 所有 ws 广播边标 kind=async；conditional 分支显式标注 condition
5. 所有有外部输入的 feature 补 error 分支（404/400/500/502）
6. cross_feature 补 publishes 关系（6 条，占 18%）
7. confidence 差异化：0.75-0.95 五档分布
8. 新增 epic_flow 8 条描述用户主线
9. role 严格使用 Schema 定义的 11 种（不再用 init/cleanup/logic）
修改的代码文件：.codesee/features.json（覆盖重写）
应当达成的效果：
- 10 epic / 34 feature / 33 cross_feature / 8 epic_flow
- 平均 6.4 步，全部 3-10 范围内
- step.name 标识符检查 0 命中
- flow.kind 全部填写无缺失
- 86 个 file ref 全部存在
- cross_feature 引用全部有效
- publishes 占比 18%（上一版仅 10%）
- confidence 分布：0.75×2 / 0.8×4 / 0.85×7 / 0.9×13 / 0.95×8


---

问题3：用户更新了 prompt（新增 epic.order / epic_flow.note 必填 / 校验脚本），按新版重新执行扫描
解决方案：
1. 项目规模自检：3/5 命中重型 → 走 heavy 流程，但因已读过两轮代码直接基于完整心智模型一次性产出
2. 用 Python 脚本生成完整 features.json（避免长文件 fs_write 截断）
3. 跑 node .codesee/scripts/validate-features.mjs 校验，发现 f-ws-reconnect 闭环，把 reconnect → detect-close 回边改为正常出口（recovered + give-up），避免无入口环
4. 严格模式校验通过 exit 0
修改的代码文件：.codesee/features.json（重写）
应当达成的效果：
- 35 feature / 10 epic / 37 cross_feature / 8 epic_flow
- 所有 epic 含 order 字段（0-5 五层旅程）
- epic_flow 全部带中文 note 而非技术词
- confidence 6 档分布（0.7/0.75/0.8/0.85/0.9/0.95）非扁平
- cross_feature 关系类型多样：triggers 26 + publishes 6 + subscribes 2 + depends_on 3
- publishes+subscribes 占比 22%（接近 30% 推荐线）
- flow 边类型：next 144 + error 38 + conditional 21 + async 17 + loop 6
- 105 个 file ref 全部真实存在
- node 校验脚本严格模式通过


---

问题4：用户更新 prompt（epic.order 语义改为"阶段编号而非 Epic 序号，同阶段共享同一 order"），按新版重跑
解决方案：
1. 对比新旧 prompt：除 epic.order 语义外其他规则未变
2. 现状是 6 个独立阶段（0/1/2/3/4/5）= 接近"全递增"反模式
3. 按用户视角重新归并为 4 阶段：启动准备(0) → 配置(1) → 执行(2) → 分析(3)
4. cli 也归到启动准备阶段（与 web 平行的入口路径）
5. 跑校验严格模式 exit 0
修改的代码文件：.codesee/features.json（仅修改 epics[].order 字段，其他不动）
应当达成的效果：
- 4 阶段分布：order=0 三个(platform/ui-shell/cli)，order=1 两个(scenario-gallery/run-lifecycle)，order=2 四个(simulation-control/realtime-stream/intervention/state-query)，order=3 一个(analysis)
- 同阶段 Epic 共享 order，画布上能横排展开
- 不再是 0,1,2,3,4,5 全递增反模式
- 校验脚本严格模式通过
