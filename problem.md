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
