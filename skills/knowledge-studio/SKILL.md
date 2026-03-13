---
name: knowledge-studio
description: 基于 Obsidian Vault 笔记的知识处理与创新工坊。用于笔记归纳、跨笔记组合创新、苏格拉底式思辨讨论、个性化学习路径生成、工具创意生成。当用户想要基于已有笔记进行深度思考、产生新想法、进行思辨对话、学习新知识或生成工具创意时触发。
---

# Knowledge Studio - 知识处理与创新工坊

基于你的 Obsidian Vault 笔记，提供知识处理、组合创新、思辨讨论、学习辅助和工具生成的能力。

## 核心功能

### 1. 笔记洞察 (Insight)
查看知识库概况，发现笔记间的关联。

```bash
python3 scripts/knowledge_engine.py --action list
```

### 2. 组合创新 (Combine)
基于多篇笔记进行组合，产生新想法、新项目、新概念。

```bash
python3 scripts/knowledge_engine.py --action combine --topic "AI Agent"
python3 scripts/knowledge_engine.py --action combine --keywords "Claude,代码,工程"
```

### 3. 思辨伙伴 (Discuss)
基于笔记内容，作为苏格拉底式的思辨伙伴进行深度讨论。

```bash
python3 scripts/knowledge_engine.py --action discuss --topic "AI时代工程师的价值"
```

### 4. 学习教练 (Learn)
基于已有笔记，生成个性化学习路径和知识测验。

```bash
python3 scripts/knowledge_engine.py --action learn --topic "MCP协议"
```

### 5. 工具生成 (Tool)
基于笔记中的代码片段和工具思路，生成新的工具创意。

```bash
python3 scripts/knowledge_engine.py --action tool --requirement "批量处理Markdown文件的脚本"
```

## 使用流程

### 组合创新流程

1. 用户提出想要探索的主题或方向
2. 运行 `--action combine` 查找相关笔记
3. 基于返回的笔记列表和关键概念，进行AI组合思考
4. 生成创新点子、项目想法、新概念
5. 将创新成果保存到 Obsidian Vault

### 思辨讨论流程

1. 用户提出想要深入讨论的话题
2. 运行 `--action discuss` 获取相关笔记上下文
3. 基于返回的上下文，进入苏格拉底式对话模式
4. 可以质疑、反问、提出反例、挑战假设
5. 目的是通过对话深化思考，而非给出答案

### 学习辅助流程

1. 用户提出想要学习的主题
2. 运行 `--action learn` 分析已有知识基础
3. 识别知识缺口，生成学习路径
4. 基于笔记内容生成练习题和测验
5. 跟踪学习进度

### 工具生成流程

1. 用户描述工具需求
2. 运行 `--action tool` 查找相关笔记和代码片段
3. 基于已有知识生成工具设计
4. 输出可执行的代码或脚本
5. 保存到工具库

## 数据存储

- 知识来源：`/root/.openclaw/workspace/obsidian-vault/`
- 创新成果：保存到 `03-Articles/Innovations/` 或 `07-Tools/`
- 讨论记录：保存到 `02-Conversations/`
- 学习计划：保存到 `08-Learning/`

## 注意事项

- 所有处理基于本地 Obsidian Vault，无需网络
- 创新成果自动同步到 GitHub
- 可以跨多个主题进行组合创新
- 思辨讨论会引用具体笔记内容作为论据
