"""进化体 · 核心逻辑层（可热重载）。

main.py 只负责启动、热重载检测与输入循环；所有业务逻辑（agent 构建、
命令处理、反思/进化、对话持久化）都在这里。

本模块可被 main.py 热重载：修改 core.py / prompts.py / mem.py / tools.py
后无需重启程序，下一轮对话自动加载新版代码。
只有 main.py 自身（最外层容器）的改动需要重启，但它已精简到几乎不需要改。

注意：模块内一律用 `import mem/prompts/tools` 形式访问，确保热重载后
引用到最新版本的模块，而不是旧的绑定。
"""

import os
from pathlib import Path

from deepagents import create_deep_agent

import mem
import prompts
import tools

ROOT = Path(os.getcwd())

# 每 N 轮用户对话后自动触发一次反思（可用环境变量覆盖）
AUTO_REFLECT_EVERY = int(os.environ.get("AUTO_REFLECT_EVERY", "5"))
# 单轮 agent 的最大图递归次数：允许更长的工具调用链
RECURSION_LIMIT = int(os.environ.get("RECURSION_LIMIT", "100"))


# ------------------------------------------------------------------
# Agent 工厂：每次构建都注入最新的系统提示词（记忆即时生效）
# ------------------------------------------------------------------


def build_agent(model, backend):
    """构建 agent。对话历史由 mem.py 从文件加载，故不使用 checkpointer。"""
    return create_deep_agent(
        model=model,
        system_prompt=mem.build_system_prompt(),
        backend=backend,
        tools=[tools.run_git],
    )


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------


def extract_text(message) -> str:
    """从 deepagents 的回复消息中稳健地提取文本（兼容 content_blocks / 字符串 / 列表）。"""
    content_blocks = getattr(message, "content_blocks", None)
    if content_blocks:
        parts = [
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        ]
        if parts:
            return "\n".join(parts)

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(t for t in texts if t)
    return str(content)


def run_reflection(agent, cfg) -> None:
    """显式反思：结合已落盘的对话历史，回顾并沉淀教训到记忆。"""
    history = mem.load_chat_history()
    result = agent.invoke(
        {"messages": history + [{"role": "user", "content": prompts.load_prompt("reflect")}]},
        config=cfg,
    )
    print(f"  反思 > {extract_text(result['messages'][-1])}")


def run_evolution(agent, cfg) -> None:
    """自进化：让 agent 读取自身代码与记忆，实施并记录改进。"""
    print("  正在读取自身代码与记忆，评估改进空间……")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": prompts.load_prompt("evolve")}]},
        config=cfg,
    )
    print(f"  进化总结 > {extract_text(result['messages'][-1])}")


# ------------------------------------------------------------------
# 单轮处理：命令 / 对话 / 自动反思
# ------------------------------------------------------------------


def handle_line(model, backend, state: dict, line: str) -> bool:
    """处理一行输入。返回 True 表示继续对话，False 表示退出。

    state: main.py 持有的可变状态（如 {"turn_count": n}），热重载 core 时
           不会被重置，保证计数跨重载连续。
    """
    cfg = {"recursion_limit": RECURSION_LIMIT}

    # ---------- 命令处理 ----------
    if line.startswith("/"):
        action = line.lower()
        if action in ("/exit", "/quit"):
            print("再见，期待与你再次进化。")
            return False
        if action == "/help":
            print(prompts.HELP_TEXT)
            return True
        if action == "/status":
            print(f"  轮次   : {state['turn_count']}")
            print(f"  记忆   :\n{mem.memory_status()}")
            return True
        if action == "/memory":
            print(mem.memory_status())
            return True
        if action == "/reset":
            mem.clear_chat_history()
            state["turn_count"] = 0
            print("  已清空对话历史与轮次（跨会话记忆保留，进化不受影响）")
            return True
        if action == "/reflect":
            run_reflection(build_agent(model, backend), cfg)
            return True
        if action == "/evolve":
            run_evolution(build_agent(model, backend), cfg)
            return True
        print(f"  未知命令: {line}（输入 /help 查看帮助）")
        return True

    # ---------- 普通对话轮次 ----------
    state["turn_count"] += 1
    agent = build_agent(model, backend)

    try:
        history = mem.load_chat_history()
        result = agent.invoke(
            {"messages": history + [{"role": "user", "content": line}]},
            config=cfg,
        )
        reply = extract_text(result["messages"][-1])
        mem.append_chat_message("user", line)
        mem.append_chat_message("assistant", reply)
        print(f"进化体 > {reply}")
    except Exception as exc:  # 容错：单轮失败不影响进程
        print(f"\n[本轮出错，已跳过] {type(exc).__name__}: {exc}")
        return True

    # ---------- 自动反思 ----------
    if state["turn_count"] % AUTO_REFLECT_EVERY == 0:
        print(f"\n[自动反思 · 第 {state['turn_count']} 轮]")
        try:
            run_reflection(build_agent(model, backend), cfg)
        except Exception as exc:
            print(f"  [反思失败，跳过] {type(exc).__name__}: {exc}")

    return True
