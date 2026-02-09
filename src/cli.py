"""命令行入口"""

import asyncio
import sys
from pathlib import Path

import typer

from .config import get_config
from .processor.summary_gen import generate_summary

app = typer.Typer(name="paper-summary", help="论文摘要生成器")


@app.command()
def generate(
    paper_id: str = typer.Argument(..., help="arXiv论文ID"),
    download: bool = typer.Option(True, "--download/--no-download", help="是否下载PDF"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新下载"),
    no_pdf_llm: bool = typer.Option(False, "--no-pdf-llm", help="不使用LLM分析PDF"),
    api_key: str = typer.Option("", "--api-key", "-k", help="API密钥"),
):
    """生成论文摘要"""
    config = get_config()

    if api_key:
        import os

        os.environ["OPENAI_API_KEY"] = api_key

    typer.secho(f"正在处理论文: {paper_id}", fg=typer.colors.CYAN)

    try:
        summary = asyncio.run(
            generate_summary(
                paper_id=paper_id,
                download=download,
                force=force,
                use_pdf_llm=not no_pdf_llm,
            )
        )

        typer.secho("\n生成的摘要:", fg=typer.colors.GREEN)
        typer.echo("-" * 50)
        typer.echo(summary)
        typer.echo("-" * 50)

    except Exception as e:
        typer.secho(f"错误: {e}", fg=typer.colors.RED)
        # 如果是可重试的错误，给用户建议
        if (
            "ConnectionError" in str(e)
            or "timeout" in str(e).lower()
            or "502" in str(e)
            or "SSL" in str(e)
        ):
            typer.secho(
                "建议: 网络不稳定，可使用 --no-download 跳过下载",
                fg=typer.colors.YELLOW,
            )
        sys.exit(1)


@app.command()
def batch(
    input_file: str = typer.Argument(..., help="包含论文ID的文本文件"),
    output_dir: str = typer.Option("./summaries", "--output", "-o", help="输出目录"),
    api_key: str = typer.Option("", "--api-key", "-k", help="API密钥"),
):
    """批量处理论文ID列表"""
    from pathlib import Path as P

    if api_key:
        import os

        os.environ["OPENAI_API_KEY"] = api_key

    ids = []
    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)

    typer.secho(f"将处理 {len(ids)} 篇论文", fg=typer.colors.CYAN)

    output_path = P(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    async def process_all():
        for pid in ids:
            typer.secho(f"\n处理: {pid}", fg=typer.colors.YELLOW)
            try:
                summary = await generate_summary(paper_id=pid)
                (output_path / f"{pid}_summary.md").write_text(summary)
                typer.secho(f"  ✓ 完成", fg=typer.colors.GREEN)
            except Exception as e:
                typer.secho(f"  ✗ 失败: {e}", fg=typer.colors.RED)

    asyncio.run(process_all())
    typer.secho(f"\n所有摘要已保存到: {output_dir}", fg=typer.colors.GREEN)


@app.command()
def config_show():
    """显示当前配置"""
    config = get_config()

    typer.secho("当前配置:", fg=typer.colors.CYAN)

    typer.secho("\n文本生成:", fg=typer.colors.YELLOW)
    typer.echo(f"  Provider: {config.api.text.provider}")
    typer.echo(f"  Model: {config.api.text.model}")
    text_env = f"{config.api.text.provider.upper()}_API_KEY"
    typer.echo(f"  环境变量: {text_env}")

    typer.secho("\n图像/VL分析:", fg=typer.colors.YELLOW)
    typer.echo(f"  Provider: {config.api.vl.provider}")
    typer.echo(f"  Model: {config.api.vl.model}")
    vl_env = f"{config.api.vl.provider.upper()}_API_KEY"
    typer.echo(f"  环境变量: {vl_env}")

    typer.secho("\nAPI密钥:", fg=typer.colors.YELLOW)
    typer.echo(f"  {'✓ 已配置' if config.api.api_key else '✗ 未配置'}")

    typer.echo(f"  缓存目录: {config.paths.cache_dir}")
    typer.echo(f"PDF目录: {config.paths.pdf_dir}")
    typer.echo(f"摘要目录: {config.paths.summaries_dir}")


def main():
    app()


if __name__ == "__main__":
    main()
