"""main.py: 聊天入口（薄壳）。业务逻辑在 agent_builder / hotreload / session 里。

热更新（Flask 风格）：改任意 .py / .md 都不会重启进程，
而是 reload 对应模块 + 重建 agent，对话记忆（session.checkpointer）全程保留。
"""

import config  # noqa: F401  (加载 DEEPSEEK_API_KEY 等环境变量)
import sys

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

# 热更新：改任意 .md 会重建 agent（记忆保留）；改任意 .py 会自动重启进程让新代码生效。
# 项目可以拆成任意多个 .py / .md 文件，都会纳入监控，不锁死在 main.py。
DEFAULT_PROMPT = "你是一位和人聊天的朋友，使用人类的聊天风格：非 md 语法、无大量 emoji。思考放开、用上全部能力，但对我只说结论，不复述内部过程。"
PROJECT_ROOT = Path(__file__).resolve().parent
PROMPT_FILE = PROJECT_ROOT / "AGENT.md"
IGNORED_DIRS = {".git", ".venv", "__pycache__", ".idea", ".vscode", "node_modules", "dist", "build"}

model = init_chat_model(
    "deepseek-v4-flash",
    model_provider="deepseek",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)

checkpointer = InMemorySaver()  # 全局复用：热更新后对话记忆不丢
real_backend = LocalShellBackend(root_dir=os.getcwd())

deep_agent = None
file_sigs: dict[str, float] = {}


def load_prompt() -> str:
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()
    return DEFAULT_PROMPT


def scan_signatures() -> dict[str, float]:
    """扫描项目里所有 .py / .md 文件，返回 {相对路径: mtime}，跳过忽略目录。"""
    sigs: dict[str, float] = {}
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fname in filenames:
            if not fname.endswith((".py", ".md")):
                continue
            full = Path(dirpath) / fname
            try:
                sigs[str(full.relative_to(PROJECT_ROOT))] = full.stat().st_mtime
            except (ValueError, OSError):
                continue
    return sigs


def build_agent() -> None:
    global deep_agent, file_sigs
    deep_agent = create_deep_agent(
        model=model,
        system_prompt=load_prompt(),
        checkpointer=checkpointer,
        backend=real_backend,
    )
    file_sigs = scan_signatures()


build_agent()

content = f""""""

deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "the-beginning"}},
)


def extract_text(content_blocks) -> str:
    """从 content_blocks 里把所有 text 片段拼起来（跳过 reasoning / tool_call 等）。"""
    parts = []
    for block in content_blocks:
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def chat_once(user_input: str) -> None:
    """发送一条用户消息，流式打印回复。"""
    try:
        for chunk, _meta in agent_builder.deep_agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config={"configurable": {"thread_id": THREAD_ID}},
            stream_mode="messages",
        ):
            # 只打印 AI 的回复文本，跳过工具结果等中间消息，
            # 否则 read_file/edit_file 的返回内容会刷屏（如 "Successfully replaced..."）。
            if getattr(chunk, "type", "") != "ai":
                continue
            text = extract_text(getattr(chunk, "content_blocks", None) or [])
            if text:
                sys.stdout.write(text)
                sys.stdout.flush()
    except KeyboardInterrupt:
        # 允许在 AI 回复过程中打断
        print("\n（已打断）")
    except Exception as exc:  # noqa: BLE001
        print(f"\n[出错了: {exc}]")


def main() -> None:
    print("输入 exit / quit / q / 退出 结束，Ctrl+C 也能退出。")
    print("我可以读取和修改当前目录下的文件，比如：帮我看看 main.py 然后改点什么。")
    print("改 .py / .md 都会热更新：新代码立即生效、对话记忆保留（不再重启进程）。")
    print()

    while True:
        hotreload.check_hot_reload()

        try:
            user_input = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print("再见！")
            break

        print("AI > ", end="", flush=True)
        chat_once(user_input)
        print("\n")


if __name__ == "__main__" and not getattr(sys, "_hot_reload_guard", False):
    main()
