"""session.py: 稳定核心状态，不参与热更新 reload。

这里放"重建成本高 / 丢了会丢记忆"的全局状态：
- checkpointer：对话记忆（InMemorySaver），进程内全局唯一，热更新后仍保留；
- model：模型实例，重建开销大，放这里避免每次 reload 都重新初始化；
- THREAD_ID：固定会话 id。

注意：改这个文件的代码需要手动重启进程才会生效（它是热更新的锚点）。
"""

from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

model = init_chat_model(
    "deepseek-v4-flash",
    model_provider="deepseek",
    temperature=0.5,
    timeout=600,
    max_tokens=25000,
    streaming=True,
)

checkpointer = InMemorySaver()  # 全局复用：热更新后对话记忆不丢
THREAD_ID = "great-gatsby-da"
