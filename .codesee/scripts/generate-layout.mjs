#!/usr/bin/env node
/**
 * CodeSee · 功能视图初始布局生成器（方案 C：分层约束布局）
 *
 * 读取：
 *   - .codesee/features.json（Epic/Feature 归属 + cross_feature 连线）
 *   - .codesee/layout.json 的 views.overview（概览视图人工布局坐标）
 *
 * 输出：
 *   - 更新 .codesee/layout.json 的 views.features（功能视图坐标）
 *   - 不动 overview / steps:* 等其他 view
 *
 * 算法（方案 C：概览锚点 + 分层约束布局）：
 *   1. 读概览坐标 → 归一化 → 乘以目标画布尺寸 → 得到容器锚点
 *   2. 估算每个容器包围盒大小 = f(Feature 数量)
 *   3. 容器间矩形排斥（保持相对位置，消除重叠）
 *   4. 容器内按 cross_feature 拓扑排序 → 从左到右、从上到下排列
 *   5. 跨容器连线微调（±偏移）
 *
 * 用法：
 *   node .codesee/scripts/generate-layout.mjs
 *   node .codesee/scripts/generate-layout.mjs --dry-run   # 只打印不写入
 */

import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'

/* ================================ 配置 ================================ */

const CELL_W = 300       // 单个 Feature 节点占位宽度
const CELL_H = 200       // 单个 Feature 节点占位高度
const MAX_COLS = 3       // 容器内最大列数
const CONTAINER_PAD = 80 // 容器内边距
const CONTAINER_GAP = 120 // 容器间最小间距
const CANVAS_SCALE = 4   // 概览坐标 → 功能视图坐标的放大系数

/* ================================ 读取 ================================ */

const root = path.resolve(process.cwd())
const featuresPath = path.join(root, '.codesee', 'features.json')
const layoutPath = path.join(root, '.codesee', 'layout.json')

if (!fs.existsSync(featuresPath)) {
  console.error('✗ 找不到 .codesee/features.json')
  process.exit(2)
}

const features = JSON.parse(fs.readFileSync(featuresPath, 'utf-8'))
let layout = { version: '0', views: {} }
if (fs.existsSync(layoutPath)) {
  layout = JSON.parse(fs.readFileSync(layoutPath, 'utf-8'))
}

const dryRun = process.argv.includes('--dry-run')

/* ================================ 步骤 1：概览坐标 → 容器锚点 ================================ */

const overviewPositions = layout.views?.overview ?? {}
const epicIds = features.epics.map(e => e.id)

// 收集概览坐标
const epicAnchors = new Map() // epicId → {x, y}
for (const epic of features.epics) {
  const key = `epic:${epic.id}`
  const pos = overviewPositions[key]
  if (pos) {
    epicAnchors.set(epic.id, { x: pos.x * CANVAS_SCALE, y: pos.y * CANVAS_SCALE })
  } else {
    // 没有概览坐标的 Epic，按 order 给默认位置
    epicAnchors.set(epic.id, { x: (epic.order ?? 0) * 1500, y: 0 })
  }
}

/* ================================ 步骤 2：估算容器包围盒 ================================ */

// 按 epicId 分组 Feature
const featuresByEpic = new Map() // epicId → Feature[]
for (const f of features.features) {
  const eid = f.epicId || '__misc__'
  if (!featuresByEpic.has(eid)) featuresByEpic.set(eid, [])
  featuresByEpic.get(eid).push(f)
}

// 容器尺寸
const containers = new Map() // epicId → {x, y, w, h, features: Feature[]}
for (const epicId of epicIds) {
  const fts = featuresByEpic.get(epicId) || []
  const cols = Math.min(MAX_COLS, Math.max(1, fts.length))
  const rows = Math.ceil(fts.length / cols)
  const w = cols * CELL_W + CONTAINER_PAD * 2
  const h = rows * CELL_H + CONTAINER_PAD * 2
  const anchor = epicAnchors.get(epicId) || { x: 0, y: 0 }
  containers.set(epicId, {
    x: anchor.x - w / 2,
    y: anchor.y - h / 2,
    w,
    h,
    features: fts,
  })
}

/* ================================ 步骤 3：容器间矩形排斥 ================================ */

function rectsOverlap(a, b) {
  return !(a.x + a.w + CONTAINER_GAP <= b.x ||
           b.x + b.w + CONTAINER_GAP <= a.x ||
           a.y + a.h + CONTAINER_GAP <= b.y ||
           b.y + b.h + CONTAINER_GAP <= a.y)
}

