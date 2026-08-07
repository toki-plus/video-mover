# Video Mover

面向多平台内容运营场景的视频处理与发布工作流。

该项目将文件监听、视频标准化处理、文案生成、任务调度和多平台发布整合到一条可配置流水线中，用于探索如何减少内容团队在重复操作上的时间投入。

> 本项目仅应用于拥有合法使用权的内容与账号。使用者应遵守内容版权、平台规则和当地法律法规。

## 项目背景

跨平台内容运营通常包含多个相互割裂的步骤：素材进入、格式处理、文案整理、发布时间安排和逐平台上传。重复的人工操作不仅耗时，也容易造成命名、参数和发布记录不一致。

Video Mover 将这些步骤抽象为可组合的任务模块，以便对流程进行自动化、监控和扩展。

## 主要能力

- 监听指定目录并触发处理任务
- 基于 FFmpeg / OpenCV 进行视频格式与画面处理
- 使用大模型辅助生成标题和标签
- 配置任务队列与发布时间
- 适配 TikTok、抖音、快手、哔哩哔哩、视频号和小红书等平台
- 通过插件与 Handler 结构扩展处理及上传步骤
- 记录任务日志与执行状态

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
- `Dedup/`：基于 FFmpeg、OpenCV 的视频处理模块
- `Upload/`：各平台上传适配器与账号配置
- `my_apps.yaml`：应用与网络参数配置

主要技术：Python、FFmpeg、OpenCV、Playwright、Watchdog、APScheduler、LLM API。

## 快速开始

### 环境要求

- Windows
- Python 3.12+
- Node.js 22.x
- FFmpeg（需加入 `PATH`）
- Chrome

### 安装

```bash
git clone https://github.com/toki-plus/video-mover.git
cd video-mover
```

运行 `setup.bat` 安装 Python、Playwright 与相关依赖。建议在独立虚拟环境中运行。

### 配置

1. 在 `my_apps.yaml` 中配置输入目录、目标平台、账号文件、代理和调度参数。
2. 如启用 AI 文案功能，通过安全的本地配置方式提供 API Key。
3. 首次运行平台适配器时，根据提示完成账号登录与 Cookie 初始化。

```bash
python main.py
```

## 当前限制

- 平台页面和接口发生变化时，上传适配器可能需要同步更新。
- 部分上游依赖存在版本兼容要求，建议固定依赖版本并使用隔离环境。
- 项目尚未建立完整的自动化测试与 CI，生产使用前应进行小规模验证。
- API Key、Cookie 和账号配置不应提交到 Git 仓库。

## 项目价值

本项目重点验证的是跨工具、跨平台工作流的拆解与编排能力，包括任务边界设计、第三方系统适配、失败日志和后续扩展，而非单一的视频处理算法。

## License

See [LICENSE](./LICENSE).
