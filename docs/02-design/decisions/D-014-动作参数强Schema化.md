# D-014：动作参数强 Schema 化

> **状态**：草案（2026-04-26 session 23 起草）→ 待评审  
> **关联决策**：D-009（公式落代码层）、D-013（跨层语义校验）；前置 D-016（prompt 规范化）  
> **关联 pitfall**：P2 [2026-04-25] random decision_mode 对带参动作不友好  
> **预计实施 session**：session 24-25（2-3 个 session）

---

## 一、决策背景（Why）

### 1.1 现状证据

当前 `ActionParamSchema` 只声明 2 个字段：

```python
class ActionParamSchema(BaseModel):
    type: Literal["number", "string", "boolean", "entity_ref"]
    required: bool = False
```

LLM 收到的参数信息也只有 type + required（`core/llm_policy.py:101-106`）：

```python
"params": {
    p_name: {"type": p.type, "required": p.required}
    for p_name, p in action_schema.params.items()
}
```

### 1.2 现状导致的 4 类问题

| 问题 | 后果 | 证据 |
|---|---|---|
| **random mode 失败率高** | charlie 75% 概率选到带参动作 → 缺参 → 校验拒绝 → fallback | pitfalls.md P2 顶条；`tests/test_rules_three_party_negotiation.py::test_three_decision_modes_all_active` |
| **LLM 不知参数语义** | 只见 `{"budget": {"type": "number", "required": true}}`，看不到"budget 是动作预算上限"等语义提示 | `core/llm_policy.py:build_prompt` payload 缺 description 字段 |
| **参数取值无约束** | LLM 可能给出 budget=-100 / budget=999999，校验只看类型不看取值 | `models/runtime_models.py:ActionProposal.params: dict[str, Any]` 无范围检查 |
| **前端无可解释面板** | 前端要展示"动作详情"只能展示 raw type—— UI 无法做出可用面板 | v0.2 前端 MVP 阻塞点 |

### 1.3 v0.2 前端紧迫性 🔴 关键

v0.2 实时态势前端的"LLM 决策面板 / 干预面板"必须能向用户展示：

> "这个动作叫 `promote`，参数 `budget` 是数值型（10-1000），表示推广预算，默认 50。"

没有强 schema，前端只能做"raw JSON 展示"，体验等同于看终端输出。**这是 v0.2 必须解决的引擎侧前置**。

---

## 二、决策内容（What）

### 2.1 扩充 `ActionParamSchema` 加 6 个字段

参考 `AttributeSchema` 已有的设计（type / min / max / values / clamp / default 模式）：

```python
class ActionParamSchema(BaseModel):
    """动作参数定义（D-014 扩充版）。"""

    model_config = ConfigDict(extra="forbid")

    # ── 现有字段（不变）──
    type: Literal["number", "string", "boolean", "entity_ref"]
    required: bool = False

    # ── D-014 新增字段 ──
    description: str | None = None
    """参数语义说明。LLM 必读以理解参数用途；前端展示在动作详情面板的 tooltip。
    强烈建议填写——空值时降级为参数名本身。"""

    default: Any = None
    """默认值。当 required=False 且 LLM 未提供时使用；random mode 缺参时也使用。
    类型必须与 `type` 一致——load 期校验。"""

    min: float | None = None
    """数值下限（type=number 时）。校验在 BaseRules.validate_action 中执行。
    与 AttributeSchema.min 同义。"""

    max: float | None = None
    """数值上限（type=number 时）。校验在 BaseRules.validate_action 中执行。"""

    values: list[str] | None = None
    """枚举候选值（type=string 时）。LLM 看到此字段时只会从中选；
    BaseRules.validate_action 校验提议的 string 值是否在列表中。"""

    entity_type_filter: list[str] | None = None
    """实体类型限定（type=entity_ref 时）。例如 actor 必须是 'company' 类型。
    BaseRules.validate_action 校验目标实体的 type 是否在列表中。"""
```

### 2.2 字段语义约束（cross-validation）

加入 `model_validator(mode="after")`：

| 约束 | 说明 |
|---|---|
| `default is not None` 时，`type` 与 `default` 类型必须一致 | float ↔ number / str ↔ string / bool ↔ boolean / str ↔ entity_ref |
| `min` / `max` 仅当 `type="number"` 时有意义 | 否则抛 ValueError |
| `values` 仅当 `type="string"` 时有意义 | 否则抛 ValueError |
| `entity_type_filter` 仅当 `type="entity_ref"` 时有意义 | 否则抛 ValueError |
| `min <= max`（如果两者都给） | 否则抛 ValueError |
| `default in values`（如果 values 给了） | 否则抛 ValueError |

### 2.3 JSON Schema 同步

