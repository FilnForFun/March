# March - OpenClaw 巴别塔架构配置仓库

> **BABEL TOWER v10** - 主动代理架构（感知→提炼→压缩→联系→执行）

## 📊 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    BABEL TOWER v10                           │
│                                                             │
│  L6 执行层 ⚡  统一执行层 (意图→计划→执行→子代理路由)          │
│  L5 谱系层 🔗  知识图谱 (5701实体/13545关系/路径发现)          │
│  L4 知识层 📚  蒸馏管线 (raw→distilled→向量化/自动扫描)        │
│  L3 项目层 📁  项目工作区 (129个项目/文档)                     │
│  L2 任务层 ⏰  16个Cron任务 + 每日三思 + 心跳 + 达尔文         │
│  L1 记忆层 🧠  58个记忆文件 + 25个归档 + 语义搜索 + CACE      │
│  L0 对话层 💬  84个会话 + 1334条消息 + 全文索引               │
│                                                             │
│  横向能力: 达尔文进化引擎 (用进/废退/变异/自然选择)            │
│  压缩引擎: CACE (内容感知/语义评分/混合策略/结构化摘要)        │
│  基础设施: OpenClaw Gateway (飞书 + qwen3.6-plus)            │
└─────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
March/
├── config/
│   └── openclaw.json          # OpenClaw 主配置 (已脱敏)
├── babel/
│   ├── babel-index.json       # 巴别塔总索引
│   ├── session-fts.json       # 会话全文索引 (3.16MB)
│   ├── semantic-graph.json    # 语义关联图谱
│   └── unified-index.json     # 统一知识索引
├── scripts/
│   ├── knowledge-distiller-auto.py  # 知识蒸馏管线
│   ├── darwin_evolution.py          # 达尔文自进化引擎
│   ├── darwin-auto.py               # 达尔文扫描脚本
│   ├── babel-selfcheck-engine.py    # 每日三思自检引擎
│   └── qmc_decrypt.py               # QMC 音乐解密
├── skills/                      # 巴别塔技能目录 (软链接/引用)
├── .gitignore
└── README.md
```

## 🔧 核心配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **模型** | 阿里云百炼/qwen3.6-plus | 主模型 |
| **渠道** | 飞书 (feishu) | 主要交互渠道 |
| **Cron 任务** | 16 个 | 全部 agent 类型 |
| **子代理超时** | 600 秒 (10 分钟) | 升级后 |
| **Cron 超时** | 300 秒 (5 分钟) | 升级后 |
| **会话超时** | 1800 秒 (30 分钟) | 全局 |

## 📈 核心能力

| 能力 | 状态 | 说明 |
|------|------|------|
| **主动搜索** | ✅ | 会话+记忆+技能+知识 统一搜索 |
| **主动压缩** | ✅ | CACE 内容感知压缩 (L0-L3 四级) |
| **主动联系** | ✅ | 5701 实体/13545 关系图谱 |
| **自进化** | ✅ | 每周自动达尔文扫描 |
| **意图识别** | ✅ | 5 意图 × 6 领域分类 |
| **统一执行** | ✅ | 意图→计划→执行 全链路 |

## 🔄 更新策略

### 自动推送
- **每日 03:00**: Windows 计划任务 `March-Repo-Auto-Push` 自动推送
- **OpenClaw 升级前**: 手动运行 `auto-push.bat` 备份当前状态
- **巴别塔架构升级前**: 手动运行 `auto-push.bat` 备份当前状态

### 手动推送
```powershell
# 运行自动推送脚本
C:\Users\30959\.openclaw\workspace\March\auto-push.bat

# 或手动推送
cd C:\Users\30959\.openclaw\workspace\March
git add -A
git commit -m "Manual update: [description]"
git push origin main
```

### 达尔文进化扫描
- **每周日 22:00**: 达尔文进化扫描自动更新索引

## ⚠️ 安全说明

- `openclaw.json` 已脱敏，API Keys 替换为 `***REDACTED***`
- 实际使用时请替换为真实的 API Keys
- `.gitignore` 已配置排除敏感文件

## 📅 创建时间

- **仓库创建**: 2026-04-13
- **巴别塔版本**: v10
- **OpenClaw 版本**: 2026.4.8
