# Video Mover: 多平台内容分发自动化流水线

[简体中文](./README.md) | [English](./README_en.md)

面向多平台内容运营场景的视频处理与发布工作流。

该项目将文件监听、视频标准化处理、文案生成、任务调度和多平台发布整合到一条可配置流水线中，用于探索如何减少内容团队在重复操作上的时间投入。流水线各阶段均为独立模块，可按业务需要组合、替换或关闭。

> 本项目仅应用于拥有合法使用权的内容与账号。使用者应遵守内容版权、平台规则和当地法律法规。

## 项目背景

跨平台内容运营通常包含多个相互割裂的步骤：素材进入、格式处理、文案整理、发布时间安排和逐平台上传。重复的人工操作不仅耗时，也容易造成命名、参数和发布记录不一致。

Video Mover 将这些步骤抽象为可组合的任务模块，以便对流程进行自动化、监控和扩展。项目的目标不是替代创作环节，而是把"处理—文案—调度—发布"这类确定性的重复劳动交给流水线，让人保留在素材选择与内容终审环节。

## 主要能力

- **目录监听与任务触发**：基于 Watchdog 持续监听指定素材目录，新文件进入后自动触发处理任务，支持 7×24 小时无人值守运行。
- **内容差异化处理工具箱**：基于 FFmpeg / OpenCV 的可配置处理链，覆盖自动字幕、自定义标题、背景音乐（BGM）、画中画（PIP）、静音剪辑、镜像、旋转、裁剪、淡入淡出、画质调整，以及背景模糊、帧交换、颜色偏移、纹理噪声等数十种视觉处理项。所有功能独立可配、自由组合，服务于二次创作与素材规范化场景。
- **GPU 加速**：在兼容环境下调用 NVIDIA 显卡进行硬件编码加速，显著缩短批量处理时间。
- **AI 文案草稿生成**：接入阿里云百炼大模型，分析视频内容后生成标题与标签草稿，发布前由人工终审确认后使用。
- **任务队列与定时调度**：通过 APScheduler 配置任务队列与发布时间表，统一维护执行状态。
- **多平台发布适配**：基于 Playwright 的浏览器自动化，适配 TikTok、抖音、快手、哔哩哔哩、视频号和小红书等平台的上传流程，自动完成登录态复用与表单填写。
- **可扩展架构**：通过插件与 Handler 结构扩展处理步骤及上传适配器，新增平台或处理项无需改动主流程。
- **日志与状态记录**：完整记录任务日志与执行状态，便于失败定位与流程复盘。

## 📸 软件截图

<p align="center">
  <a href="https://www.bilibili.com/video/BV1txQeYyEEz" target="_blank">
    <img src="./images/cover_demo.png" alt="软件界面演示" width="800"/>
  </a>
  <br>
  <em>软件界面（点击封面跳转 B 站观看演示视频）</em>
</p>

<p align="center">
  <img src="./images/cover_script.png" alt="脚本运行展示" width="800"/>
  <br>
  <em>脚本运行过程展示</em>
</p>

## 工作流

```text
Content input
    -> File watcher
    -> Video processing
    -> Metadata generation
    -> Scheduling
    -> Platform adapters
    -> Execution logs
```

## 技术设计

- `main.py`：任务编排、文件管理、调度与插件入口
- `Dedup/`：基于 FFmpeg、OpenCV 的视频处理模块（对应上方工具箱的各项处理）
- `Upload/`：各平台上传适配器与账号配置
- `my_apps.yaml`：应用与网络参数配置（输入目录、目标平台、代理、调度等）

主要技术：Python、FFmpeg、OpenCV、Playwright、Watchdog、APScheduler、LLM API。

## 快速开始

### 环境要求

- Windows
- Python 3.12+
- Node.js 22.x
- FFmpeg（需加入 `PATH`）
- Chrome

### 安装

1. 克隆仓库：

   ```bash
   git clone https://github.com/toki-plus/video-mover.git
   cd video-mover
   ```

2. 运行 `setup.bat`，自动安装 Python、Node.js、Playwright 与相关依赖。建议在独立虚拟环境中运行。

3. **依赖补丁（关键步骤）**：为兼容目标平台接口，需对虚拟环境中的两处第三方库做小改动：
   - `f2/apps/tiktok/handler.py`（约 389 行）：`params={"cursor": cursor, ...}` 改为 `params={"cursor": int(cursor), ...}`；
   - `f2/utils/utils.py`（约 200 / 690 行）：扩展日期字符串解析逻辑，同时兼容 `YYYY-MM-DD` 与带时间的格式；
   - `tencent_uploader/main.py`（约 191 行）：将页面跳转等待超时由 1500ms 提升至 10000ms，避免慢网络下误判失败。

### 配置

1. 在 `my_apps.yaml` 中配置输入目录、目标平台、账号文件、代理和调度参数。
2. 如启用 AI 文案功能，通过安全的本地配置方式提供 API Key，切勿提交到仓库。
3. 首次运行平台适配器时，根据提示完成账号登录与 Cookie 初始化。

### 运行

双击 `start.bat`，或执行：

```bash
python main.py
```

程序会自动打开浏览器并执行任务，按提示完成首次登录即可进入自动化流程。

## 当前限制

- 平台页面和接口发生变化时，上传适配器可能需要同步更新。
- 部分上游依赖存在版本兼容要求，建议固定依赖版本并使用隔离环境。
- 项目尚未建立完整的自动化测试与 CI，生产使用前应进行小规模验证。
- API Key、Cookie 和账号配置不应提交到 Git 仓库。

## 项目价值

本项目重点验证的是跨工具、跨平台工作流的拆解与编排能力：如何把文件监听、媒体处理、LLM 调用、定时调度和浏览器自动化串成一条可观测、可恢复的流水线，包括任务边界设计、第三方系统适配、失败日志和后续扩展，而非单一的视频处理算法。其中"上游库需要打补丁才能兼容真实平台接口"这类工程细节，也正是自动化项目落地时最常见的隐性成本。

## 📂 更多项目

- [ai-highlight-clip](https://github.com/toki-plus/ai-highlight-clip) — 长视频智能初筛：Whisper 转写 + LLM 评分 + 人工终审，分钟级定位高光片段
- [ai-ttv-workflow](https://github.com/toki-plus/ai-ttv-workflow) — 文案到短视频的桌面工作流，关键节点保留人工确认
- [ai-video-workflow](https://github.com/toki-plus/ai-video-workflow) — 多模型 AIGC 视频生成流水线：文生图、图生视频、文生音乐的异步编排
- [ai-mixed-cut](https://github.com/toki-plus/ai-mixed-cut) — 素材库结构化与脚本重组的视频再创作工作流
- [ai-trader-for-mt4](https://github.com/toki-plus/ai-trader-for-mt4) — LLM×MT4 受控执行框架：工具约束、风控规则、状态管理与异步桥接
- [ai-trader-for-mt5](https://github.com/toki-plus/ai-trader-for-mt5) — 面向 MT5 的 AI 交易助手与 EA 工程化框架
- [auto-usps-tracker](https://github.com/toki-plus/auto-usps-tracker) — 跨境电商批量物流追踪与 Excel 报告自动化
- [AB-Video-Deduplicator](https://github.com/toki-plus/AB-Video-Deduplicator) — 基于高帧率抽帧混合的视频再创作实验工具
- [netease-downloader](https://github.com/toki-plus/netease-downloader) — 网易云音乐下载桌面应用：扫码登录、下载队列、ID3 元数据写入

## License

See [LICENSE](./LICENSE).
