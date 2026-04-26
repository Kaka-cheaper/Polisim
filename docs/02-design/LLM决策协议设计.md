# LLM决策协议设计

## 一、文档目标

本文件定义第一版 `LLM` 决策协议。

目标：

1. 明确 LLM 在系统中的职责边界
2. 明确输入上下文结构
3. 明确输出 schema
4. 明确校验、重试、降级机制

## 二、职责边界

LLM 的职责只有一件事：

**在给定上下文和动作边界内，选择一个合法动作并给出参数。**

LLM 不负责：

1. 直接修改系统状态
2. 生成未定义的新动作类型
3. 绕过规则层
4. 决定消息何时投递

## 三、输入上下文结构

第一版传给 LLM 的上下文建议由 6 部分组成：

### 3.1 Actor Profile

当前实体自身信息：

1. `id`
2. `type`
3. 当前属性值
4. 当前角色目标

### 3.2 Local Relations

与当前实体相关的关系：

1. 直接连接的实体
2. 关系类型
3. 关系强度或值

### 3.3 Inbox Messages

上一 tick 收到的消息：

1. 消息类型
2. 发送方
3. 载荷摘要

### 3.4 Perceived World Summary

基于感知范围可见的其他实体摘要。

第一版只传摘要，不传整个世界。

### 3.5 Environment State

当前环境变量值。

### 3.6 Action Space

当前允许选择的动作列表：

1. 动作名
2. 动作参数要求
3. 动作简述

## 四、建议的输入格式

第一版建议统一为结构化 JSON 输入，再拼接简短自然语言说明。

示例：

```json
{
  "tick": 5,
  "remaining_ticks": 25,
  "actor": {
    "id": "company_a",
    "type": "Company",
    "attributes": {
      "market_share": 25,
      "cash": 120,
      "reputation": 60,
      "strategy_bias": "aggressive"
    }
  },
  "relations": [
    { "type": "competition", "target": "company_b", "value": 1.0 }
  ],
  "messages": [
    { "type": "policy_signal", "from": "regulator_main", "payload": { "signal": "加强审查", "strength": 80 } }
  ],
  "environment": {
    "market_demand": 55,
    "policy_pressure": 30,
    "public_sentiment": 5
  },
  "available_actions": [
    {
      "name": "promote",
      "params": {
        "budget": { "type": "number", "required": true }
      }
    },
    {
      "name": "do_nothing",
      "params": {}
    }
  ]
}
```

## 五、输出 Schema

第一版输出必须是结构化 JSON。

建议 schema：

```json
{
  "action": "promote",
  "params": {
    "budget": 20
  },
  "reason": "在监管压力上升前提升品牌势能，并争取用户支持。"
}
```

字段约束：

1. `action` 必填，必须存在于 `available_actions`
2. `params` 必填，可为空对象
3. `reason` 可选，但建议保留，供日志摘要使用

## 六、校验机制

第一版至少校验以下内容：

1. 输出是否为合法 JSON
2. `action` 是否存在于允许动作中
3. `params` 是否满足该动作参数要求
4. 参数类型是否匹配
5. 参数是否缺失必填字段

## 七、重试机制

第一版采用最多 2 次重试。

该值在第一版视为**协议默认值**，不放入 `Scenario.config`。

如果未来需要按场景或按实体类型调整，再考虑把它提升为配置项。

流程：

1. 第一次输出不合法
2. 系统返回明确错误信息
3. LLM 基于错误重试
4. 若仍失败，可再重试一次

重试提示应只包含：

1. 哪个字段错了
2. 期望格式是什么
3. 允许动作有哪些

重试发生在**当前 tick 内部**，属于计算过程的一部分，不推动仿真时间进入下一个 tick。

## 八、降级机制

如果重试后仍失败，则执行降级策略：

1. 优先执行 `World Definition.defaults.fallback_action`
2. 若未定义，则执行 `do_nothing`
3. 同时记录一条 `decision_rejected` 或 `fallback_used` 事件

如果当前 tick 内 LLM 调用或重试超时，也按同样规则降级，不将该决策顺延到下一 tick。

## 九、不同决策模式的协议边界

### 9.1 llm

走完整协议：输入上下文 → 结构化输出 → 校验 → 重试 → 降级

### 9.2 rule

不调用 LLM，由规则函数直接输出同样结构的 `ActionProposal`

### 9.3 random

从允许动作中随机采样，输出同样结构的 `ActionProposal`

这意味着三种决策模式在运行时应共享统一输出结构。

## 十、上下文压缩原则

为了避免 token 爆炸，第一版采用以下原则：

1. 只传感知范围内信息
2. 历史只传最近几轮摘要，不传全量事件
3. 关系传摘要，不传全图
4. 世界真相以系统状态为准，不以 LLM 记忆为准

这里的“最近几轮摘要”在第一版是**协议默认行为**，不是 `Scenario` 层配置项。

如果未来需要按场景定制摘要窗口，再考虑将其升级为独立分析/上下文配置。

## 十一、候选动作来源

