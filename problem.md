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