`schemas/world_definition.schema.json` 中 `ActionParamSchema` 同步扩充。约束用 JSON Schema 的 `if/then` 或 `dependencies` 表达：

```json
{
  "type": "object",
  "required": ["type"],
  "additionalProperties": false,
  "properties": {
    "type": {"type": "string", "enum": ["number", "string", "boolean", "entity_ref"]},
    "required": {"type": "boolean", "default": false},
    "description": {"type": "string"},
    "default": {},
    "min": {"type": "number"},
    "max": {"type": "number"},
    "values": {"type": "array", "items": {"type": "string"}},
    "entity_type_filter": {"type": "array", "items": {"type": "string"}}
  }
}
```

JSON Schema 不强制 cross-field 约束（写起来太复杂，得不偿失）——这些约束**只在 Pydantic 层强制**。这是 Polisim 一贯的"JSON Schema 做语法层、Pydantic 做语义层"分工。

---

## 三、影响面（Where）

| 文件 | 改动性质 | 工作量 |
|---|---|---|
| `schemas/world_definition.schema.json` | 加 5 个新字段定义 | 小 |
| `models/world_models.py:ActionParamSchema` | 加字段 + model_validator | 中 |
| `core/llm_policy.py:build_prompt` | 在 prompt payload 的 available_actions 里展示新字段（特别是 description / default / min / max / values） | 中 |
| `rules/base.py:BaseRules.validate_action` | 加参数 min/max/values/entity_type_filter 校验 | 中 |
| `core/runtime.py:_decide_via_random` | 升级为"按 schema 填随机参数"——使用 default 或在 min/max 范围内采样 | 中 |
| `scenarios/minimal_market/world.yaml` | 给 `promote.budget` 补 description / min / max / default | 小 |
| `scenarios/three_party_negotiation/world.yaml` | 给 `propose / accept / reject` 的所有参数补元信息 | 小 |
| `tests/test_world_models.py` | 加 ActionParamSchema cross-validation 测试 | 中 |
| `tests/test_rules_base.py` | 加 validate_action 参数约束新测试 | 中 |
| `tests/test_runtime.py:_decide_via_random` 路径 | random mode 现在能正常给带参动作出参——更新测试期待 | 中 |
| `tests/test_definition_loader.py` | 加 D-014 字段 schema 校验测试 | 小 |
| `pitfalls.md` 顶条 P2 | 标"已结清（D-014）"，类似 D-013 结清 fallback_action 的处理 | 小 |

**总工程量**：4-5 天（1-2 个 session）。

---

## 四、迁移路径（How）

### 4.1 实施顺序（一个 session 内）

1. **schema + Pydantic 双写**（第一步必须先做完，下游全靠它）
   - 改 `world_definition.schema.json`：加字段
   - 改 `world_models.py:ActionParamSchema`：加字段 + cross-validator
   - 加 `tests/test_world_models.py` 新测试：cross-validation 全分支
   - 跑 `tests/test_definition_loader.py` 确认两个产线场景仍能 load（向后兼容）
2. **LLM 协议层升级**
   - `build_prompt` 让 available_actions 输出完整字段（description / default / min / max / values 都给 LLM 看）
   - `tests/test_llm_policy.py` 验证 prompt payload 含新字段
3. **Rules 校验升级**
   - `BaseRules.validate_action` 实施 min/max/values/entity_type_filter 校验
   - `tests/test_rules_base.py` 加新校验测试
4. **Runtime random mode 升级**
   - `_decide_via_random` 按 schema 填参（用 default 或随机采样）
   - 结清 P2 顶条：随机模式不再失败
   - `tests/test_runtime.py` 更新 random mode 期待
5. **场景 YAML 迁移**
   - 给 minimal_market / three_party_negotiation 所有 action.params 补 description / 合理 default
6. **回归测试 + 文档同步**
   - 跑全部 599 测试 + 新加测试，期望全绿
   - 更新 `世界定义文件格式设计.md` 第 X 节描述 ActionParamSchema 的扩充
   - 更新 `pitfalls.md` P2 顶条状态

### 4.2 向后兼容性

✅ **完全向后兼容**——所有新字段都是可选（default=None）。已有 YAML 不需要任何改动就能 load。

但**强烈建议**所有产线场景**主动迁移**——补 description 等元信息，让 v0.2 前端能展示完整动作面板。

---

## 五、测试设计

### 5.1 新增测试（约 30+ 项）