`available_actions` 不应被理解为实体类型动作全集。

第一版约定：

1. `World Definition.entity_types.actions` 定义实体理论上可用的动作集合
2. `Runtime + Rules` 在当前 tick 先做筛选
3. 传给 LLM 的 `available_actions` 是当前状态下允许尝试的候选动作集合

这样可以避免让 LLM 去猜哪些动作当前其实不可执行。

## 十二、Provider 抽象层（D-005）

本协议本身与具体 LLM 厂商无关。为避免 `core/llm_policy.py` 或 `core/runtime.py`
直接依赖某家 SDK（比如 `openai.ChatCompletion`），第一版要求**所有真实 LLM 调用
走统一的 Provider ABC**。

### 12.1 抽象接口位置

- `core/providers/base.py` 定义 `LLMProvider` ABC
- `core/providers/{mock,openai,anthropic}.py` 分别实现
- 可用实现列表与 `models/config_models.LLMProviderConfig.provider` 的 `Literal`
  枚举**一一对应**——配置里出现的值必须有对应实现

### 12.2 最小接口约定

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """同步调用，返回原始文本。kwargs 至少支持 temperature / max_tokens / timeout。"""
```

异步版本（`async_generate`）留到需要真正并发决策时再加，第一版的
`RuntimeConfig.max_concurrent_decisions` 默认 1，同步接口足够。

### 12.3 MockProvider（第 2~4 步默认使用）

`core/providers/mock.py` 的 `MockProvider`：

1. 不调任何外部 API
2. 根据配置返回可复现的结构化输出（例如按实体 id 哈希选一个合法动作）
3. 支持 `seed` 参数以配合 `RuntimeConfig.random_seed`
4. 测试与 CI 默认走这条路径，避免 API key 泄露与网络不稳定

### 12.4 真实 Provider（第 5 步实装）

`openai.py` / `anthropic.py` 各自负责：

1. 从 `LLMProviderConfig.api_key_env` 指定的环境变量读取 key
2. 按 `timeout_sec` / `max_retries` / `temperature` 调用真实 SDK
3. 把 SDK 抛出的异常封装成统一的 `ProviderError`（留给 `llm_policy.py` 做协议层重试）

**不允许**在这两个文件之外的任何代码 `import openai` / `import anthropic`。

### 12.5 与本文档已有章节的关系

- 第六节"校验机制" → 由 `core/llm_policy.py` 执行，不在 Provider 层
- 第七节"重试机制" → Provider 层只做**传输级**重试（网络抖动），**协议级**重试
  （LLM 输出不合法 → 重新请求）仍由 `llm_policy.py` 负责
- 第八节"降级机制" → 完全在 `llm_policy.py` + `Runtime`，Provider 无需感知

这样分层保证：换 Provider 不影响协议，协议升级不影响 Provider。

## 十三、输出语言（session 19 追加）

### 13.1 问题

LLM 输出里有两类字段：

- **机器标识符**（`action` / `params` 的 key）——必须保持原样，语言无关
- **自然语言字段**（`reason`、Phase C 的叙事/判断/建议段落）——用户需要指定显示语言

### 13.2 机制

通过 **prompt 注入** 实现，**不**改协议结构：

- `RuntimeConfig.output_language: str`（默认 `"zh-CN"`）——全局偏好
- `core.llm_policy.build_prompt(..., language=...)`——在 payload JSON 尾部追加一段自然语言指令，显式告诉 LLM "reason 等自然语言字段使用 {language}"
- `core.llm_policy.decide` 从 `config.output_language` 读取，传给 `build_prompt`
- Provider 层**完全不感知**——`generate(prompt: str) -> str` 的契约保持不变

### 13.3 适用范围

- **决策层** `llm_policy.decide` 产出的 `ActionProposal.raw_reasoning_summary`（`reason` 字段）——✅ 受影响
- **Phase C 分析层** `core/analysis.enhance_with_llm` 的叙事 / 局势判断 / 建议段落——✅ 受影响（复用同一 `language` 参数）
- **JSON 结构字段**（`action` 动作名、`params` 的 key）——❌ 不受影响，机器标识符跨语言不变

### 13.4 为什么不放 `LLMProviderConfig`

provider 是传输层——只关心"发送 / 接收"。"用什么语言"是 Polisim 侧的业务偏好，换 Anthropic / Gemini 时应保持不变。放 `RuntimeConfig` 最干净：Runtime 已持有该配置，无需新增通道。

### 13.5 未来扩展

- CLI 可加 `--output-language <code>` 选项覆盖 YAML 配置（当前未加）
- Phase C 分析增强（`core.analysis._build_analysis_prompt`）已**复用**同一 `language` 参数——一次铺设、多处消费

## 十四、第一版不做什么

第一版不在 LLM 协议中支持：

1. 多轮链式思维持久化
2. 自定义函数调用 DSL
3. 多模型协商决策
4. 复杂记忆检索系统

第一版只解决一件事：

**让 LLM 能在稳定、可校验、可降级的协议下参与仿真决策。**
