# LLM辅助建模方案

## 一、为什么需要这层

按照当前架构，用户如果要真正使用 `Polisim`，至少要理解并编写：

1. `World Definition`
2. `Scenario`
3. `Rules`

这对普通用户来说门槛很高，尤其是：

1. 世界定义中的实体、动作、消息、环境变量如何抽象
2. 场景实例中的初始状态和事件如何组织
3. 规则层中的前置条件、效果、冲突处理如何表达

因此，系统不能只提供“手写配置”的方式，还应提供一层：

**LLM 辅助建模层**

它的作用不是绕过现有分层，而是帮助用户用自然语言逐步生成并修正：

1. `World Definition`
2. `Scenario`
3. `Rules`

## 二、这层的定位

这不是一个新的运行层，也不是一个新的规则层。

它更像一个：

**建模助手 / 配置作者助手 / 场景编写助手**

它应该位于用户输入和结构化配置之间：

```text
用户自然语言描述
    ↓
LLM 辅助建模层
    ↓
World Definition / Scenario / Rules 草案
    ↓
校验与修复
    ↓
用户确认
    ↓
Runtime 运行
```

## 三、它不应该做什么

为了保持现有架构可控，这一层不应：

1. 直接替代 Runtime
2. 让用户一句话直接黑箱跑仿真
3. 绕过 `World Definition / Scenario / Rules`
4. 直接修改运行中的状态真相

也就是说：

**LLM 辅助建模层只负责帮助用户“写配置”，不负责替代引擎本身。**

## 四、推荐的交互流程

第一版建议采用“逐步引导”而不是“一次性生成”。

### 第一步：明确目标

先问用户：

1. 你想模拟什么系统
2. 你最想回答什么问题
3. 结果最终要用来做什么

这一阶段的目标是确定：

1. 世界边界
2. 主要实体
3. 仿真目标

### 第二步：生成世界定义草案

基于用户描述，LLM 先提出：

1. 可能的实体类型
2. 关键属性
3. 关键关系
4. 候选动作
5. 候选消息类型
6. 环境变量

这一阶段产出的是：

**World Definition 草案**

### 第三步：生成场景实例草案

再根据用户提供的具体场景，补：

1. 实体实例
2. 初始属性值
3. 初始关系
4. 环境初始值
5. 预设事件
6. 轮次与暂停配置

这一阶段产出的是：

**Scenario 草案**

### 第四步：生成规则草案

这是最难的一层。

LLM 应帮助用户逐步明确：

1. 动作前置条件
2. 动作效果解释
3. 冲突如何处理
4. 哪些状态变化要受约束

这一阶段产出的是：

**Rules 草案**

### 第五步：校验与修复

系统对三层草案进行：

1. 结构校验
2. 引用关系校验
3. 字段完整性校验
4. 明显矛盾修复建议

#### 5.1 复用现有验证模块（session 21 决策——不重写）

session 1-21 已经搭好的验证链路**直接复用**，不再造轮子：

| 校验层 | 现有产出 | 反馈给 LLM 的内容 |
|---|---|---|
| 结构（schema） | `schemas/*.json` + Pydantic `extra="forbid"` | 字段缺失 / 类型错 / 枚举非法 |
| 跨字段 | `model_validator`（如 `LLMConfig._default_provider_must_exist`） | 字段间矛盾 |
| 跨文件 | `core/scenario_loader._validate_cross_references` | 跨 World/Scenario 引用未声明 |
| 业务规则 | `BaseRules.validate_action`（动作前置条件） | 业务前置违反 |
| 错误体系 | `core/errors.SimEngineError` 子类树 | 精确分类捕获，不模糊 |

加载入口（`load_world_definition` / `load_scenario`）抛出的 `SimEngineError`
本身就是结构化错误信息，把它序化为 prompt 反馈即可。

#### 5.2 自我修复循环（Generator-Validator Loop）

循环形态：

