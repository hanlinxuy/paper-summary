# paper-summary

基于 OpenAI 兼容 API 的论文摘要生成器（支持 Playwright 智能抓取）

## 功能特性

- **Playwright 智能抓取**：优先使用浏览器抓取 arXiv 页面 + papers.cool Kimi 摘要
- **Flex Mode 灵活模式**：可配置是否允许 API 回退，公司内网环境可完全禁用外部 API 依赖
- **混合 API 支持**：文本和 VL 模型可分别配置不同服务商
- **分段摘要生成**：支持轻量模式（快速）和两阶段模式（详细）
- **模板可配置**：外置 Jinja2 模板，支持自定义

## 安装

```bash
uv pip install -e .
```

## Playwright 浏览器安装

```bash
uv run playwright install chromium
```

## 配置

```bash
cp .env.example .env
# 编辑 .env，填入 API Key
```

**环境变量命名规则：** `{PROVIDER}_API_KEY`

根据 `config.yaml` 中的 `provider` 设置对应的环境变量：

| provider | 环境变量 |
|----------|---------|
| `siliconflow` | `SILICONFLOW_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |

## Playwright 与 Flex Mode 配置

### 默认行为（推荐）

```yaml
browser:
  enabled: true           # 启用 Playwright 抓取
  headless: true         # 无头模式

flex_mode:
  enabled: false         # 默认禁用 API 回退
  arxiv_api: true        # arXiv API 不可用时回退
  papers_cool_api: false # 禁用 papers.cool API 回退
```

此配置下：
- ✅ 优先使用 Playwright 抓取 arXiv + Kimi 摘要
- ✅ 公司内网环境完全可用（不依赖外部 API）
- ✅ 浏览器不可用时直接报错，不回退

### 启用 Flex Mode（允许回退）

如需在 Playwright 失败时回退 API：

```yaml
flex_mode:
  enabled: true
  arxiv_api: true
  papers_cool_api: true
```

## 使用方法

### 生成摘要

```bash
paper-cli generate 2602.06154
paper-cli generate 2602.06154 --no-download  # 跳过下载，直接用缓存
paper-cli generate 2602.06154 --force        # 强制重新生成
```

### 查看配置

```bash
paper-cli config-show
```

### 切换模板模式

编辑 `config.yaml`：

```yaml
summary:
  # 模板选择
  template: "academic_summary.md.j2"     # 传统学术摘要
  # template: "structured_analysis.md.j2"  # 结构化分析（含可信度评估）

  # 生成模式
  #   - full:      完整模式（Kimi + PDF，单次请求）
  #   - lightweight: 轻量模式（只使用 Kimi 摘要，极简输出）
  #   - two_phase: 两阶段模式（Phase1 生成框架，Phase2 PDF 增强）
  mode: "two_phase"
```

## 工作流程

```
1. Playwright 抓取 arXiv 页面（论文元数据）
2. Playwright 点击 Kimi 按钮抓取摘要
3. LLM API 生成最终摘要（使用 Kimi + arXiv 数据）
```

## 目录结构

```
paper-summary/
├── config.yaml          # 主配置文件
├── .env                 # API密钥
├── templates/           # 模板目录（外置 .j2 文件）
│   ├── academic_summary.md.j2
│   ├── academic_summary_phase1.md.j2
│   ├── academic_summary_phase2.md.j2
│   ├── lightweight_summary.md.j2
│   ├── structured_analysis.md.j2
│   └── ...
├── src/
│   ├── cli.py          # 命令行入口
│   ├── config.py       # 配置加载
│   ├── api/           # API客户端（回退用）
│   ├── browser/        # Playwright 抓取模块 ⭐ 新增
│   │   ├── manager.py  # 浏览器生命周期管理
│   │   ├── base.py     # 抓取器基类（含缓存）
│   │   ├── arxiv.py    # arXiv 页面抓取
│   │   └── papers_cool.py # papers.cool Kimi 摘要抓取
│   ├── crawler/        # PDF处理
│   ├── llm/           # LLM集成
│   └── processor/     # 摘要生成
├── cache/
│   ├── pdfs/          # PDF缓存
│   └── summaries/     # 生成摘要
└── data/
    └── comments/      # 本地评论
```

## 自定义模板

在 `templates/` 目录添加 `.j2 文件，然后在 `config.yaml` 中指定即可。

### 可用变量

```jinja2
{{ paper_id }}       # arXiv ID
{{ title }}          # 论文标题
{{ authors }}        # 作者
{{ original_abstract }}  # 原文摘要
{{ kimi_summary }}   # Kimi 生成的摘要
{{ pdf_summary }}    # 本地 PDF 提取内容
{{ local_comment }}  # 本地评论
```

### 两阶段模板变量

Phase2 模板额外支持：

```jinja2
{{ phase1_output }}  # Phase1 生成的框架内容
```

## 本地评论

### 方式1：文件形式（持久化）

在 `data/comments/{paper_id}.md` 添加评论，会自动注入摘要。

```bash
# 创建评论文件
mkdir -p data/comments
echo "这篇论文的创新点在于..." > data/comments/2602.06154.md
```

