# AI 同声传译助手

桌面同声传译应用：采集系统音频，本地 Whisper 实时转写英文，经阿里云 DashScope（Qwen-MT）翻译为中文，以字幕叠加显示。

## 产品定位

帮助用户降低语言门槛，在观看外语演讲、技术分享、国际会议或网课时，同步理解内容要点，无需暂停或事后查词。

## 当前能力

| 包含 | 暂不包含 |
|------|----------|
| WASAPI 系统内录（Windows） | TTS 语音播报 |
| Faster-Whisper 流式 ASR（partial + final） | 多语言切换 |
| DashScope Qwen-MT 英 → 中翻译（`final_only`） | 用户登录 |
| 双区字幕：灰色英文 partial / 白色中文 final | 本地 Ollama 翻译 |

## 技术栈

| 组件 | 选型 | 用途 |
|------|------|------|
| 运行时 | Python 3.11+ | 应用语言 |
| GUI | PySide6 + qasync | 桌面界面与 asyncio 事件循环 |
| 音频 | PyAudioWPatch | WASAPI Loopback 系统内录 |
| VAD | Silero（可选）/ Energy | 话轮切分 |
| ASR | Faster-Whisper | 本地英文转写 |
| 翻译 | DashScope Qwen-MT | 云端低延迟机器翻译 |
| HTTP | httpx | 异步翻译 API 客户端 |

## 架构概览

```
ui/  →  app/  →  core/  →  services/
表现层    装配层    领域层    基础设施
```

核心数据流（Phase 2 + 3）：

```
系统音频 → VAD 话轮 → Whisper partial/final → SubtitleManager
                                              ↓
                                    TranslationCoordinator（final_only）
                                              ↓
                                    DashScope Qwen-MT → 中文字幕 UI
```

- **partial**：灰色显示英文 ASR 中间结果  
- **final**：句末定稿后异步翻译，白色显示中文（失败时保留英文）

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)、[docs/PHASE3.md](docs/PHASE3.md)。

## 目录结构

```
AI-/
├── app/              # 入口、依赖注入、生命周期
├── ui/               # PySide6 界面
├── core/             # Pipeline、字幕、翻译协调
├── services/         # 音频、Whisper、VAD、DashScope 翻译
├── infrastructure/   # 配置、日志、Qt↔asyncio 桥接
├── resources/        # default_config.toml、测试音频
├── scripts/          # benchmark_translate.py 等
├── tests/
└── docs/
```

## 环境要求

- Python 3.11+
- Windows 10/11（WASAPI 系统内录）
- 阿里云百炼 [DashScope API Key](https://help.aliyun.com/zh/model-studio/get-api-key)（翻译）
- 建议 NVIDIA GPU（Faster-Whisper 可选 CUDA；CPU 亦可运行）
- 可选：`torch`（启用 Silero VAD；未安装时自动降级为 Energy VAD）

## 快速开始

```powershell
# 克隆并进入项目
git clone <repository-url>
cd AI-

# 虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 设置 DashScope API Key（环境变量，勿写入配置文件或 Git）
$env:DASHSCOPE_API_KEY = "sk-你的密钥"

# 启动应用
python -m app
```

持久化环境变量（Windows 用户级）：

```powershell
[Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "sk-你的密钥", "User")
```

设置后需重新打开终端或 IDE。

## 配置

主配置文件：[resources/default_config.toml](resources/default_config.toml)

| 区块 | 说明 |
|------|------|
| `[asr]` | Whisper 模型大小、语言、VAD |
| `[utterance]` | 话轮切分、partial 间隔与窗口 |
| `[translation]` | DashScope provider、`final_only`、模型 `qwen-mt-lite` |
| `[subtitle]` | 字号、颜色、历史行数 |

翻译相关默认值：

```toml
[translation]
enabled = true
provider = "dashscope_mt"
mode = "final_only"
dashscope_model = "qwen-mt-lite"
```

未设置 `DASHSCOPE_API_KEY` 时，翻译自动降级为仅显示英文 ASR，不影响识别。

## 测试翻译时延

```powershell
cd D:\AI-
$env:DASHSCOPE_API_KEY = "sk-你的密钥"
python scripts/benchmark_translate.py
```

典型单次 en→zh 延迟约 **220–450 ms**（视网络与句长而定）。

## 使用场景

1. **YouTube / B 站外语视频**：系统内录 + 底部实时中文字幕。  
2. **Zoom / Teams 国际会议**：采集会议音频，同步阅读中文翻译。  
3. **TED / 技术分享**：句末定稿后快速出中文，partial 阶段可看英文预览。

## 设计原则

- **模块化**：音频、ASR、翻译均面向接口，便于替换实现。  
- **UI 与业务分离**：Pipeline 不依赖 Qt。  
- **异步优先**：Whisper 在线程池运行，翻译在独立 asyncio Task，不阻塞 ASR。  
- **隐私分层**：音频与 ASR 在本地处理；**final 英文文本**会发送至 DashScope 翻译。  
- **渐进增强**：默认 `final_only` 降低延迟与 API 用量。

## 开发路线

- [x] 架构设计文档  
- [x] Phase 1：项目骨架 + UI 框架  
- [x] Phase 2：音频采集 + Whisper ASR（balanced：VAD + partial/final）  
- [x] Phase 3a：DashScope 翻译 + 中文字幕（`final_only`）  
- [ ] Phase 3b：partial 中文预览、双语字幕等（可选）  
- [ ] Phase 4：稳定性与错误处理  

## 许可证

待定。

## 贡献

欢迎提交 Issue 与 Pull Request。架构或 Phase 变更请同步更新 `docs/` 下相关文档。
