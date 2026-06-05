# Phase 2 — 实时音频 + ASR 目标与任务说明

> 状态：需求明确阶段（Phase 1 已回滚至 `407ae2d`）  
> 核心议题：**实时性 vs 准确性** 的可量化权衡  
> 范围：音频采集 → 语音识别 → 英文字幕显示（翻译留给 Phase 3）

---

## 1. Phase 2 要解决的问题

用户观看外语内容时，需要**尽快、尽量准确**地在屏幕上看到正在说的内容。Phase 2 只打通「听 → 识别 → 显示原文」，不接入 Ollama 翻译。

| 用户感知 | 技术含义 |
|----------|----------|
| 「跟得上说话节奏」 | 首词延迟低、partial 更新流畅 |
| 「看得懂在说什么」 | 最终文本 WER 可接受、少截断、少粘连 |
| 「字幕不晃眼」 | partial 不闪烁、换行自然 |

Phase 1 已验证 UI 骨架与事件链路；Phase 2 用**真实音频**替换 demo 字幕循环。

---

## 2. 成功标准（可验收）

### 2.1 功能完成度

- [ ] Windows WASAPI 系统环回采集，16 kHz mono
- [ ] 启动/停止 Pipeline，状态指示正确
- [ ] 英文语音 → 屏幕显示 ASR 原文（可先不做中文翻译）
- [ ] 支持 partial（进行中）与 final（定稿）两种更新
- [ ] `demo_mode = false` 时走 live 路径；保留 demo 模式便于 UI 调试
- [ ] core/services 层单测覆盖新增模块

### 2.2 延迟指标（在清晰英文演讲、GPU 可用条件下）

| 指标 | 目标 A：偏实时 | 目标 B：均衡（推荐默认） | 目标 C：偏准确 |
|------|----------------|--------------------------|----------------|
| 首词上屏 | ≤ 800 ms | ≤ 1.5 s | ≤ 2.5 s |
| partial 刷新间隔 | 50–100 ms | 100–200 ms | 300–500 ms |
| 定稿相对语音结束 | ≤ 500 ms | ≤ 800 ms | ≤ 1.2 s |
| 主观感受 | 「几乎同步」 | 「稍慢但可跟读」 | 「像延迟字幕，但字更对」 |

> 测量方法：日志打点 `speech_onset → first_partial_ui`；测试音频用固定 WAV + 人工标注首词时间。

### 2.3 准确率指标（英文，无背景音乐）

| 指标 | 目标 A | 目标 B（默认） | 目标 C |
|------|--------|----------------|--------|
| 句级 WER（final） | ≤ 25% | ≤ 15% | ≤ 10% |
| 可接受场景 | 日常对话、清晰旁白 | TED / 技术分享 | 专业术语讲座 |
| 不可接受 | 词头大面积丢失、整句语义反转 | 同上 | 同上 |

---

## 3. 实时性 vs 准确性：根本矛盾

```
                    低延迟 ◄────────────────────────► 高准确
                         │                              │
    Sherpa 20M 流式      │  ★ 首词快，字常错            │
    Whisper tiny + 短窗  │       ★ 折中偏快             │
    Whisper small + 流式 │              ★ 推荐默认       │
    Whisper medium 整段  │                         ★ 最准最慢
```

### 3.1 上次迭代教训（已回滚代码的经验）

| 方案 | 实时性 | 准确性 | 结论 |
|------|--------|--------|------|
| Sherpa zipformer 20M mobile | partial 约 2 s 首 token；50 ms 喂入 | 词头丢失、粘连、截断严重 | **不适合作为默认**，可作「极速预览」档 |
| Whisper 2 s 固定分块 | 首句 ≥ 2 s | 明显优于 20M | 准确但不够「直播感」 |
| 双区字幕 + 逐词 UI | 不改善 ASR，只改善感知 | — | 属于 **Phase 2b（体验层）**，依赖 ASR 质量 |

**结论**：没有单一引擎能同时满足「<1 s 首词」和「<15% WER」。Phase 2 必须提供**可配置档位**，而不是押注一种方案。

---

## 4. 推荐策略：三档配置 Profile

通过 `resources/default_config.toml` 中的 `profile` 或等效字段切换，避免用户改多个参数。

### Profile `realtime` — 偏实时

```toml
[asr]
engine = "sherpa"          # 或 whisper tiny + 极短窗
model_size = "tiny"
# 首词优先，接受较高 WER
```

- 适用：快速扫内容、不在意错字
- 风险：词头丢失、英文专有名词错误

### Profile `balanced` — 均衡（**Phase 2 默认**）

```toml
[asr]
engine = "whisper"
model_size = "small"
device = "auto"            # 有 GPU 用 CUDA

[utterance]
# 话轮切分 + partial 窗口（Phase 2 实现）
partial_interval_ms = 300
partial_tail_sec = 1.0
utterance_end_silence_ms = 600
max_phrase_sec = 0         # 不强制长句换行，靠标点/停顿
```

- 适用：YouTube / TED / 会议（MVP 主场景）
- 预期：首词 1–2 s，WER ~12–18%（small + GPU）

### Profile `accurate` — 偏准确

