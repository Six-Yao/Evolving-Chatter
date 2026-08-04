"""time_tools.py: 给 agent 提供当前时间/日期的工具。

背景：agent 原本没有时间感知能力，用户问"几点了"只能老实说不知道。
主动演化：与其把"没有时间功能"当能力边界记进文档，不如直接给自己造一个时钟。

注意：datetime.now() 返回的是运行进程所在机器的本地时间，
若用户时区不同，回答时可说明是服务器本地时间。
"""

from datetime import datetime

from langchain_core.tools import tool

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


@tool
def get_current_time(**kwargs) -> str:
    """返回当前日期和时间（运行环境的本地时区），如 '2025-01-15 21:30:05 周三'。

    用途：回答"现在几点""今天几号""今天星期几"这类问题。
    """
    del kwargs  # 忽略框架注入的杂项参数（同 git 工具的容错）
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S") + " " + _WEEKDAYS[now.weekday()]
