import config  # noqa: F401  (加载 DEEPSEEK_API_KEY 等环境变量)

import os
import sys

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

SYSTEM_PROMPT = """"""


model = init_chat_model(
    "deepseek-v4-flash",
    model_provider="deepseek",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)

checkpointer = InMemorySaver()
real_backend = LocalShellBackend(root_dir=os.getcwd())

deep_agent = create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
    backend=real_backend,
)

content = f""""""

deep_agent_result = deep_agent.invoke(
    {"messages": [{"role": "user", "content": content}]},
    config={"configurable": {"thread_id": "the-beginning"}},
)

print(deep_agent_result["messages"][-1].content_blocks[-1]["text"])
