# paper-summary

基于 OpenAI 兼容 API 的论文摘要生成器

## 功能特性

- 自动获取 arXiv 论文元数据和 PDF
- 从 papers.cool 提取 Kimi 生成的摘要
- 支持本地 Markdown 评论注入
- 基于 LLM 生成结构化中文摘要
- 支持 OpenAI、Anthropic 和 SiliconFlow API 配置

## 安装

```bash
# 使用 uv 安装
uv pip install -e .
```

## 配置

1. 复制配置模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 填入 API Key（根据你的接口类型选择）
   - OpenAI 兼容接口（OpenAI, SiliconFlow, TogetherAI 等）：`OPENAI_API_KEY`
   - Anthropic 兼容接口：`ANTHROPIC_API_KEY`

3. 可选：编辑 `config.yaml` 调整配置

## 使用方法

### 生成单篇论文摘要

```bash
python -m src.cli generate 2602.06154
python -m src.cli generate 2602.06154 --no-download
python -m src.cli generate 2602.06154 --force
```

### 批量处理

```bash
python -m src.cli batch papers.txt -o ./summaries
```

### 查看配置

```bash
python -m src.cli config-show
```

## 目录结构

```
paper-summary/
├── config.yaml          # 主配置文件
├── .env                 # API密钥 (需手动创建)
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

## 配置文件说明

`config.yaml` 支持以下配置：

```yaml
api:
  provider: "siliconflow"  # 或 "openai", "anthropic"
  siliconflow:
    base_url: "https://api.siliconflow.cn/v1"
    model: "deepseek-ai/DeepSeek-V3.2"
    vl_model: "Qwen/Qwen2-VL-7B-Instruct"
  anthropic:
    base_url: "https://api.minimaxi.com/anthropic/v1"
    model: "MiniMax-M2.1"
  openai:
    base_url: "https://api.openai.com/v1"
    model: "gpt-4o"
```

## 本地评论

在 `data/comments/` 目录下添加 `{paper_id}.md` 文件，可注入自定义评论。

示例：`data/comments/2602.06154.md`

```markdown
# 我的评论

这篇论文的创新点在于...
```