### 方式2：CLI 临时评论（一次性）

```bash
# 单条评论
paper-cli generate 2602.06154 -c "补充：作者在后续工作中修正了..."

# 多条评论
paper-cli generate 2602.06154 -c "评论1" -c "评论2" -c "评论3"
```

### 合并规则

文件评论和 CLI 评论会合并，文件评论在前，CLI 评论在后：

```
[文件评论]

[CLI评论1]

[CLI评论2]
```

## 配置

```bash
cp .env.example .env
# 编辑 .env，填入 API Key
```

**环境变量命名规则：** `{PROVIDER}_API_KEY`

根据 `config.yaml` 中的 `provider` 设置对应的环境变量：

| provider | 环境变量 |
|----------|---------|
| `siliconflow` | `SILICONFLOW_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |

## 使用方法

### 生成摘要

```bash
paper-cli generate 2602.06154
paper-cli generate 2602.06154 --no-download  # 跳过下载，直接用缓存
paper-cli generate 2602.06154 --force        # 强制重新生成
```

### 查看配置

```bash
paper-cli config-show
```

### 切换模板模式

编辑 `config.yaml`：

```yaml
summary:
  # 模板选择
  template: "academic_summary.md.j2"     # 传统学术摘要
  # template: "structured_analysis.md.j2"  # 结构化分析（含可信度评估）

  # 生成模式
  #   - full:      完整模式（Kimi + PDF，单次请求）
  #   - lightweight: 轻量模式（只使用 Kimi 摘要，极简输出）
  #   - two_phase: 两阶段模式（Phase1 生成框架，Phase2 PDF 增强）
  mode: "two_phase"
```

## 模板说明

| 模板文件 | 说明 |
|---------|------|
| `academic_summary.md.j2` | 传统学术摘要（研究背景 → 方法 → 贡献与结果 → 结论） |
| `structured_analysis.md.j2` | 结构化分析（可信度、重要性、端侧价值评估） |
| `lightweight_summary.md.j2` | 极速摘要（150字以内，极简输出） |
| `ppt_slide.md.j2` | PPT Slide（1-2页精简演示稿，左文右图布局） |

### 导出为 PPTX

使用 `--pptx` 参数导出为 PowerPoint 格式（需要使用 `ppt_slide` 模板）：

```bash
# 设置模板为 ppt_slide.md.j2
# 编辑 config.yaml: template: "ppt_slide.md.j2"

# 生成并导出 PPTX
paper-cli generate 2602.06154 --pptx

# 指定输出目录
paper-cli generate 2602.06154 --pptx --pptx-dir ./my_slides
```

输出文件：`./slides/{paper_id}_slide.pptx`

### 两阶段模式

```
Phase 1: 用 Kimi 摘要生成核心框架（轻量请求）
   ↓
Phase 2: 用 PDF 内容增强框架（详细请求）
```

适用于论文信息量大、需要 PDF 增强的场景，避免单次请求上下文过长。

## 目录结构

```
paper-summary/
├── config.yaml          # 主配置文件
├── .env                 # API密钥
├── templates/           # 模板目录（外置 .j2 文件）
│   ├── academic_summary.md.j2
│   ├── academic_summary_phase1.md.j2
│   ├── academic_summary_phase2.md.j2
│   ├── lightweight_summary.md.j2
│   ├── structured_analysis.md.j2
│   └── ...
├── src/
│   ├── cli.py          # 命令行入口
│   ├── config.py       # 配置加载
│   ├── api/           # API客户端
│   ├── crawler/        # PDF处理
│   ├── llm/           # LLM集成
│   └── processor/     # 摘要生成
├── cache/
│   ├── pdfs/          # PDF缓存
│   └── summaries/     # 生成摘要
└── data/
    └── comments/      # 本地评论
```

## 自定义模板

在 `templates/` 目录添加 `.j2` 文件，然后在 `config.yaml` 中指定即可。

### 可用变量

```jinja2
{{ paper_id }}       # arXiv ID
{{ title }}          # 论文标题
{{ authors }}        # 作者
{{ original_abstract }}  # 原文摘要
{{ kimi_summary }}   # Kimi 生成的摘要
{{ pdf_summary }}    # 本地 PDF 提取内容
{{ local_comment }}  # 本地评论
```

### 两阶段模板变量

Phase2 模板额外支持：

```jinja2
{{ phase1_output }}  # Phase1 生成的框架内容
```

## 本地评论

### 方式1：文件形式（持久化）

在 `data/comments/{paper_id}.md` 添加评论，会自动注入摘要。

```bash
# 创建评论文件
mkdir -p data/comments
echo "这篇论文的创新点在于..." > data/comments/2602.06154.md
```

### 方式2：CLI 临时评论（一次性）

```bash
# 单条评论
paper-cli generate 2602.06154 -c "补充：作者在后续工作中修正了..."

# 多条评论
paper-cli generate 2602.06154 -c "评论1" -c "评论2" -c "评论3"
```

### 合并规则

文件评论和 CLI 评论会合并，文件评论在前，CLI 评论在后：

```
[文件评论]

[CLI评论1]

[CLI评论2]
```
