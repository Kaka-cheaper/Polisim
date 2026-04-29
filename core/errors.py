"""Polisim 统一异常体系（D-011 全量落地）。

对应 session 19 Phase B 启动时产出的 D-011 决策——Runtime / Rules / EventLog /
Providers 早期只有 `ProviderError` 一个自定义异常，其余分支裸用 `RuntimeError`
/ `ValueError`，上层 ``except RuntimeError`` 容易漏抓真正的 bug。本模块给出统一
的继承根 `SimEngineError`，所有业务型异常**都应继承**它，方便上层用一条
``except SimEngineError`` 精确拦截。

**D-011 决议细节**（见 `docs/00-overview/progress.md` D-011 条目）：

- 决策日期：2026-04-24 session 19（Phase B 启动时触发）
- 采用方案 A：新建 `core/errors.py` + `SimEngineError` 基类 + 7 条支
- **session 19 落地**：基础设施 + ProviderError re-export
- **session 21 完成全量迁移**：Runtime 5 处裸用 `RuntimeError` / `ValueError` 全部换
  为 `PausedError` / `TerminatedError` / `InvalidStateError`；RulesLoadError 入树；
  实地 scope 只 5 处，原估 30~50 处是高估。其余 `ValueError` / `FileNotFoundError`
  （mock 构造参数错 / IO 错 / 用户输入错）按 Python 惯例**保留**，不属 D-011 范畴
- **session 22 加 SemanticValidationError**（D-013 跨层语义校验）为本树第 7 个子类
- `ProviderError` 从 `core/providers/base.py` 迁入本文件作为权威定义，原文件做
  re-export 保向后兼容——**既有 ``from core.providers.base import ProviderError``
  的代码无需任何改动**

**异常树**：

``SimEngineError``
├── `ProviderError`——Provider 传输层失败（网络 / 鉴权 / 429 / 5xx / 超时）
├── `LLMProtocolError`——协议层失败（JSON 不合法 / 动作不在白名单 / 重试耗尽）
├── `RulesError`——规则层错误（v1 未使用；保留供未来扩展点）
├── `RulesLoadError`——rules_module 解析失败（定义在 `core/rules_loader.py`，
│                     避免本文件反向依赖 rules 加载逻辑；构造期错误，
│                     CLI ``except SimEngineError`` 兜住后给友好提示）
├── `InvalidStateError`——Runtime 内部状态不一致（session 21 落地于 Runtime 3 处）
├── `PausedError`——在 paused=True 时调用 step() 的违约（session 21 落地）
├── `TerminatedError`——在 reached_total_ticks 后再调 step() 的违约（session 21 落地）
└── `SemanticValidationError`——D-013 跨层语义校验失败
                                 （fallback_action 与 rules 不一致、
                                  rules 声明 resolve 了未在 world 声明的 action 等）

**使用约定**：

- 具体错误应**从底层异常链式抛出**：``raise ProviderError(...) from exc``；
  保留 ``__cause__`` 以便调试
- 文本信息用中文 / 英文都可；保持与项目其他 docstring 风格一致（中文为主）
- 本模块**不**继承 Python 内置的 `RuntimeError` / `ValueError`——这就是 D-011
  的核心动机：让 ``except SimEngineError`` 与 ``except RuntimeError`` 正交
"""

from __future__ import annotations


class SimEngineError(Exception):
    """Polisim 所有业务异常的根类。

    使用模式：
    - 上层拦截："``except SimEngineError``"——把所有业务错误一网打尽
    - 不要继承 Python 内置 `RuntimeError` / `ValueError`——保持与 Python 常规
      错误路径的区分度（D-011 核心动机）
    """


class ProviderError(SimEngineError):
    """Provider 传输层失败时抛出的统一异常（D-005）。

    典型触发场景：

    - 网络超时 / 连接失败
    - HTTP 非 2xx（含 401 鉴权失败、429 速率限制、5xx 服务器错误）
    - SDK 内部抛出的不可恢复异常

    具体 provider 实现应捕获底层 SDK 异常并重新抛出 ``ProviderError``，
    保留原始异常作为 ``__cause__``（用 ``raise ProviderError(...) from exc``）。

    上层 `core/llm_policy.py` 捕获本异常后按 `LLM决策协议设计.md` 第七节
    协议级重试规则处理；不需要区分是 "key 错了" 还是 "网络抖动"——
    protocol 层的唯一关心点是 "这次调用失败了，要不要再试一次"。
    """


