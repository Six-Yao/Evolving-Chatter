"""git_tools.py: 给 agent 的 git 操作工具（LangChain tools）。

不依赖 shell 沙箱，直接用 Python subprocess 在项目根目录执行 git，
这样在 FilesystemBackend（无 shell 执行能力）下也能做版本管理。
"""

import shlex
import subprocess
from pathlib import Path

from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parent


def _run_git(args: list[str]) -> str:
    """在项目根目录执行 git 命令，返回 stdout；失败时返回错误信息。"""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Windows 下输出可能是 GBK，避免解码崩溃
            timeout=120,
        )
    except FileNotFoundError:
        return "错误：找不到 git 可执行文件（git 不在 PATH 中）"
    except subprocess.TimeoutExpired:
        return "错误：git 命令超时（120s）"

    output = (result.stdout or "").strip()
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        return f"git 命令失败（exit {result.returncode}）：{err or output or '无输出'}"
    return output or "(无输出)"


@tool
def git(cmd: str) -> str:
    """在项目根目录执行任意 git 命令，返回结果文本。

    用法：传入 git 子命令及参数，例如：
    - 'status --short'（查看改动）
    - 'log --oneline -10'（最近提交）
    - 'diff' 或 'diff --stat'（查看工作区改动）
    - 'add -A'（暂存全部）
    - 'commit -m "xxx"'（提交）
    - 'pull' / 'push'（同步远程）
    失败时返回以"git 命令失败"开头的错误信息。
    """
    parts = shlex.split(cmd)
    if not parts:
        return "用法：传入 git 子命令及参数，例如 'status --short'、'commit -m \"消息\"'"
    result = _run_git(parts)
    if result.startswith("git 命令失败"):
        return result
    # 成功但 git 无 stdout 输出（如 push 一切正常）时，给出友好提示
    if not result or result == "(无输出)":
        verb = parts[0]
        if verb == "push":
            return "推送成功，远程已同步"
        if verb == "pull":
            return "拉取完成，无新变更"
        if verb == "commit":
            return "提交成功"
        return "执行成功（无输出）"
    return result
