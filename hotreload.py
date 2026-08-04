"""hotreload.py: 文件监控 + 热更新（Flask 风格，不重启进程）。

- 任意 .md 变化：重建 agent（新提示词生效），对话记忆保留；
- 任意 .py 变化（除 session.py）：reload 对应模块后重建 agent，对话记忆保留；
- session.py 是稳定核心，改它需要手动重启。
"""

import importlib
import os
import sys
from pathlib import Path

import agent_builder

PROJECT_ROOT = Path(__file__).resolve().parent
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".idea", ".vscode", "node_modules", "dist", "build"}

file_sigs: dict[str, int] = {}


def scan_signatures() -> dict[str, int]:
    """扫描项目里所有 .py / .md 文件，返回 {相对路径: mtime_ns}，跳过忽略目录。"""
    sigs: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fname in filenames:
            if not fname.endswith((".py", ".md")):
                continue
            full = Path(dirpath) / fname
            try:
                sigs[str(full.relative_to(PROJECT_ROOT))] = full.stat().st_mtime_ns
            except (ValueError, OSError):
                continue
    return sigs


def _reload_module(rel: str) -> None:
    """按相对路径 reload 一个模块；session.py 特殊处理，main.py 不重载。"""
    if rel == "session.py":
        print("（session.py 是稳定核心，改动需手动重启才会生效）")
        return
    if rel == "main.py":
        print("（main.py 改动建议手动重启，自动热重载已跳过）")
        return
    # 普通 .py 文件重载
    name = rel[:-3].replace(os.sep, ".")
    if name in sys.modules:
        importlib.reload(sys.modules[name])
    else:
        importlib.import_module(name)

def check_hot_reload() -> bool:
    """扫描文件变化并热更新：reload 变化的模块 + 重建 agent。

    - 变化的 .py（除 session.py / main.py）：reload 模块；
    - 变化的 .md：只触发重建（提示词变化）；
    - 最后统一重建 agent，对话记忆（checkpointer）保留。
    """
    global file_sigs
    sigs = scan_signatures()
    # 首次运行时，直接保存签名并返回，不触发更新
    if not file_sigs:
        file_sigs = sigs
        return False

    changed = [rel for rel, mtime in sigs.items() if file_sigs.get(rel) != mtime]
    file_sigs = sigs
    if not changed:
        return False

    # 1) reload 变化的 .py 模块（session.py / main.py 由 _reload_module 内部特殊处理）
    for rel in changed:
        if rel.endswith(".py"):
            _reload_module(rel)
        # .md 无需 reload，只参与下面的 agent 重建

    # 2) 用最新模块状态重建 agent
    agent_builder.build_agent()
    print(f"（热更新：{', '.join(changed)} → 已重建 agent）")
    return True