```python
def llm_assisted_modeling_loop(
    user_brief: str,
    provider: LLMProvider,
    *,
    max_attempts: int = 3,
) -> WorldDefinition:
    """LLM 引导建模——生成 → 校验 → 反馈 → 重试。"""
    feedback: str | None = None  # 第一轮无反馈
    for attempt in range(max_attempts):
        prompt = _build_modeling_prompt(
            user_brief, prior_feedback=feedback
        )
        raw_yaml = provider.generate(
            prompt, system_prompt=_MODELING_SYSTEM_PROMPT
        )
        try:
            world = load_world_definition_from_str(raw_yaml)
            return world  # 校验通过
        except SimEngineError as exc:
            # 把结构化错误序化成 LLM 可消费的反馈
            feedback = _format_error_for_llm(exc, raw_yaml)
            # 下一轮 prompt 会附 "上次你写的是 X，错了，因为 Y，请修复"
    raise ModelingFailedError(
        f"LLM 经过 {max_attempts} 次仍未产出合法 world definition；"
        f"最后一次错误：{feedback}"
    )
```

关键设计点：

1. **校验器 = 现有 loader**——抛 `SimEngineError`，错误信息已结构化，无须重写
2. **错误反馈格式必须明确**——指出"哪里错了 / 为什么 / 期望什么"。例：
   ``"relations[0].type 'trust' 未在 world 声明；可用关系类型：[]"``
3. **max_attempts + 兜底**——避免死循环。LLM 真无法收敛时把控制权交回用户，让其手动修或换 prompt
4. **prior_feedback 累积**——每次重试 prompt 附上一次错误，而不是从零开始

#### 5.3 已知陷阱（落地前必须想清楚）

##### 陷阱 1：校验通过 ≠ 语义正确

`docs/03-implementation/pitfalls.md` 已记的 P1 案例：`world.defaults.fallback_action`
schema 校验全过，但运行到第 N tick 才炸（指向 rules 不认的动作）。

**含义**：自我修复循环只能保证 schema 通过；**跨层语义校验**（如 fallback_action
必须能被 rules.resolve_effects 处理）当前是空白。LLM 辅助建模落地前**必须**
先扩展跨层语义校验——见 D-013 待决策。

##### 陷阱 2："DSL" 在 Polisim 语境里到底是什么

可能的两种语义：

- **A. YAML + JSON Schema + Pydantic**（当前形式）——校验链路已完整
- **B. 更高层的自然语言友好抽象**（如 `"Alice 信任 Bob 50 分"`）——需新 parser
  把 DSL 翻译为 YAML

**建议默认 A**——LLM 直接生成 YAML 比生成自创 DSL 风险低，OpenAI 的 JSON 模式
+ `response_format` 可直接用 schema 约束输出。是否需要 B 见 D-012 待决策。

##### 陷阱 3：可视化与生成是两件事

可视化是**展示层**——把 YAML 渲染为图（实体关系图 / 动作流图），用 Cytoscape.js
/ Mermaid 等成熟库，不属于"验证模块"。两条独立工作流：

```text
LLM 生成 + 校验循环  →  产出合法 YAML
                      ↓
                   可视化渲染层（独立组件）
                      ↓
                   用户审阅 / 修正
```

##### 陷阱 4：引导问题不能太复杂

第一版的安全做法是 **问答 = 字段填空**——一个问题对齐 World Definition 的一个
字段族，避免开放式"你想做什么仿真"。例：

| 引导问题 | 提取的字段 |
|---|---|
| "你的世界叫什么名字？描述一句话。" | `world.name` / `world.description` |
| "有哪几类参与者？" | `entity_types[*].name` |
| "他们能做什么动作？" | `action_types` |
| "动作产生什么后果？" | rules 草案（业务公式） |

每个问题 1-3 句答案，LLM 直接转为结构化字段。这样**问题数量上限可控**
（与 World Definition 字段数同阶），不会发散。

#### 5.4 落地前提（v1 不做，但锁定方向）

按 `AGENTS.md` 4.2，第一版**不**做自动建模。但本节方向已锁定，未来真要做时：