| 测试文件 | 新增测试主题 |
|---|---|
| `tests/test_world_models.py` | ActionParamSchema cross-validation 全分支（type×default 一致性 / min<=max / default in values 等约束） |
| `tests/test_rules_base.py` | validate_action 对 min/max/values/entity_type_filter 越界的拒绝（合规与不合规两种） |
| `tests/test_runtime.py` | random mode 对带参动作能稳定生成有效提议（覆盖 number/string/entity_ref 三种参数采样） |
| `tests/test_llm_policy.py` | build_prompt 在 available_actions 中展示新字段（description / default / values 等出现在 payload） |
| `tests/test_definition_loader.py` | 含 D-014 完整字段的 world.yaml 能成功 load + 含非法字段（如 type=number 但 values 给了）能被拒绝 |
| `tests/test_rules_minimal_market.py` | 现有 `promote(budget)` 在 budget < min 时被拒（如果场景 YAML 设了 min） |

### 5.2 回归测试

- 跑 `pytest tests/ -q`，期望 599 + 30 ≈ 630 通过
- 特别关注：`test_three_decision_modes_all_active` 现在应该 random 路径也成功（不再 75% fallback）

### 5.3 验收证据模板

按 `验收标准.md` 第 6.1 节模板：

```text
验收对象：D-014 动作参数强 Schema 化
对应验收项：（自定 D-014 验收清单——见本文第六节）
输入：
  - schemas/world_definition.schema.json（已扩充）
  - 场景 YAML（已迁移）
执行方式：
  1. pytest tests/ -q
  2. polisim run scenarios/three_party_negotiation/scenario.yaml --ticks 8
     （观察 charlie 不再 75% fallback）
实际输出：
  - 全部测试通过
  - 三人谈判中 charlie 提交的 propose 含合理 budget（在 min/max 范围内）
是否通过：✅
```

---

## 六、D-014 验收清单

实施完成的判定标准（按 AGENTS.md 第 3.5 节"必须给验收证据"）：

- [ ] **C1：schema/Pydantic 双写一致** —— 6 个新字段在两处都存在且约束等价
- [ ] **C2：cross-validation 完整** —— 6 项约束全部由 model_validator 实施
- [ ] **C3：LLM 看到完整信息** —— build_prompt 的 available_actions 含 description 等字段（test 验证）
- [ ] **C4：random mode 不再失败** —— `test_three_decision_modes_all_active` 中 charlie 路径成功率从 ~25% 升至 100%
- [ ] **C5：rules 校验生效** —— validate_action 对越界参数返回 valid=False
- [ ] **C6：向后兼容** —— 现有产线场景 YAML（如未迁移）仍能 load 与运行
- [ ] **C7：场景 YAML 迁移** —— 两个产线场景的全部 action.params 补充元信息
- [ ] **C8：pitfall 结清** —— pitfalls.md P2 顶条标"已结清（D-014）"
- [ ] **C9：回归零影响** —— 全部已有测试 + 新测试通过

---

## 七、未决问题

| 问题 | 评估 | 决策建议 |
|---|---|---|
| `default` 是否支持函数式（如 `default: now()`）？ | 复杂、引入计算逻辑、违反"World 是声明性"分层 | **拒绝**——只支持静态字面量 |
| `entity_ref` 类型的 `default` 怎么写？写实体 id 还是占位？ | id 是 scenario 实例信息，World 层不该知道 | `default` 对 entity_ref **禁止设默认**（设 None 或不设） |
| 是否要加 `regex` 字段（type=string 的正则约束）？ | 罕用、增加复杂度、可推迟 | **不加**——v0.1.1 不做；未来场景需要时再开 D-xxx |
| 数值类型是否区分 int 与 float？ | 当前 type=number 同时覆盖 int 与 float | **不区分**——保持现状；min/max 用 float 表达即可 |
| 错误信息是否需要本地化？（中文 vs 英文） | 现有 errors 都是中文 | 保持中文一致 |

---

## 八、关联文档

- `世界定义文件格式设计.md` 第三节"动作类型"（实施时需更新此节描述新字段）
- `规则层设计.md` 3.2 节"validate_action 通用契约"（实施时需扩充校验项）
- `LLM决策协议设计.md` 第四节"prompt 结构"（实施时需更新 available_actions payload schema）
- `运行时与事件轨迹设计.md` 十二节"random decision_mode"（实施时需更新降级行为说明）
- `pitfalls.md` P2 顶条（实施完成后标结清）

---

## 九、版本号策略

D-014 是**向后兼容**改动——所有新字段都是可选。

- `pyproject.toml` 版本：`0.1.0-dev` → `0.1.1-dev`（实施过程中）→ `0.1.1`（D-014/D-015/D-016 全部实施完成后正式发版）
- World definition 格式版本：仍是 `0.1`（不升）—— 因为是**纯加字段不破现有**

如果未来某个决策 break 现有 YAML（如改字段语义、删字段），那才升 World 格式版本到 `0.2`。
