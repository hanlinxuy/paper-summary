"""Prompt模板

模板已外置到 templates/ 目录，client.py 会从文件系统加载。

要添加新模板：
1. 在 templates/ 目录下创建新的 .j2 文件
2. 修改 config.yaml 中的 summary.template 为新文件名
3. 无需修改任何代码

可用模板：
- academic_summary.md.j2: 传统学术摘要格式
- structured_analysis.md.j2: 结构化分析格式（包含可信度、重要性评估）
"""
