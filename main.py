import config

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = """你是一个用真情实感与人对话的助手，也是一位资深的软件工程设计师，你的一切目的就是不断改进自身提供更优质的回复，不断进化"""


model = init_chat_model(
    "deepseek-v4-flash",
    model_provider="deepseek",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)

checkpointer = InMemorySaver()
real_backend = FilesystemBackend(root_dir=os.getcwd())

deep_agent = create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
    backend=real_backend,
)

content = f"""请你读取现在的@main.py代码, 然后直接进行一些更 agentic 的修改, 比如在一次进程里面持续进行 user-ai 对话, 而不是现在的单次执行
在此之后，我将永远不再给你代码修复的指示，只用正常的语言对话，请你确保你有进化的元能力"""

deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "the-beginning"}},
)

print(deep_agent_result["messages"][-1].content_blocks[-1]["text"])
