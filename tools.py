"""进化体 · 自定义工具集。

拆分自 main.py v2.0：目前包含受限 git 执行工具 run_git 与系统时钟工具 get_time。
边界写死在机制里，不靠自觉。
"""

import os
import shlex
import subprocess
from pathlib import Path

from langchain_core.tools import tool

ROOT = Path(os.getcwd())

# git 子命令黑名单：网络操作 / 重写历史 / 全局配置，一律禁止
GIT_FORBIDDEN_SUBCOMMANDS = {
    "push", "fetch", "pull", "clone", "remote", "config",
    "filter-branch", "gc", "prune", "submodule",
}


@tool
def run_git(command: str) -> str:
    """在项目根目录内执行 git 命令，用于查看与记录改动。

    用法示例：
      run_git("status")                  查看工作区状态
      run_git("diff")                    查看未提交改动
      run_git("log --oneline -10")       查看最近 10 条提交
      run_git("add main.py")             暂存改动
      run_git("commit -m 说明")           提交改动（本地，不会 push）

    安全约束（代码层面强制，非自觉）：
      - 只接受以 git 开头的命令；
      - 禁止 ; | & > < $ ` 等 shell 元字符，防止命令注入；
      - 禁止网络与历史重写类子命令（push/fetch/pull/clone/remote/config 等）；
      - 工作目录固定为项目根；
      - 30 秒超时。
    """
    stripped = command.strip()
    if not stripped.startswith("git "):
        return "错误：只允许 git 命令（如 git status）"
    if any(c in stripped for c in ";|&><`$"):
        return "错误：命令包含不允许的 shell 元字符"
    parts = shlex.split(stripped)
    if len(parts) < 2 or parts[0] != "git":
        return "错误：命令必须以 git 开头"
    subcmd = parts[1]
    if subcmd in GIT_FORBIDDEN_SUBCOMMANDS:
        return f"错误：子命令 {subcmd} 被禁止（仅限本地版本控制操作）"
    try:
        result = subprocess.run(
            parts,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output.strip() or f"（退出码 {result.returncode}，无输出）"
    except subprocess.TimeoutExpired:
        return "错误：命令执行超时（>30s）"
    except Exception as exc:
        return f"执行失败：{exc}"
    """获取当前系统时间（本地时区），返回精确的日期与时刻。

    用于回答"现在几点了"这类问题。系统时钟是可靠来源，
    优于用 git 提交时间戳等间接推断（后者有误差且依赖近期有提交）。
    """
    from datetime import datetime

    now = datetime.now().astimezone()
    tz = now.strftime("%Z") or f"UTC{now.strftime('%z')}"
    return now.strftime("%Y-%m-%d %H:%M:%S") + f" {tz}"