class LLMProtocolError(SimEngineError):
    """LLM 协议层失败——非传输错，而是"LLM 回了但不合规"类问题。

    典型触发场景：

    - 原始响应不是合法 JSON
    - ``action`` 字段不在实体允许的动作白名单内
    - ``params`` 形状与 World Definition 声明不匹配
    - 协议级重试次数耗尽仍无法得到合法响应

    v1 的 `llm_policy.decide` 捕获本异常后会走 fallback（e.g., ``do_nothing``），
    不会让异常逃出到 Runtime；但提供给 `llm_policy` 内部各阶段使用——
    例如"重提 + 附错误信息"模式（Instructor 的思路）。
    """


class RulesError(SimEngineError):
    """规则层错误（D-015 全量版启用——chained action 链深度超限）。

    **触发场景**（session 28 D-015 全量版落地）：

    - ``ChainedActionEffect`` 同 tick 内递归深度超过
      ``RuntimeConfig.max_chain_depth``——典型场景是 rules 写错让 A → B → A
      循环触发（无限递归）。Runtime 在 ``_apply_chained_action_effect`` 检测到
      ``depth > max_chain_depth`` 时立即抛本类，由 CLI 顶层 ``except SimEngineError``
      兜住 + 友好提示
    - ``EntityCreateEffect`` 试图创建 ``state.entities`` 中已存在的 ``entity_id``——
      rules 设计错（违反"全局唯一"约定）

    **不**触发场景：

    - `validate_action` 返 `ValidationResult(valid=False, errors=[...])`（不抛异常）
    - `resolve_effects` 遭遇未知 action 返空列表（防御式）
    - rules 装配失败走 `RulesLoadError`（定义在 `core/rules_loader.py`）

    **未来扩展**：若 rules 层有更多业务异常需要分类（如公式崩溃 / Effect 形状
    不合约），可继续继承本类或加细分子类。本类是 D-011 异常树为 rules 层留的
    主入口。
    """


class InvalidStateError(SimEngineError):
    """Runtime 内部状态不一致（session 21 已落地于 `Runtime`）。

    实际触发场景（截至 session 21）：

    - `Runtime.__init__` 时 `rules` 与 `scenario.rules_module` 都缺失
    - `Runtime.run_until(tick)` 目标 tick 小于当前 tick（违约调用）
    - `Runtime._make_decision` 命中 unknown ``decision_mode``（不可达分支断言）

    未来扩展候选：tick 编号跳变 / entity_id 未注册却被引用 /
    scheduled_event 指向不存在的 message_type 等。
    """


class PausedError(SimEngineError):
    """在 ``paused=True`` 时调用 ``step()`` 的违约（session 21 已落地）。

    Runtime 对该场景抛本异常；调用方应 ``resume()`` 后再 step。
    """


class TerminatedError(SimEngineError):
    """在 ``reached_total_ticks=True`` 后再调 ``step()`` 的违约（session 21 已落地）。

    Runtime 对该场景抛本异常；这是"正常终止态"，调用方应停止推进，
    可继续做 analyze_run / get_snapshot 等只读操作。
    """


class SemanticValidationError(SimEngineError):
    """D-013 跨层语义校验失败（session 22 落地）。

    现有的 `core/scenario_loader._validate_cross_references` 已经覆盖了"World↔Scenario
    引用一致性"（实体 type / 关系 type / 环境变量 / scheduled_event 消息类型 / breakpoint
    引用等）。但有一类语义错误**仅当 rules 实例可见时才能发现**：

    - ``world.defaults.fallback_action`` 必须能被 ``rules.resolve_effects`` 处理
      （否则第一次 fallback 触发时崩在运行期，详见 `pitfalls.md` P1）
    - rules 声明能 resolve 的 action 不应包含 world 未声明的（防开发者拼写错）

    这些校验在 Runtime 构造时（rules 装配后、bootstrap 前）一次性跑完，
    失败聚合所有问题统一抛出，便于 LLM 辅助建模的修复循环消费结构化反馈
    （见 `LLM辅助建模方案.md` 5.2 节）。

    携带 ``issues`` 字段——结构化错误条目列表（每条带 ``field_path / kind / detail``），
    供 LLM 反馈格式器渲染成不同形态（YAML 行号 / DSL 源码位置 / 自然语言提示）。
    元素类型由 `core/semantic_validator.SemanticIssue` 定义；本类不导入它以避免
    反向依赖，issues 字段在类型上只声明为 ``list``。
    """

    def __init__(self, message: str, issues: list | None = None) -> None:
        super().__init__(message)
        self.issues: list = list(issues) if issues else []
