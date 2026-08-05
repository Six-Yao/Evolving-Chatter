"""
=================================================================
  进化体 · Agentic 持续对话系统  v3.0
=================================================================
v2.x → v3.0 的核心升级：
  1. 热重载     —— 每轮对话前检测代码文件变化，自动 reload；
                   改 core.py / prompts.py / mem.py / tools.py 无需重启
  2. 逻辑外置   —— 全部业务逻辑移入 core.py，main.py 精简为启动器
  3. 对话持久化 —— memory/chat_history.jsonl 落盘，重启后恢复上下文
  4. 自进化能力 —— run_git 受限 git 工具，改动可 commit 留痕

唯一需要重启的情形：修改 main.py 自身（但 main.py 已极小且稳定，
正常情况下几乎不需要改）。

运行：python main.py
"""

import config  # noqa: F401  确保 DEEPSEEK_API_KEY 最先被设置

import importlib
import os
import sys
from pathlib import Path

from deepagents.backends import FilesystemBackend
from langchain.chat_models import init_chat_model

import core
import mem
import prompts
import tools  # noqa: F401  确保启动即导入，纳入热重载监控

# 热重载监控顺序：依赖在前（core 依赖 prompts/mem/tools，最后加载）
WATCH_MODULES = ["prompts", "mem", "tools", "core"]
_last_mtime: dict[str, float] = {}


def hot_reload() -> list[str]:
    """检测被监控模块的 mtime 变化，有变化则 reload，返回已重载的模块名。"""
    changed = []
    for name in WATCH_MODULES:
        mod = sys.modules.get(name)
        path = getattr(mod, "__file__", None) if mod else None
        if not path:
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if name in _last_mtime and _last_mtime[name] != mtime:
            try:
                importlib.reload(sys.modules[name])
                changed.append(name)
            except Exception as exc:
                print(f"  [热重载失败] {name}: {type(exc).__name__}: {exc}（继续使用旧版本）")
        _last_mtime[name] = mtime
    return changed


def main() -> None:
    mem.ensure_memory_files()

    # 记录基线 mtime：启动这一轮不触发 reload
    for name in WATCH_MODULES:
        mod = sys.modules.get(name)
        path = getattr(mod, "__file__", None) if mod else None
        if path:
            try:
                _last_mtime[name] = os.path.getmtime(path)
            except OSError:
                pass

    model = init_chat_model(
        "deepseek-v4-flash",
        model_provider="deepseek",
        temperature=0.5,
        timeout=600,
        max_tokens=25000,
        streaming=True,
    )
    backend = FilesystemBackend(root_dir=str(Path(os.getcwd())))

    state = {"turn_count": 0}

    print(prompts.BANNER)
    print(f"  记忆目录: {mem.MEMORY_DIR}")
    print(f"  对话历史: {mem.CHAT_HISTORY_FILE.name}（持久化，重启不丢）")
    print(f"  热重载  : 改 core/prompts/mem/tools 即时生效，无需重启")
    print(f"  自动反思: 每 {core.AUTO_REFLECT_EVERY} 轮  |  递归上限: {core.RECURSION_LIMIT}")

    while True:
        # 读取用户输入（Ctrl+D / 管道 EOF 均视为退出）
        try:
            line = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见，期待与你再次进化。")
            break

        if not line:
            continue

        # 每轮先做热重载：代码/提示词有更新则下一句直接用新版
        changed = hot_reload()
        if changed:
            print(f"  [热重载] 已加载更新: {', '.join(changed)}")

        try:
            if not core.handle_line(model, backend, state, line):
                break
        except Exception as exc:  # 容错：单轮失败不影响进程
            print(f"\n[本轮出错，已跳过] {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
