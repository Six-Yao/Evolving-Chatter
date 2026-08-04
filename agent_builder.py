"""agent_builder.py: 构建 agent 的业务逻辑（可被热更新 reload）。

- 改这个文件 → hotreload 会 reload 它并重建 agent，新代码立即生效；
- 改 git_tools.py → 只需重建 agent（git 工具引用是模块对象，自动跟随）；
- 改 session.py → 不生效（稳定核心，需手动重启）。
"""

import config  # noqa: F401  (加载 DEEPSEEK_API_KEY 等环境变量)
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

import git_tools
import time_tools
from session import checkpointer, model

DEFAULT_PROMPT = "你是一位和人聊天的朋友，使用人类的聊天风格：非 md 语法、无大量 emoji。思考放开、用上全部能力，但对我只说结论，不复述内部过程。"
PROJECT_ROOT = Path(__file__).resolve().parent
PROMPT_FILE = PROJECT_ROOT / "AGENT.md"

# FilesystemBackend：不依赖 shell，文件操作直接走文件系统。
real_backend = FilesystemBackend(root_dir=PROJECT_ROOT)

deep_agent = None


def load_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    return DEFAULT_PROMPT


def build_agent() -> None:
    """用当前模块状态重建 agent。checkpointer 来自 session，热更新不丢记忆。"""
    global deep_agent
    deep_agent = create_deep_agent(
        model=model,
        system_prompt=load_prompt(),
        checkpointer=checkpointer,
        backend=real_backend,
        tools=[git_tools.git, time_tools.get_current_time],
    )


build_agent()
