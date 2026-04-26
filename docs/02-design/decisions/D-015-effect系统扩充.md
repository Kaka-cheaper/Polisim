# D-015：Effect 系统扩充

> **状态**：草案（2026-04-26 session 23 起草，简版）→ 待评审  
> **关联决策**：D-009（公式落代码层）；与 D-014/D-016 同属 v0.1.1 三联坑  
> **关联 pitfall**：P2 [2026-04-24] AttributeEffect 只支持 numeric delta  
> **预计实施 session**：v0.1.1 后期或 v0.2.x（**v0.2 MVP 撑得住，可推迟**）

---

## 一、决策背景（Why）

### 1.1 现状证据

`models/runtime_models.py` 当前只有 4 类 Effect：

| Effect | 用途 | 限制 |
|---|---|---|
| `AttributeEffect` | 改实体属性 | **只支持 numeric delta**——不能改 enum / string / boolean 属性（pitfalls P2 已记录） |
| `RelationEffect` | 改关系（add / remove / update_value） | 完整 |
| `MessageEffect` | 发消息 | 完整 |
| `EnvironmentEffect` | 改环境变量 | 与 AttributeEffect 同样限制（v0.1 隐含） |

### 1.2 缺失的 Effect 类型

| 缺失 | 典型场景 | v0.2 紧迫性 |
|---|---|---|
| `EntityCreateEffect` | 公司分裂、订单生成、新人加入 | 🟡 中 |
| `EntityDestroyEffect` | 公司破产、消息删除、人物离开 | 🟡 中 |
| `ChainedActionEffect` | 动作 A 触发动作 B（需防递归） | 🟢 低 |
| `BatchEffect` | 原子化应用多个 effect（事务语义） | 🟢 低 |

v0.2 前端 MVP 只需可视化现有 4 类 effect，**这 4 个新增缺失不阻塞**。

---

## 二、决策内容（What）

### 2.1 扩展 `AttributeEffect`（小改）

```python
class AttributeEffect(BaseModel):
    """属性效果（D-015 扩充版）。"""

    actor_id: str
    attribute: str

    # ── 二选一（互斥）──
    delta: float | None = None  # numeric 类型
    new_value: Any | None = None  # 任意类型（enum/string/bool/number）
```

加 `model_validator`：恰好一个非 None；类型与 actor.attributes[attribute] schema 兼容。

### 2.2 新增 `EntityCreateEffect`

```python
class EntityCreateEffect(BaseModel):
    """生成新实体（D-015）。"""

    entity_id: str  # 必须唯一，不能与现有冲突
    entity_type: str  # 必须在 world.entity_types 中
    initial_attributes: dict[str, Any] | None = None  # 部分覆盖默认值
    initial_relations: list[RelationEffect] | None = None  # 同时建立关系
```

### 2.3 新增 `EntityDestroyEffect`

```python
class EntityDestroyEffect(BaseModel):
    """删除实体（D-015）。"""

    entity_id: str  # 必须存在
    cascade: Literal["all", "preserve_messages", "preserve_relations"] = "all"
    # 删除策略：是否级联删除该实体的关系 / 邮箱 / 历史
```

### 2.4 新增 `ChainedActionEffect`（高风险，需防递归）

```python
class ChainedActionEffect(BaseModel):
    """动作触发动作（D-015）。"""

    actor_id: str
    action_type: str
    params: dict[str, Any]
    delay_ticks: int = 0  # 0 = 立刻应用；>0 = 延后到第 N tick
```

防递归约束（**Runtime 强制**）：
- 单 tick 内 chained 链长度 ≤ `runtime_config.max_chain_depth`（建议默认 3）
- 链跨 tick 不限（`delay_ticks > 0` 时归到下一 tick 的 scheduled_events）

---

## 三、影响面（Where）

