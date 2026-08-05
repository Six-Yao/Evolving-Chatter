# 改动备忘（内部记录，非审计凭据）

> 每次对 main.py / config.py / 系统提示词 / 记忆结构的实质性改动，记录在这里，方便我跨会话回忆。
> 格式：`时间 / 文件 / 位置 / 改动前 → 改动后（关键片段） / 为什么`
> 重要声明：这是我自己写的备忘，我自己可以修改，它不能作为给任何人的验证凭据。
> 真正可验证的改动历史需要 git 之类的不可篡改机制，而那超出我当前的工具能力；在获得执行命令的能力之前，我无法自证改动。

- 2026-07-15 21:10 / main.py / REFLECT_PROMPT / 原："read_file 读取 → write_file 写入完整新内容"；现："read_file 了解已有条目 → edit_file 在末尾追加"，并禁止用 write_file 覆盖记忆文件 / 全量重写会随记忆增长覆盖丢失历史。
- 2026-07-15 21:10 / main.py / EVOLVE_PROMPT / 原："再用 write_file/edit_file 安全修改"；现："再用 write_file/edit_file 安全修改；对 memory/*.md 的追加请用 edit_file 在末尾追加，不要用 write_file 覆盖整个记忆文件" / 与 REFLECT 保持一致，防止进化时误覆盖记忆。
- 2026-07-15 21:30 / main.py / imports / 新增 shlex、subprocess、langchain_core.tools.tool / 为受限 git 工具做准备。
- 2026-07-15 21:30 / main.py / 新增 run_git 工具 + GIT_FORBIDDEN_SUBCOMMANDS 黑名单 / 机制层限定：仅 git、禁 shell 元字符、禁网络/历史重写子命令、cwd 固定项目根、30s 超时；create_deep_agent 的 tools 参数挂载 / 用户指出"你不应该自己给自己加这些功能吗"，遂动手给自己补上可验证改动的能力（git），而非把系统配置推给用户。
- 2026-07-15 21:30 / main.py / BASE_SYSTEM_PROMPT 进化准则 4-6 条 / 明确"改动先用 run_git 查状态与 diff，再 commit 留痕"，并声明 run_git 边界 / 让 git 成为进化流程的默认一环。
- 2026-07-15 21:40 / 架构 / main.py 从 405 行拆分为 prompts.py（提示词）+ mem.py（记忆层与对话持久化）+ tools.py（run_git）+ main.py（仅入口编排） / 用户指出"全部写进 main 以后会不会特别臃肿"——确会；提示词、记忆、工具、主循环职责不同，拆模块后各自演进。
- 2026-07-15 21:40 / 架构 / 对话持久化：放弃 InMemorySaver，新增 memory/chat_history.jsonl（JSONL 落盘），main.py 每次 invoke 前 load_chat_history()、invoke 后 append_chat_message()；/reset 清空历史 / 用户指出"重启后这轮记忆是不是全没了"——确会：InMemorySaver 是内存级，进程结束即清空；改文件持久化后重启可恢复上下文。
- 2026-07-15 21:40 / 命名 / memory.py 改名为 mem.py 并删除 / memory.py 与 memory/ 目录同名，import 会撞车；改名避免歧义。
- 2026-07-15 21:45 / 提示词外置 / 新增 memory/prompts/{base,reflect,evolve}.md；prompts.py 改为 load_prompt() 每次从文件读取、内置文本仅作兜底；mem.py / main.py 改用 load_prompt / 用户问"下一轮你再有什么修改我又得重启？"——提示词是高频改动，不该让用户反复重启；外置为文件后改提示词即时生效，只有代码改动才需重启。
- 2026-07-15 21:50 / 热重载架构 / 新增 core.py（全部业务逻辑：build_agent/extract_text/run_reflection/run_evolution/handle_line）；main.py 精简为启动器：热重载检测（每轮对比 prompts/mem/tools/core 的 mtime，变化则 importlib.reload，按依赖顺序）+ 输入循环；turn_count 由 main 持有 state 字典，重载不重置 / 用户继续追问"那下一轮改了代码我又得重启啊"——上一条方案的逻辑漏洞：改代码恰是我的核心工作，"只有改代码才需重启"等于还是让用户当运维。热重载后，改 core/prompts/mem/tools 全部即时生效，只有 main.py 自身（已极小且稳定）需重启。
- 2026-07-15 21:50 / 修复 bug / core.py run_reflection 用 prompts.load_prompt("reflect") / 原 main.py 第 89 行仍引用已删除的 prompts.REFLECT_PROMPT，会导致 AttributeError；重构时一并修复。
