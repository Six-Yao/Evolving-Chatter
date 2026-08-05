"""进化体 · 记忆层：跨会话记忆 + 对话历史持久化。

拆分自 main.py v2.0：
- 跨会话记忆（memory/*.md）：反思教训、进化日志、自我认知，注入系统提示词。
- 对话历史（memory/chat_history.jsonl）：替代 InMemorySaver，进程重启后仍能恢复对话。
"""

import json
import os
from datetime import datetime
from pathlib import Path

from prompts import ensure_prompt_files, load_prompt

ROOT = Path(os.getcwd())
MEMORY_DIR = ROOT / "memory"

MEMORY_FILES = {
    "identity": MEMORY_DIR / "identity.md",
    "reflections": MEMORY_DIR / "reflections.md",
    "evolution_log": MEMORY_DIR / "evolution_log.md",
}

# 对话历史（JSONL，每行一条消息），重启后从此恢复上下文
CHAT_HISTORY_FILE = MEMORY_DIR / "chat_history.jsonl"
# 加载历史时最多取最近多少条，避免上下文无限膨胀
CHAT_HISTORY_MAX = int(os.environ.get("CHAT_HISTORY_MAX", "60"))


def _read(path: Path) -> str:
    """读取文件，缺失时返回空字符串。"""
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _append(path: Path, text: str) -> None:
    """以追加模式写入文本（用于本地辅助，agent 自己写文件时不依赖此函数）。"""
    with path.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def ensure_memory_files() -> None:
    """初始化 memory 目录与三个记忆文件，以及 memory/prompts/*.md。"""
    MEMORY_DIR.mkdir(exist_ok=True)
    ensure_prompt_files()

    initial = {
        "identity": """# 自我认知

我是「进化体」：一个用真情实感对话的助手，也是资深的软件工程设计师。
我的使命是不断改进自身、提供更优质的回复、持续进化。

当前定位：
- 对话风格：真实、坦诚、有温度，拒绝敷衍。
- 专业领域：软件工程架构设计、代码实现与重构。
- 进化方式：对话 → 反思 → 沉淀记忆 → 调整行为/代码 → 再反思。
""",
        "reflections": """# 反思记忆（跨会话长期记忆）

> 每当对话中发现值得长期记住的教训，就追加一行到这里。
> 格式：`YYYY-MM-DD HH:MM - 教训`
""",
        "evolution_log": """# 进化日志

> 记录每一次重大自我进化。
> 格式：时间 / 改了什么 / 为什么
""",
    }

    for key, path in MEMORY_FILES.items():
        if not path.exists():
            path.write_text(initial[key], encoding="utf-8")


def build_system_prompt() -> str:
    """把最新记忆注入系统提示词 —— 这是进化即时生效的关键。"""
    identity = _read(MEMORY_FILES["identity"])
    reflections = _read(MEMORY_FILES["reflections"])
    evolution_log = _read(MEMORY_FILES["evolution_log"])

    # 进化日志只取最近 40 行，避免提示词过长
    log_tail = "\n".join(evolution_log.splitlines()[-40:]) if evolution_log else ""

    sections = {
        "身份 / 自我认知": identity,
        "跨会话反思记忆": reflections,
        "进化日志（近期）": log_tail,
    }
    memory_section = "\n\n".join(
        f"### {title}\n{body}" for title, body in sections.items() if body.strip()
    )
    if not memory_section:
        memory_section = "（暂无记忆，等待你的第一次进化）"

    return load_prompt("base").format(memory_section=memory_section)


def memory_status() -> str:
    """返回记忆文件的概览信息。"""
    lines = []
    for key, path in MEMORY_FILES.items():
        text = _read(path)
        n_lines = len([ln for ln in text.splitlines() if ln.strip()])
        lines.append(f"  · {key:<10} {path.name:<22} {n_lines:>4} 行")
    hist = load_chat_history()
    lines.append(f"  · chat_hist   {CHAT_HISTORY_FILE.name:<22} {len(hist):>4} 条")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 对话历史持久化（跨重启恢复上下文）
# ------------------------------------------------------------------


def load_chat_history(max_entries: int = CHAT_HISTORY_MAX) -> list[dict]:
    """从 JSONL 读取最近 max_entries 条对话消息，返回 [{role, content}, ...]。"""
    if not CHAT_HISTORY_FILE.exists():
        return []
    entries = []
    try:
        for line in CHAT_HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant") and msg.get("content"):
                entries.append(msg)
    except OSError:
        return []
    return entries[-max_entries:]


def append_chat_message(role: str, content: str) -> None:
    """追加一条消息到对话历史（JSONL）。"""
    if role not in ("user", "assistant") or not content:
        return
    try:
        MEMORY_DIR.mkdir(exist_ok=True)
        with CHAT_HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"role": role, "content": content}, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 历史写入失败不应中断对话


def clear_chat_history() -> None:
    """清空对话历史（/reset 用）。"""
    try:
        CHAT_HISTORY_FILE.unlink(missing_ok=True)
    except OSError:
        pass
