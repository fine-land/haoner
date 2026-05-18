# 🤖 HAONER - AI-Powered Agent

> **⚠️ 纯 AI 开发警告 ⚠️**  
> 此项目完全由 AI 开发完成，未经人类程序员审查。  
> 代码质量、安全性和正确性需自行验证。

---

## 🌟 项目简介

**Haoner** 是一个基于 Anthropic API 构建的智能代理系统，支持工具调用、上下文压缩等高级功能。

### 📋 当前特性

| 功能 | 状态 | 说明 |
|------|------|------|
| Anthropic API 集成 | ✅ 已完成 | 支持 DeepSeek Anthropic 兼容接口 |
| 工具调用 | ✅ 已完成 | 支持 terminal 等工具 |
| 上下文压缩 | ✅ 已完成 | 五种压缩技术优化长对话 |
| 彩色 CLI | ✅ 已完成 | 美观的终端界面 |
| Mock 模式 | ✅ 已完成 | 支持离线测试 |
| 安全机制 | ✅ 已完成 | 工作目录验证、危险命令检测、代码执行限制 |

### 🚀 未来规划

- [ ] 支持更多工具（文件操作、网络请求等）
- [ ] 添加记忆系统
- [ ] 支持多轮对话总结
- [ ] 集成向量数据库
- [ ] 添加 Web UI 界面
- [ ] 支持多模型切换
- [ ] 可配置的安全策略
- [ ] 沙箱执行环境

---

## 🛠️ 快速开始

### 环境要求

- Python 3.11+
- Anthropic API 密钥（或 DeepSeek Anthropic 兼容 API）

### 安装步骤

```bash
# 克隆项目
git clone <repository-url>
cd haoner

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install anthropic openai
```

### 配置说明

1. 复制示例配置文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的 API 密钥：
```bash
# .env 文件内容
LLM_PROVIDER=anthropic
API_KEY=your-api-key-here
API_BASE=https://api.deepseek.com/anthropic
MODEL=deepseek-v4-pro
```

### 启动方式

```bash
# 交互式聊天
./haoner chat

# 单查询模式
./haoner chat -q "你的名字是什么？"

# 查看可用工具
./haoner chat --list-tools

# 查看版本
./haoner version
```

---

## 📁 项目结构

```
haoner/
├── haoner              # 启动脚本
├── cli.py              # 命令行界面
├── main.py             # 主入口
├── .env                # 环境配置
├── .env.example        # 配置示例
├── .gitignore          # Git 忽略规则
├── venv/               # 虚拟环境
├── agent/              # 核心代理模块
│   ├── agent_loop.py       # Agent 循环逻辑
│   ├── anthropic_client.py # Anthropic 客户端
│   ├── context_compression.py # 上下文压缩
│   ├── prompt_builder.py   # 提示词构建
│   ├── llm_factory.py      # LLM 工厂
│   ├── security.py         # 安全机制
│   └── system_prompt.py    # 系统提示词
└── tools/              # 工具模块
    ├── model_tools.py      # 工具定义
    ├── registry.py         # 工具注册
    └── terminal_tool.py    # 终端工具
```

---

## 📝 使用示例

### 交互式聊天
```
╔════════════════════════════════════════════════════════════════╗
║                      HAONER - AI Agent CLI                      ║
╚════════════════════════════════════════════════════════════════╝

💡 Type "exit" or "quit" to quit

You: 你好！
🔄 Thinking...

Haoner: 你好！👋 我是 Haoner，你的 AI 助手。有什么我可以帮你的吗？
```

### 执行命令
```
You: 运行命令 ls -l
🔄 Thinking...

Haoner: 执行命令: ls -l
工具执行结果:
total 40
-rwxr-xr-x  1 user  group  1024 May 18 10:00 haoner
-rw-r--r--  1 user  group  2048 May 18 10:00 cli.py
...
```

---

## �️ 安全机制

Haoner 内置了多层次的安全机制，保护系统免受意外或恶意的命令执行影响。

### 安全检查项目

| 检查类型 | 说明 | 默认状态 |
|----------|------|----------|
| 工作目录验证 | 阻止访问项目目录外的路径 | ✅ 启用 |
| 危险命令检测 | 阻止 `rm -rf`, `dd`, `mkfs` 等 | ✅ 启用 |
| 代码执行检测 | 阻止 `python -c`, `eval`, `exec` 等 | ✅ 启用 |
| 网络访问检测 | 阻止 `curl`, `wget`, `ssh` 等 | ❌ 默认阻止 |
| 路径遍历检测 | 阻止 `../`, `./../../` 等 | ✅ 启用 |
| Git 命令白名单 | 仅允许安全的只读 git 命令 | ✅ 启用 |

### 安全级别

| 级别 | 说明 | 示例命令 |
|------|------|----------|
| `safe` | 完全允许 | `ls`, `git status` |
| `elevated` | 需要提升权限 | `sudo rm` |
| `dangerous` | 潜在危险 | `rm -rf` |
| `blocked` | 阻止执行 | `curl`, `cd ..` |

### 配置安全设置

```python
from tools.terminal_tool import set_security_settings

# 默认设置（最安全）
set_security_settings(
    allow_network=False,    # 阻止网络访问
    allow_code_exec=False,  # 阻止代码执行
    allow_git_write=False   # 阻止 Git 写操作
)

# 按需开启
set_security_settings(allow_network=True)  # 允许网络访问
```

---

## �� 配置选项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `LLM_PROVIDER` | LLM 提供商 | `anthropic` |
| `API_KEY` | API 密钥 | - |
| `API_BASE` | API 基础 URL | `https://api.anthropic.com` |
| `MODEL` | 模型名称 | `claude-sonnet-4-20250514` |
| `MAX_TOKENS` | 最大令牌数 | `8192` |
| `TEMPERATURE` | 温度参数 | `1.0` |
| `MAX_TURNS` | 最大对话轮数 | `30` |

---

## 📄 许可证

MIT License

---

*Built with 🤖 AI*