function resolveOverlaps(containerList, iterations = 20) {
  for (let iter = 0; iter < iterations; iter++) {
    let moved = false
    for (let i = 0; i < containerList.length; i++) {
      for (let j = i + 1; j < containerList.length; j++) {
        const a = containerList[i]
        const b = containerList[j]
        if (!rectsOverlap(a, b)) continue

        // 计算重叠量并推开
        const overlapX = Math.min(a.x + a.w + CONTAINER_GAP - b.x, b.x + b.w + CONTAINER_GAP - a.x)
        const overlapY = Math.min(a.y + a.h + CONTAINER_GAP - b.y, b.y + b.h + CONTAINER_GAP - a.y)

        // 沿重叠最小的轴推开
        if (overlapX < overlapY) {
          const push = overlapX / 2 + 1
          if (a.x < b.x) { a.x -= push; b.x += push }
          else { a.x += push; b.x -= push }
        } else {
          const push = overlapY / 2 + 1
          if (a.y < b.y) { a.y -= push; b.y += push }
          else { a.y += push; b.y -= push }
        }
        moved = true
      }
    }
    if (!moved) break
  }
}

const containerList = [...containers.values()]
resolveOverlaps(containerList)

/* ================================ 步骤 4：容器内拓扑排列 ================================ */

// 构建 cross_feature 邻接表（仅同 Epic 内的连线用于排序）
const crossLinks = features.cross_feature || []

function topoSortFeatures(fts, epicId) {
  const ids = new Set(fts.map(f => f.id))
  // 收集同 Epic 内的有向边
  const inDeg = new Map()
  const adj = new Map()
  for (const f of fts) {
    inDeg.set(f.id, 0)
    adj.set(f.id, [])
  }
  for (const link of crossLinks) {
    if (ids.has(link.from) && ids.has(link.to)) {
      adj.get(link.from).push(link.to)
      inDeg.set(link.to, (inDeg.get(link.to) || 0) + 1)
    }
  }
  // Kahn's algorithm
  const queue = []
  for (const [id, deg] of inDeg) {
    if (deg === 0) queue.push(id)
  }
  const sorted = []
  while (queue.length > 0) {
    // 稳定排序：按 id 字母序
    queue.sort()
    const node = queue.shift()
    sorted.push(node)
    for (const next of (adj.get(node) || [])) {
      inDeg.set(next, inDeg.get(next) - 1)
      if (inDeg.get(next) === 0) queue.push(next)
    }
  }
  // 环中剩余节点按 id 追加
  for (const f of fts) {
    if (!sorted.includes(f.id)) sorted.push(f.id)
  }
  return sorted
}

/* ================================ 步骤 5：生成最终坐标 ================================ */

const featurePositions = {} // "feature:f-xxx" → {x, y}

for (const [epicId, container] of containers) {
  const fts = container.features
  if (fts.length === 0) continue

  const sortedIds = topoSortFeatures(fts, epicId)
  const cols = Math.min(MAX_COLS, Math.max(1, fts.length))

  for (let idx = 0; idx < sortedIds.length; idx++) {
    const fid = sortedIds[idx]
    const col = idx % cols
    const row = Math.floor(idx / cols)
    const x = container.x + CONTAINER_PAD + col * CELL_W
    const y = container.y + CONTAINER_PAD + row * CELL_H
    featurePositions[`feature:${fid}`] = { x, y }
  }
}

/* ================================ 步骤 5.5：跨容器连线微调 ================================ */

// 对有跨容器连线的 Feature，稍微偏向目标方向
const CROSS_NUDGE = 40
for (const link of crossLinks) {
  const fromKey = `feature:${link.from}`
  const toKey = `feature:${link.to}`
  const fromPos = featurePositions[fromKey]
  const toPos = featurePositions[toKey]
  if (!fromPos || !toPos) continue

  // 只对跨 Epic 的连线做微调
  const fromEpic = features.features.find(f => f.id === link.from)?.epicId
  const toEpic = features.features.find(f => f.id === link.to)?.epicId
  if (fromEpic === toEpic) continue

  // 把 from 节点稍微推向 to 的方向
  const dx = toPos.x - fromPos.x
  const dy = toPos.y - fromPos.y
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist > 0) {
    fromPos.x += (dx / dist) * CROSS_NUDGE
    fromPos.y += (dy / dist) * CROSS_NUDGE
  }
}

/* ================================ 写入 ================================ */

// 保留原有 views 中非 features 的部分
layout.views = layout.views || {}
layout.views.features = featurePositions
layout.generated_at = new Date().toISOString()

if (dryRun) {
  console.log(JSON.stringify(layout, null, 2))
  console.log(`\n[dry-run] 生成 ${Object.keys(featurePositions).length} 个 Feature 坐标`)
} else {
  fs.writeFileSync(layoutPath, JSON.stringify(layout, null, 2) + '\n', 'utf-8')
  console.log(`✓ 已更新 ${layoutPath}`)
  console.log(`  Feature 坐标: ${Object.keys(featurePositions).length} 个`)
  console.log(`  容器数: ${containers.size}`)
  console.log(`  排斥迭代后无重叠`)
}