1. ~~先解决 D-013（语义级跨层校验）~~ ✅ **已落地 session 22**——`core/semantic_validator.py` + `SemanticValidationError(SimEngineError)` + `BaseRules.actions_handled()` 钩子。校验器已就位，自我修复循环可消费结构化错误（`SemanticIssue` 三元组）
2. 决策 D-012（DSL 形式）——倾向 A 方案（YAML + 现有 schema）
3. 实现 `core/modeling_loop.py`（暂未存在）——`llm_assisted_modeling_loop` 单点入口
4. 引导问答前端独立——不污染 `core/` 编排层

**关键观察**：D-013 落地后，本节 5.2 伪代码中的 `load_world_definition_from_str` 校验链路实质上已经具备**完整能力**——`load_*` 抛 schema/loader 错 + 后续 `validate_semantics` 抛跨层错；二者统一继承 `SimEngineError`，错误反馈格式器一律按 `exc.issues`（如有）+ `str(exc)` 渲染即可。这意味着 LLM 辅助建模的"自我修复循环"骨架现在**只缺生成端**——modeling_loop.py 落地时直接复用已有校验链路，无需再造任何校验逻辑。

### 第六步：用户确认

只有在用户确认后，配置才进入可运行状态。

## 五、建议的产品形态

第一版更适合做成：

1. **多轮问答式引导器**
2. 每一步生成结构化草案
3. 用户可以修改、接受、退回

而不是：

1. 完全自动黑箱生成
2. 一次性吐出超长 YAML

## 六、哪些能力应该直接复用现成轮子

这一层不应该从零开始手搓所有底层能力。

### 6.1 结构化配置校验

#### 应复用什么能力

1. schema 定义
2. schema 校验
3. schema 文档化
4. 结构化错误提示

#### 建议复用

**JSON Schema**

文档：
- https://json-schema.org/

建议用途：
1. 作为 `World Definition` / `Scenario` 的结构定义标准
2. 作为配置校验基础

**Pydantic**

文档：
- https://docs.pydantic.dev/

建议用途：
1. 作为 Python 侧运行时校验模型
2. 生成更友好的错误信息

#### 结论

这部分**不要自研**。

### 6.2 结构化生成与修复

#### 应复用什么能力

1. 让 LLM 输出结构化对象
2. 输出不合法时自动修复
3. 结构与 UI/editor 共用同一份 schema

#### 建议复用

**llm-schema**

GitHub：
- https://github.com/shenli/llm-schema

建议关注的能力：
1. `schema.toPrompt()`：从 schema 自动生成 prompt 约束
2. `schema.toOpenAITool()`：从 schema 自动生成工具 schema
3. `schema.safeParse()`：结构化校验
4. `SchemaEditor`：同一份 schema 生成编辑器

这套思路非常适合拿来做：

**“World Definition / Scenario / Rules 草案 + 人工修订界面”**

**Outlines**

GitHub：
- https://github.com/dottxt-ai/outlines

建议关注的能力：
1. 结构化输出约束
2. JSON/Pydantic 兼容生成
3. grammar/regex 级约束生成

它适合用在：

**让 LLM 稳定输出符合 schema 的对象，而不是自由文本。**

**Jsonformer**

GitHub：
- https://github.com/1rgs/jsonformer

建议关注的能力：
1. 让模型按 JSON 结构生成输出
2. 降低格式错误概率

#### 结论

这一层也**不建议从零自研结构化生成底座**。

### 6.3 场景/世界的自然语言生成思路

#### 应复用什么能力

1. 自然语言到结构化世界草案
2. 多轮场景构建
3. 分阶段生成，而不是一次性生成

#### 可参考项目

**SceneSmith**

GitHub：
- https://github.com/nepfaff/scenesmith

项目主页：
- https://scenesmith.github.io/

建议关注的思想：
1. 不是一次性生成，而是分阶段 agentic generation
2. 先生成上层结构，再逐步细化
3. 生成结果要可直接进入 simulation-ready 状态

这和 `Polisim` 的建模助手非常像：

**先定结构，再补细节，再生成可运行配置。**

**NVIDIA Isaac Sim Chat IRO**

官方文档入口：
- https://docs.isaacsim.omniverse.nvidia.com/

建议关注的思想：
1. 让用户用自然语言描述场景
2. 再生成结构化仿真输入
3. 再进入运行系统

