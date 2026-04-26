# D-016：Prompt 上下文规范化

> **状态**：草案（2026-04-26 session 23 起草，简版）→ 待评审  
> **关联决策**：D-014（参数强 schema，**前置依赖**）；D-015（effect 扩充，并行）  
> **预计实施 session**：v0.1.1 末期（D-014 + D-015 实施完成后，3-4 个 session）

---

## 一、决策背景（Why）

### 1.1 现状评估

`core/llm_policy.py:build_prompt` 已经是结构化输出（JSON dump 而非自由文本），**比想象中好**。但 4 类关键信息缺失：

| 缺失 | 后果 | 例证 |
|---|---|---|
| ❌ actor 关系视图 | LLM 看不到自己与他人的 trust / debt 等关系 | 三人谈判场景：alice 不知与 bob/charlie 的当前 trust 值 |
| ❌ actor 决策历史 | LLM 每 tick "失忆"，行为不连贯 | minimal_market：company_a 上 tick promote 失败，本 tick 仍执意再 promote |
| ❌ entity 角色提示 | LLM 不知扮演的角色语义 | charlie 不知"我是被动谈判者，应保守接受高 offer" |
| ❌ rules 模块定制 prompt | 场景特化提示无处可注 | 谈判场景想加"你的目标是把 trust 拉到 80"无 API |

### 1.2 v0.2 前端紧迫性 🔴 关键

v0.2 前端的 **"LLM 决策实时面板"** 需要：
- 拆分 prompt 各段（system_role / actor_view / perception / available_actions / language_hint），每段独立可视化
- 实时显示 LLM 流式回复
- 让用户能在 UI 上看到"prompt 喂了什么 → LLM 回复了什么 → 解析后是什么 action"

如果 prompt 仍是一坨 JSON dump，前端只能展示 raw text——失去**核心独家价值**（让用户理解 LLM 决策过程）。

---

## 二、决策内容（What）

### 2.1 引入 PromptContext 数据类

```python
@dataclass(frozen=True)
class PromptContext:
    """LLM 决策 prompt 的结构化容器（D-016）。

    每段独立可序列化，前端可分别渲染。最终通过 `render()` 拼成 str
    供 LLMProvider.generate 消费——保持向后兼容。
    """

    # ── A. 角色与身份 ──
    system_role: str | None
    """例如 "You are entity 'company_a' of type 'company'"。
    rules 模块可在 enrich_prompt 中替换为更场景化的角色描述。"""

    # ── B. Actor 自身视图（D-016 新增的关系 + 历史）──
    actor_view: dict
    """{
        'id': str, 'type': str, 'description': str | None,
        'attributes': dict[str, Any],
        'relations': {
            'outgoing': [{'type': str, 'to': str, 'value': float | None}, ...],
            'incoming': [{'type': str, 'from': str, 'value': float | None}, ...]
        },
        'recent_decisions': [
            {'tick': int, 'action': str, 'params': dict, 'reason': str | None}, ...
        ]  # 最近 N 项（默认 3，可配）
    }"""

    # ── C. 外部感知 ──
    perception: dict
    """{
        'inbox': [...],  # 现有
        'environment': {...},  # 现有
        'tick': int, 'remaining_ticks': int  # 现有
    }"""

    # ── D. 可用动作（含 D-014 完整 ParamSchema）──
    available_actions: list[dict]
    """每项含 name / description / params 完整 schema（含 D-014 的 default/min/max/values 等）"""

    # ── E. 语言指令 ──
    language_hint: str
    """如 "Respond natural-language fields in zh-CN" """

    # ── F. 场景特化段（rules.enrich_prompt 注入）──
    custom_segments: dict[str, str]
    """rules 模块通过 `enrich_prompt(ctx) -> ctx.with_segments({...})` 注入。
    例如 {'objective': 'Reach trust=80 with at least one other party'}"""

    def render(self) -> str:
        """拼为最终 prompt str，供 LLMProvider.generate 消费。
        实现：JSON dump 主体 + custom_segments 字符串拼接 + language_hint。"""
```

### 2.2 EventLog 同步记录结构化版本

`decision_proposed` 事件加新字段 `prompt_context`（嵌入完整 PromptContext 序列化），不再只存 raw_reasoning_summary。

前端从 EventLog 即可拿到完整 prompt 拆段视图。

### 2.3 Rules 模块新增 `enrich_prompt` 钩子

```python
class BaseRules:
    def enrich_prompt(self, ctx: PromptContext, world, scenario, state, entity_id, tick) -> PromptContext:
        """场景特化 prompt 段注入。默认实现：返回原 ctx 不动。

        子类可：
        - 替换 system_role 加场景人设
        - 在 custom_segments 加目标 / 约束 / 历史叙事提示
        - 修改 language_hint
        - **不应**修改 actor_view / perception / available_actions（这些是引擎事实）
        """
        return ctx
```

### 2.4 修订后的决策流程

