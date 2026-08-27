# prompt 记录目录

这个目录用来保存与 AI（Claude Code）交流的完整记录，防止对话历史因上下文压缩或会话结束而丢失。

## 目录结构

- `transcripts/` — 每个会话的最新完整记录（.jsonl 文件，每行一条消息）
  - 文件名是每次会话的唯一编号（session id）
  - 可以用记事本打开查看，推荐用 VS Code 打开更清晰
- `transcripts/压缩前快照/` — 每次上下文压缩前自动保存的历史快照（文件名带时间戳）
- `阶段记录/` — 每个工作阶段的可读小结

## 记录从哪来

Claude Code 会自动把每次对话保存到 `C:\Users\asus\.claude\projects\` 目录下，
本目录是这些记录的**备份副本**，方便随时查看和追溯。

## 更新方式（双重保障）

1. **自动备份（钩子）**——已在 Claude Code 中配置 PreCompact 和 SessionEnd 钩子：
   - 上下文压缩前 → 自动存一份带时间戳的完整快照到 `transcripts/压缩前快照/`
   - 会话结束时 → 自动更新 `transcripts/` 中的最新完整记录
   - 备份脚本：`C:\Users\asus\.claude\backup_zuoye_prompt.py`（配置在 `C:\Users\asus\.claude\settings.json`）
   - 覆盖范围：整个 Desktop\zuoye 下的所有会话（按路径中的 "zuoye" 过滤）
2. **手动小结**——每个工作阶段结束后，Claude 会在 `阶段记录/` 写一份可读的阶段小结