虽然它不是开源的通用建模框架，但它说明：

**自然语言 → 结构化仿真配置** 这条产品路径是成立的。

**Gazebo World Generator**

项目页：
- https://github.com/search?q=Gazebo+World+Generator&type=repositories

建议关注的思想：
1. 从自然语言生成世界配置
2. 关注可执行、可落地的世界结果，而不是只生成文字描述

#### 结论

这些项目不能直接拿来用，但它们的**生成思路、分阶段构建方式、从文本到可执行配置的路径**值得复用。

### 6.4 规则辅助建模

#### 应复用什么能力

1. 从自然语言提取形式化规则
2. 多步 formalization
3. 规则草案 + 校验 + 修正

#### 可参考项目

**L2P (LLM-driven Planning Model Library Kit)**

GitHub：
- https://github.com/AI-Planning/l2p

PyPI：
- https://pypi.org/project/l2p/

建议关注的能力：
1. 从自然语言抽取 planning domain / task
2. 把自然语言约束逐步 formalize
3. 在形式化后再交给 planner/solver

这对 `Polisim` 的启发不是“直接上 PDDL”，而是：

**规则层也应该通过多阶段 formalization 生成，而不是一次性生成整套规则。**

**NL2Plan**

GitHub：
- https://github.com/mrlab-ai/NL2Plan

建议关注的思想：
1. 用多步流程把自然语言转换成形式化 domain/problem
2. 中间每一步都可检查、修正、反馈

#### 结论

`Rules` 这层最不适合“一步到位生成”，更适合借鉴这些项目的**多阶段建模流程**。

### 6.5 多 agent / 工作流编排

#### 应复用什么能力

1. 多轮状态工作流
2. 人工确认节点
3. 持久状态流转

#### 可参考项目

**LangGraph**

GitHub：
- https://github.com/langchain-ai/langgraph

文档：
- https://docs.langchain.com/oss/python/langgraph/overview

建议关注的能力：
1. human-in-the-loop
2. durable execution
3. 有状态工作流图

它适合用在：

**建模助手工作流本身**，例如“提问 → 生成草案 → 校验 → 修复 → 用户确认”。

**AutoGen**

GitHub：
- https://github.com/microsoft/autogen

文档：
- https://microsoft.github.io/autogen/

建议关注的能力：
1. 多 agent 协作模式
2. agent tool / multi-step authoring 流程

注意：

AutoGen 现在已进入 maintenance mode，更适合作为参考，不适合直接作为未来主依赖。

#### 结论

这层可以复用“工作流和 agent 协作思路”，但不应替代 `Polisim` 的仿真运行内核。

## 七、哪些东西必须自己做

下面这些内容没有现成成熟产品能直接替你做好：

1. 面向 `Polisim` 的三层配置语义
2. `World Definition / Scenario / Rules` 之间的映射逻辑
3. 生成后如何和 `Runtime / Event Log / Analysis` 联动
4. 针对你的系统的“配置修复逻辑”
5. 面向推演引擎的“用户引导流程”

也就是说：

**底层共性件可以复用，但 Polisim 自己的建模工作流必须自己做。**

## 八、第一版最推荐的技术路径

第一版不要一口气做成“全自动建模 AI”。

最稳的路径是：

1. 先做多轮引导式建模
2. 每一步都生成结构化草案
3. 用 JSON Schema / Pydantic 校验
4. 用结构化生成工具保证输出合法
5. 允许用户人工确认和修正

也就是说：

**先做“LLM 辅助建模”，不要一开始就做“全自动黑箱建模”。**

## 九、最终结论

你这个想法是对的，而且是必要的。

但它不应该被理解为：

**“再做一个新的万能 AI 配置系统。”**

更准确的理解是：

**在现有 Polisim 分层架构之上，增加一个面向用户的 LLM 建模助手层。**

这个助手层：

1. 自己负责引导流程和领域映射
2. 复用现成的 schema、结构化生成、工作流和形式化建模轮子
3. 最终仍然产出 `World Definition / Scenario / Rules`，而不是绕过它们
