# AI 同声传译助手

本地 AI 同声传译桌面应用。用户观看 YouTube、Zoom、TED 等外语内容时，实时采集系统音频，经 ASR 转写与 LLM 翻译，以字幕形式呈现中文译文。

## 产品定位

帮助用户降低语言门槛，在观看外语演讲、技术分享、国际会议或网课时，同步理解内容要点，无需暂停或事后查词。

## MVP 范围

| 包含 | 暂不包含 |
|------|----------|
| 系统音频采集 | TTS 语音播报 |
| Faster-Whisper ASR 转写 | 多语言切换 |
| Ollama LLM 翻译为中文 | 云服务 |
| PySide6 字幕叠加显示 | 用户登录 |

## 技术栈

| 组件 | 选型 | 用途 |
|------|------|------|
| 运行时 | Python 3.11 | 应用语言 |
| GUI | PySide6 | 桌面界面与字幕 overlay |
| ASR | Faster-Whisper | 本地流式语音转写 |
| 翻译 | Ollama | 本地 LLM 英 → 中翻译 |
| 并发 | asyncio | 异步流水线，避免阻塞 UI |

## 架构概览

采用**四层模块化架构**，UI 与业务逻辑彻底分离：

```
ui/  →  app/  →  core/  →  services/
表现层    装配层    领域层    基础设施
```

核心数据流：

```
系统音频 → AudioStage → ASRStage → TranslationStage → SubtitleBuffer → 字幕 UI
                              ↑
                        CorrectionStage（预留）
```

详细设计见 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**，包含：

- 完整目录结构
- 类图（Mermaid）
- 异步流水线时序与数据流
- 各模块职责说明
- 扩展点与 MVP 实现优先级

## 目录结构

```
AI-/
├── app/              # 入口、依赖注入、生命周期
├── ui/               # PySide6 界面（零业务逻辑）
├── core/             # 领域模型、Pipeline、接口契约
├── services/         # 音频采集、Whisper、Ollama 实现
├── infrastructure/   # 配置、日志、Qt↔asyncio 桥接
├── resources/        # 静态资源
├── tests/
└── docs/
    └── ARCHITECTURE.md
```

## 环境要求

- Python 3.11
- Windows 10/11（MVP 优先支持 WASAPI 系统内录）
- [Ollama](https://ollama.com) 已安装并运行，且已 pull 翻译模型（如 `qwen2.5:7b`）
- 建议 NVIDIA GPU（Faster-Whisper 可选 CUDA 加速；CPU 亦可运行）

## 快速开始

> 应用代码开发中，以下为预期用法。

```bash
# 克隆仓库
git clone <repository-url>
cd AI-

# 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 确认 Ollama 运行中
ollama serve
ollama pull qwen2.5:7b

# 启动应用
python -m app
```

## 使用场景

1. **YouTube / B 站外语视频**：开启系统内录，屏幕底部实时显示中文字幕。
2. **Zoom / Teams 国际会议**：采集会议音频，同步阅读中文翻译字幕。
3. **TED / 技术分享**：LLM 翻译保留术语上下文，降低理解成本。

## 设计原则

- **模块化**：音频、ASR、翻译均面向接口编程，便于替换实现。
- **UI 与业务分离**：UI 只负责展示；Pipeline 不依赖 Qt。
- **异步优先**：asyncio 流水线 + 线程池执行 Whisper 推理，主线程保持流畅。
- **本地隐私**：音频与文本不出本机。
- **渐进增强**：MVP 打通主链路，修正引擎 / TTS / 多语言后续迭代。

## 开发路线

- [x] 架构设计文档
- [ ] Phase 1：项目骨架 + UI 框架
- [ ] Phase 2：音频采集 + ASR
- [ ] Phase 3：Ollama 翻译 + 字幕联动
- [ ] Phase 4：稳定性与错误处理

## 许可证

待定。

## 贡献

欢迎提交 Issue 与 Pull Request。架构变更请同步更新 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。
