# 舆情通 - 智能问答与检索Agent系统

## 项目简介

舆情通是一个面向舆情场景的智能问答与检索Agent系统，实现舆情从实时抓取到自动简报生成的全流程自动化，提供一站式的舆情管理解决方案。

## 核心功能

- **智能问答**: 基于LLM的Agent系统，支持自然语言交互
- **语义检索**: Hybrid Retrieval + 多阶段排序策略
- **舆情抓取**: 多源实时爬虫（新闻/社交媒体/论坛）
- **自动简报**: 一键生成舆情分析简报
- **热点分析**: 实时监测热点话题
- **多模态检索**: 支持文本与图像跨模态检索

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React + Ant Design)              │
├─────────────────────────────────────────────────────────────┤
│                        API网关 (FastAPI)                      │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Agent系统   │   检索引擎    │   爬虫服务   │    简报服务     │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                    工具层 (检索/数据库/爬虫)                    │
├─────────────────────────────────────────────────────────────┤
│     记忆层 (Redis缓存 + PostgreSQL存储 + 向量索引)            │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 一键启动

```bash
# 克隆项目
git clone https://github.com/essss-son/Yuqingtong.git
cd Yuqingtong

# 配置环境变量
cp .env.example .env
# 编辑.env文件，配置OpenAI API Key

# 启动服务
docker-compose up -d
```

### 访问地址

- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 项目结构

```
Yuqingtong/
├── backend/                 # 后端代码
│   ├── agents/             # Agent系统
│   ├── tools/              # 工具封装
│   ├── memory/             # 记忆机制
│   ├── retrieval/          # 检索引擎
│   ├── models/             # 数据模型
│   ├── services/           # 业务服务
│   ├── api/                # API路由
│   └── config/             # 配置管理
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API服务
│   │   └── stores/         # 状态管理
│   └── public/
├── docker/                 # Docker配置
├── scripts/                # 部署脚本
└── docs/                   # 文档
```

## 核心模块说明

### 1. Agent系统

基于LLM的智能问答Agent，支持工具调用和多轮对话。

### 2. 检索系统

- **Query Expansion**: 查询扩展，生成多个查询变体
- **HyDE**: 假设文档嵌入，提升召回效果
- **Hybrid Retrieval**: 融合语义检索+关键词匹配
- **Cross-Encoder**: 精排阶段重排序

### 3. 记忆机制

- **短期缓存**: Redis存储热点查询结果
- **长期存储**: PostgreSQL存储历史数据

### 4. 工具封装

标准化工具接口，支持：
- 语义检索
- 关键词搜索
- 数据库查询
- 网页爬取
- RSS订阅

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/search | POST | 语义搜索 |
| /api/chat | POST | 智能问答 |
| /api/briefing | POST | 生成简报 |
| /api/hot-topics | GET | 热点话题 |
| /api/statistics/{metric} | GET | 统计数据 |

## 配置说明

编辑 `.env` 文件进行配置：

```env
# LLM配置
OPENAI_API_KEY=your-api-key
LLM_MODEL=gpt-3.5-turbo

# 数据库配置
POSTGRES_HOST=postgres
POSTGRES_PASSWORD=your-password

# Redis配置
REDIS_HOST=redis
```

## 部署脚本

```bash
# 启动服务
./scripts/start.sh

# 停止服务
./scripts/stop.sh

```
