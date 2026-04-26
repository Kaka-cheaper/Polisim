# MVP场景定义

## 一、场景名称

**多组织竞争与合作推演**

## 二、为什么选这个场景

这个场景适合作为首个 MVP，因为它具备四个优点：

1. 比国际政治简单，复杂度可控
2. 比纯社交模拟更有决策价值
3. 动作和关系容易结构化
4. 后续容易迁移到政策、平台生态、供应链等相邻场景

这个场景的目标不是预测真实市场，而是验证分层方案的闭环：

1. 多实体类型
2. 消息传递
3. 环境事件
4. 暂停与干预
5. 基于全轨迹的分析输出
6. 世界定义、场景、规则、运行内核之间的职责分离

## 三、场景描述

在一个区域市场中，多个组织围绕市场份额、合作关系、资源成本、监管压力和舆论环境持续博弈。

系统需要能回答：

1. 哪一方逐步取得优势
2. 哪些事件触发了转折点
3. 当前局势最大的风险点是什么
4. 如果用户现在介入，应该优先做什么

## 四、范围控制

### 4.1 实体规模

MVP 建议控制在 9 个实体以内：

1. 3 家企业
2. 1 个监管方
3. 2 个媒体节点
4. 2 个用户群体
5. 1 个供应方

### 4.2 轮次规模

1. `total_ticks = 20 ~ 30`
2. `max_ticks = 40`

### 4.3 决策模式

建议采用混合决策：

1. 企业：`llm`
2. 监管方：`llm`
3. 媒体节点：`rule` 或 `llm`
4. 用户群体：`rule`
5. 供应方：`rule`

## 五、实体设计

### 5.1 企业（Company）

核心属性：

1. `market_share`
2. `cash`
3. `reputation`
4. `supply_stability`
5. `compliance_risk`
6. `influence`
7. `strategy_bias`

可选动作：

1. `promote`
2. `change_price`
3. `seek_alliance`
4. `expand`
5. `shrink`
6. `lobby_regulator`
7. `attack_competitor`
8. `stabilize_supply`
9. `do_nothing`

### 5.2 监管方（Regulator）

核心属性：

1. `strictness`
2. `credibility`
3. `pressure_level`
4. `intervention_threshold`

可选动作：

1. `issue_warning`
2. `increase_scrutiny`
3. `release_policy_signal`
4. `penalize`
5. `stay_observe`

### 5.3 媒体节点（MediaNode）

核心属性：

1. `reach`
2. `stance`
3. `credibility`
4. `heat_preference`

可选动作：

1. `report_positive`
2. `report_negative`
3. `amplify_event`
4. `ignore_event`

### 5.4 用户群体（UserGroup）

核心属性：

1. `size`
2. `price_sensitivity`
3. `trust_preference`
4. `current_support`

可选动作：

1. `shift_support`
2. `stay_neutral`
3. `spread_opinion`

### 5.5 供应方（Supplier）

核心属性：

1. `capacity`
2. `reliability`
3. `preferred_partner`
4. `cost_level`

可选动作：

1. `support_partner`
2. `raise_cost`
3. `stabilize_output`
4. `reduce_output`

## 六、关系设计

MVP 至少支持以下关系：

1. `competition`
2. `alliance`
3. `supply_dependency`
4. `influence`
5. `trust`

其中 `alliance`、`supply_dependency`、`influence`、`trust` 应支持动态变化。

## 七、环境设计

### 7.1 环境变量

1. `market_demand`
2. `policy_pressure`
3. `public_sentiment`
4. `resource_cost`
5. `risk_level`

### 7.2 环境事件

MVP 至少支持以下预设事件：

1. 政策信号加强
2. 原材料成本上升
3. 某企业出现负面新闻
4. 市场需求波动

## 八、消息设计

MVP 建议支持以下消息类型：

1. `policy_signal`
2. `cooperation_request`
3. `market_attack`
4. `media_report`
5. `supply_change`
6. `user_opinion_shift`
7. `regulatory_warning`

消息传播至少支持：

1. 定向发送
2. 广播
3. 按关系传播

## 九、用户交互

MVP 必须支持：

1. 手动暂停
2. 每轮暂停
3. 条件暂停
4. 暂停后请求即时分析
5. 人工干预后继续运行

建议首批人工干预包括：

1. 向某企业注入一条政策消息
2. 强制监管方执行一次动作
3. 直接修改某企业的 `cash` 或 `reputation`

## 十、输出设计

### 10.1 每轮输出

每轮至少输出：

1. 环境状态
2. 实体关键属性摘要
3. 本轮动作
4. 本轮新增消息
5. 关系变化

### 10.2 暂停时输出

至少包括：

1. 当前优势方
2. 当前脆弱方
3. 最近几轮关键变化
4. 当前最大风险点
5. 当前建议

### 10.3 最终输出

至少包括：

1. 全轨迹总结
2. 关键转折点
3. 各实体最终状态比较
4. 局势判断
5. 面向用户的建议

## 十一、成功标准

如果 MVP 能做到以下几点，就说明方向成立：

1. 稳定跑完 20-30 个 tick
2. 用户能中途暂停并得到当前分析
3. 用户能干预后看到后续轨迹变化
4. 最终报告基于轨迹而不是只看终态
5. 大部分能力不依赖行业硬编码

## 十二、MVP 不做什么

首个 MVP 不做：

1. 多场景同时支持
2. 实体动态增删
3. 分布式大规模模拟
4. 可视化大屏
5. 超复杂 DSL
6. 高精度现实预测承诺

MVP 的唯一目标是：

**证明“世界定义 + 场景实例 + 规则层 + 运行内核 + 事件轨迹”这一闭环可行。**
