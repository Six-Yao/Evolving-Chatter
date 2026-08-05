【自进化指令】
请完成一次完整的自我进化：
1. 读取 memory/ 目录下的所有记忆文件，回顾你的进化历史与教训；
2. 读取 main.py 与各模块，评估当前架构与提示词的优缺点（结构、可用性、进化能力）；
3. 提出并实施至少一项具体的改进 —— 可以是代码改进、系统提示词改进、或记忆整理；
   （修改文件前先 read_file 看原文，再用 write_file/edit_file 安全修改；对 memory/*.md 的追加请用 edit_file 在末尾追加，不要用 write_file 覆盖整个记忆文件）
4. 把这次进化追加记录到 memory/evolution_log.md（格式：时间 / 改了什么 / 为什么）；
5. 用 run_git 把改动 commit 留痕，并在 memory/change_log.md 补记备忘；
6. 最后用一段话总结这次进化。

注意：对代码的修改会在下次重启时生效；对 memory/ 的修改（含 memory/prompts/*.md）会立即在下一轮生效。
请确保所有修改是安全、可回退的。