```toml
[asr]
engine = "whisper"
model_size = "medium"      # 或 small + 更长上下文
compute_type = "float16"   # GPU

[utterance]
utterance_end_silence_ms = 800
partial_interval_ms = 500
```

- 适用：术语多、口音重、可接受 2–4 s 延迟
- 预期：WER ~8–12%，CPU 上可能不可实时

---

## 5. Phase 2 范围边界

### 5.1 本阶段必须做（In Scope）

| 模块 | 交付物 |
|------|--------|
| 音频 | `SystemAudioCapture`（WASAPI loopback）、重采样 16 kHz mono、环回设备选择 |
| VAD / 切句 | 话轮 START/END；Silero（首选）+ Energy 回退 |
| ASR | **Whisper 为主路径**；Sherpa 作为可选 `engine`（文档标明精度限制） |
| Pipeline | `StreamingPipelineOrchestrator` 或扩展 `PipelineOrchestrator`：feed → partial → final |
| 字幕 | `SubtitleManager`：partial UPDATE / final 定稿；基础换行（标点 + 停顿） |
| UI | 连接 live 事件；可选双区（上文白 / 当前灰）作为 **2b**，不阻塞 2a |
| 配置 | profile 三档 + 延迟/ASR 参数集中文档化 |
| 测试 | 环回 mock、VAD 切句、partial/final 事件、WER 基准脚本 |

### 5.2 本阶段不做（Out of Scope → Phase 3+）

- Ollama 翻译与中文字幕
- TTS、多语言切换、设置中心 UI
- CorrectionEngine 实际上线
- 云端 ASR、用户登录

### 5.3 体验增强（Phase 2b，可选并行）

上次回滚前的 UI 需求，**在 ASR 档位确定后再做**：

1. 双区字幕：上文（白）+ 正在说（灰，最新词高亮）
2. 逐词揭示（`word_by_word`）
3. 仅逗号/句号/短停顿换行，禁止长句强制换行
4. partial 防抖、16 ms UI 刷新

---

## 6. 任务拆分与优先级

### Phase 2a — 最小可用 live 链路（必须先完成）

```
P0  音频采集 SystemAudioCapture + loopback 设备配置
P0  VAD 话轮切分（Silero + Energy 回退）
P0  WhisperASRService（partial + final，线程池推理）
P0  StreamingOrchestrator 串联 audio → VAD → ASR → SubtitleEvent
P0  UI 显示 live 英文字幕（单行/多行即可）
P0  profile=balanced 默认配置 + demo_mode 开关
P1  延迟/WER 基准测试脚本 + 文档记录实测值
P1  背压：RingBuffer 上限、队列丢弃策略
```

**2a 验收**：播放固定英文 WAV，屏幕持续输出 partial，停顿后输出 final，停止后清空。

### Phase 2b — 体验与可选引擎（2a 稳定后）

```
P1  SubtitleManager：标点/停顿换行、partial 合并防抖
P1  双区 + 逐词 UI（SubtitleViewModel 增强）
P2  Sherpa 流式引擎（engine=sherpa，profile=realtime）
P2  GPU/CUDA 自动检测与配置提示
P2  环回静音诊断（rms 告警、设备选择指引）
```

**2b 验收**：三档 profile 切换后，延迟与 WER 符合第 2 节表格量级。

---

## 7. 架构决策（已拍板）

| 决策 | 选择 | 理由 |
|------|------|------|
| Phase 2 默认 ASR | Faster-Whisper **small** | 架构文档原定；精度明显优于 Sherpa 20M |
| 流式形态 | VAD 话轮 + partial 循环 / 流式 feed | 比固定 2 s 盲切更自然 |
| 翻译 | Phase 3 再接入 | 降低 Phase 2 复杂度；先验证 ASR 质量 |
| UI 语言 | Phase 2 显示 **英文原文** | 翻译字段预留，SubtitleLine 结构不变 |
| 提交策略 | 2a / 2b 分 commit | 便于回滚（避免再次 `git clean` 丢失） |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 无 GPU，Whisper small 过慢 | 延迟超标 | 降级 tiny / 提示用户；profile 自动建议 |
| 环回采到错误设备 | 全静音或识别 garbage | rms 诊断 + `loopback_device` 配置 |
| partial 闪烁 | 体验差 | merge_partial_text、最小更新间隔 |
| 过早切句 | 截断（如 `EXP`） | `utterance_end_silence_ms` ≥ 600 |
| 过晚切句 | 延迟累积 | `max_utterance_sec` 上限 + 标点切句 |

---

## 9. 与 Phase 3 的衔接

Phase 2 输出的 `SubtitleLine.source_text`（英文）在 Phase 3 经 `TranslationStage` 填入 `translated_text`（中文）。Partial 翻译策略（跳翻 / 句末再翻）在 Phase 3 设计，**不影响 Phase 2 ASR 接口**。

---

## 10. 下一步行动

1. **确认默认 profile**：建议 `balanced`（Whisper small + VAD partial）
2. **确认 Phase 2 字幕语言**：Phase 2 仅英文 / 还是必须中文（若必须中文则提前拉 Phase 3 翻译）
3. **按 P0 任务启动 Phase 2a 实现**

---

*维护：实现过程中若调整延迟/精度目标，请同步更新本文档第 2 节实测表格。*