```text
build_prompt(world, scenario, state, entity_id, tick):
  1. 按 D-016 结构组装 base PromptContext
  2. ctx = rules.enrich_prompt(ctx, world, scenario, state, entity_id, tick)
  3. prompt_str = ctx.render()
  4. raw = provider.generate(prompt_str, ...)
  5. parsed = parse_response(raw, allowed_actions)
  6. EventLog.append(decision_proposed, prompt_context=ctx, raw_response=raw, parsed=parsed)
```

---

## 三、影响面（Where）

| 文件 | 改动性质 |
|---|---|
| `core/llm_policy.py` | 新增 PromptContext 类；重构 build_prompt 为多段式；render 方法 |
| `core/events.py` | EventKind `decision_proposed` payload 加 prompt_context 字段 |
| `models/runtime_models.py` | EventKind / Event payload 同步 |
| `rules/base.py` | 加 `enrich_prompt` 钩子（默认 no-op） |
| `rules/minimal_market.py` | 可选：添加场景人设（"You are a competitor in a 2-company market"） |
| `rules/three_party_negotiation.py` | 可选：添加目标提示（"Reach trust=80 with anyone"） |
| `core/runtime.py` | 调用链小调整：`_decide_via_llm` 改为 `llm_policy.decide` 处理整个 PromptContext 流程 |
| `tests/test_llm_policy.py` | 重写——验证 PromptContext 各段构造 + render + enrich_prompt 钩子 |
| `tests/test_events.py` | 验证 prompt_context 进入事件日志 |

**总工程量**：5-6 天（2-3 个 session）。

---

## 四、迁移路径（How）

### 4.1 实施顺序

1. **第一步**：定义 PromptContext 类 + 基础 render（无 actor.relations / actor.recent_decisions——先骨架）
2. **第二步**：把现有 build_prompt 拆成新结构，输出与原版语义等价（向后兼容验证）
3. **第三步**：补 actor_view.relations 字段（需 Runtime 提供 `state.get_actor_relations(entity_id)`）
4. **第四步**：补 actor_view.recent_decisions 字段（需 EventLog 提供 `get_recent_decisions_by_actor(entity_id, n)`）
5. **第五步**：加 enrich_prompt 钩子 + 两个产线场景实施钩子
6. **第六步**：EventLog 持久化 prompt_context
7. **第七步**：更新所有相关测试
8. **第八步**：跑全量测试 + smoke OpenAI 验证（关键！）

### 4.2 向后兼容性

✅ **运行时完全兼容**——render() 输出仍是 str，LLMProvider.generate 不变。

🟡 **Event Log schema 微变**——`decision_proposed` 加 `prompt_context` 字段（旧 run 无此字段；前端按 optional 处理）。

🟡 **OpenAI 协议层无变化**——provider 仍只看 prompt str。

---

## 五、测试设计

| 测试主题 | 数量估计 |
|---|---|
| PromptContext 各字段构造正确 | 5 |
| render() 输出与原 build_prompt 语义等价（向后兼容回归） | 3 |
| actor_view.relations 包含 outgoing + incoming | 2 |
| actor_view.recent_decisions 含最近 N 项 | 2 |
| enrich_prompt 钩子被调用 + 注入 custom_segments | 3 |
| EventLog `decision_proposed` 含 prompt_context | 2 |
| 真实 OpenAI smoke test 仍通过（含新字段） | 1 |

合计约 **18+** 项新测试。

---

## 六、未决问题

| 问题 | 决策建议 |
|---|---|
| `recent_decisions` 默认 N 多少合理？ | 默认 3；可由 `RuntimeConfig.prompt_history_size` 调，min=0（关闭） max=10 |
| 关系信息需要展示完整图还是只 actor 的局部？ | **只 actor 局部**——避免 LLM context 爆炸；前端可看全图 |
| custom_segments 是字典还是有序 list？ | **字典**——key 即语义标签（"objective" / "history" / "constraint"），rules 不必关心顺序，render 时按字母序拼 |
| enrich_prompt 是否能修改 available_actions？ | **不能**——available_actions 是引擎事实（D-014 的 schema），rules 不应篡改 |
| PromptContext 是 dataclass 还是 Pydantic BaseModel？ | **Pydantic BaseModel**——一致性 + JSON 序列化原生支持 + 与项目其他模型同风格 |

---

## 七、关联文档

- `LLM决策协议设计.md` 第四节"prompt 结构"（实施时大幅修订）
- `运行时与事件轨迹设计.md` "事件 schema"段（实施时增 prompt_context 字段）
- `规则层设计.md` 3.x 节（实施时新增 enrich_prompt 章节）
- `D-014-动作参数强Schema化.md` 第 2 节（available_actions 字段必须用 D-014 完整 schema）

---

## 八、与 v0.1.1 范围的关系

D-016 是 v0.1.1 的**最后一块拼图**——必须在 D-014 实施完后做（available_actions 需要 D-014 的扩充字段）。

实施时序约束：

```text
D-014 完成 → D-015 完成 (或选 2.1 简化版) → D-016 启动
```

D-016 完成后 → v0.1.1 release（pyproject 0.1.0-dev → 0.1.1）→ v0.2 前端启动。