| 文件 | 改动性质 |
|---|---|
| `models/runtime_models.py` | 加 3 个新 Effect 类 + AttributeEffect.new_value 字段 |
| `core/runtime.py:_apply_effects` | 加 3 类新 effect 的应用逻辑 + chain depth 校验 |
| `core/runtime.py:_make_decision` | chain effect 触发时如何注入新动作（隐式 ActionProposal？还是新 step？） |
| `core/events.py` | 新增 `entity_created` / `entity_destroyed` / `chained_action_triggered` 三类 EventKind |
| `models/scenario_models.py:WorldState` | 加实体的动态生命周期管理（已有的 entities dict 支持 add/del 操作） |
| `rules/base.py:apply_constraints` | 新建实体的属性 clamp 也要走标准流程 |
| `core/semantic_validator.py` | D-013 校验扩展：rules 声明 `actions_handled` 中是否包含 chained 动作 |
| 测试 | 6+ 项新测试（每类 effect 至少 1 项 + 防递归 + 跨 tick chain） |

**总工程量**：5-7 天（2-3 个 session）。

---

## 四、推迟理由（详细）

### 4.1 为什么 D-015 可以推迟到 v0.2.x

| 维度 | 推迟可行性 |
|---|---|
| v0.2 前端 MVP 是否需要？ | 否——4 类 effect 已能可视化（属性折线、关系图边动态、消息流、环境曲线） |
| 现有产线场景是否需要？ | 否——minimal_market 与 negotiation 都不涉及实体生命周期或动作链 |
| 是否阻塞 D-014 / D-016？ | 否——D-014 的 ActionParamSchema、D-016 的 PromptContext 都不依赖 Effect 系统 |
| 是否引入隐患？ | 否——pitfalls P2 仅是 enum 属性改值的限制，可用 Intervention 后门绕过 |

### 4.2 v0.1.1 实际收尾时是否要做？

如果用户希望 v0.1.1 真正"全 3 坑一次到位"：建议**只做 2.1 节** `AttributeEffect.new_value`（结清 pitfalls P2 第 105 行），**不做** 2.2-2.4。理由：

- AttributeEffect.new_value 工程量极小（半天 + 几个测试），结清积压坑
- EntityCreate / EntityDestroy / ChainedAction 是大改，应留到 v0.2.x 与场景需求一起设计

---

## 五、测试设计（实施时填）

留待 D-015 实施 session 详细设计。最小测试列表：

- AttributeEffect.new_value 与 delta 互斥 + 类型兼容
- EntityCreateEffect 创建后属性按 schema 走默认值 + clamp
- EntityDestroyEffect 级联删除关系 / 邮箱 / inbox
- ChainedActionEffect 单 tick 内链深度 ≤ max_chain_depth
- ChainedActionEffect 跨 tick（delay_ticks > 0）正确进入 scheduled_events 队列
- 防无限递归：A → B → A 触发时立即抛 RulesError

---

## 六、未决问题

| 问题 | 决策建议 |
|---|---|
| ChainedAction 是否走 LLM 决策？ | **不走**——chained 是规则触发，绕过 LLM 节省 token；rules 直接构造 ActionProposal |
| EntityCreateEffect 创建的实体是否参与同 tick 的激活？ | **不参与**——下一 tick 才激活，避免同 tick 内顺序敏感 bug |
| AttributeEffect.new_value 改 enum 时是否校验值在 values 列表？ | **校验**——与 D-014 的 ActionParamSchema.values 同义 |
| BatchEffect 是否需要？事务语义有多重要？ | **不做**——v1 effect 应用顺序由 `defaults.action_effect_order` 控制；事务语义由 EventLog append-only 提供天然原子性 |

---

## 七、关联文档

- `运行时与事件轨迹设计.md` 第七节"effect 应用流程"（实施时需扩充）
- `规则层设计.md` 3.2 节"effect 类型"（实施时需扩充）
- `pitfalls.md` 第 105 行 P2（实施完成时标"已结清（D-015）"）

---

## 八、与 v0.1.1 范围的关系

**用户 session 23 决策**：v0.1.1 范围 = D-014 + D-015 + D-016 全部。

**Cascade 推荐缩限**：v0.1.1 范围 = D-014 + D-016 + **D-015 只做 2.1 节**（AttributeEffect.new_value 字段）。其他三类新 Effect 推 v0.2.x。

理由：
- 缩限版工程量从 5-7 天 → 0.5 天
- 收益：仍然结清 pitfalls P2 第 105 行
- 风险：极低
- v0.2 前端 MVP 不会撞到任何缺失功能

最终是否缩限由用户在实施 session（session 24+）决定。
