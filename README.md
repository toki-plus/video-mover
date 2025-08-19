# Video Mover - 全自动视频搬运与去重工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个强大的、全自动化的内容创作流水线工具。它可以**自动监听、下载指定的TikTok博主视频**，进行深度、多维度的**视频去重处理**，并利用**AI大模型生成爆款标题**，最终**自动发布**到不同平台。

---

> 需要进 **【短视频创作技术交流群】** 的朋友可以到最下方联系我。

### ✨ 核心功能矩阵

本项目将复杂的视频处理流程集成为三大自动化模块：

#### 📥 自动下载 (Auto-Download)
- **实时监控**：自动监听指定TikTok博主的发布状态。
- **即时下载**：一旦发布新视频，立即无水印下载到本地，为后续处理做准备。

#### ✂️ 智能去重 (Intelligent Deduplication)
提供一套强大的视频二次创作工具箱，所有功能均可配置和组合，以达到理想的去重效果：

- **性能优化**：
  - **🚀 GPU加速**：利用NVIDIA显卡大幅提升处理速度。
- **内容增强**：
  - **🔊 自动字幕**：智能识别音频并生成SRT字幕文件。
  - **✍️ 自定义标题**：在视频顶部或底部添加动态或静态标题，支持自定义字体、颜色和描边。
  - **🎵 背景音乐 (BGM)**：自动添加指定的背景音乐，并调整音量。
  - **🖼️ 画中画 (PIP)**：在主视频上叠加小窗口视频或图片。
- **视频处理**：
  - **🔇 静音剪辑**：自动检测并移除视频中的静音片段。
  - **🎞️ 基础操作**：镜像、旋转、裁剪、淡入淡出。
  - **🎨 画质调整**：饱和度、亮度、对比度调节。
  - **🌀 视觉特效**：背景模糊、高斯模糊、帧交换、颜色偏移、频域扰乱、纹理噪声、边缘模糊等高级特效。

> 对 **AB视频去重工具** 感兴趣的朋友可以移步我的另一个项目：https://github.com/toki-plus/AB-Video-Deduplicator
>

#### 🚀 AI 驱动上传 (AI-Powered Upload)
- **AI标题生成**：调用阿里云百炼AI大模型，分析视频内容，自动生成爆款标题和标签。
- **自动化发布**：模拟浏览器操作，登录视频号后台，自动填写所有信息并发布视频。

### 🎬 视频教程 (点击图片播放👇)

[![视频封面](https://i2.hdslb.com/bfs/archive/678607430d704dfbe72183613c6aca60dcebb4fc.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1txQeYyEEz)

### 🚀 快速上手指南 (Getting Started Guide)

请严格按照以下步骤进行环境配置和安装。

#### 第1步：环境准备 (Prerequisites)

请确保你的系统中已安装以下所有软件，并**正确配置了环境变量**（特别是`ffmpeg`）。

| 软件/工具              | 下载链接                                                     | 备注                                                     |
| :--------------------- | :----------------------------------------------------------- | :------------------------------------------------------- |
| **.NET Framework 4.8** | [官方下载](https://dotnet.microsoft.com/en-us/download/dotnet-framework/thank-you/net48-web-installer) | Windows 系统组件。                                       |
| **Python 3.12+**       | [官方下载](https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe) | 安装时请务必勾选 `Add Python to PATH`。                  |
| **Node.js 22.x**       | [官方下载](https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi) | 建议选择 LTS 版本。                                      |
| **Git**                | [官方下载](https://git-scm.com/downloads/win)                | 版本控制工具。                                           |
| **FFmpeg**             | [Gyan.dev Builds](https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-full_build.7z) | **必须**解压并将其 `bin` 目录添加到系统环境变量 `PATH`。 |
| **Chrome 浏览器**      | [官方下载](https://www.google.com/)                          | 用于自动化上传。                                         |
| **v2rayN** (可选)      | [GitHub Releases](https://github.com/2dust/v2rayN/releases/download/5.39/v2rayN-Core.zip) | 如果你需要网络代理来访问TikTok。                         |
| **VSCode** (推荐)      | [官方下载](https://code.visualstudio.com/Download)           | 用于修改配置文件和代码。                                 |

#### 第2步：安装与配置

1.  **克隆本项目**
    ```bash
    git clone https://github.com/你的用户名/你的仓库名.git
    cd 你的仓库名
    ```
2.  **自动安装依赖**
    双击运行项目根目录下的 `setup.bat` 脚本。它会自动安装所有必要的 Python 和 Node.js 依赖。

#### 第3步：⚠️ 重要：手动修改依赖库

由于特定功能需求，部分已安装的Python库需要进行少量代码修改。**这是保证程序正常运行的关键步骤**。

1.  **修改 `f2/apps/tiktok/handler.py` 文件**
    -   找到第 `389` 行，将 `cursor` 强制转换为 `int` 类型。
    -   **修改前**: `cursor`
    -   **修改后**: `int(cursor)`

2.  **修改 `f2/utils/utils.py` 文件**
    -   **定位到第 `200` 行附近**，修改日期处理逻辑以兼容不同格式。
        ```python
        # 将以下代码块:
        if date_type == "start":
            date_str = f"{start_date} 00-00-00"
        elif date_type == "end":
            date_str = f"{end_date} 23-59-59"
        # ...
        
        # 替换为:
        if len(start_date.split()) == 1:
            if date_type == "start":
                date_str = f"{start_date} 00-00-00"
            elif date_type == "end":
                date_str = f"{end_date} 23-59-59"
        else:
            if date_type == "start":
                date_str = f"{start_date}"
            elif date_type == "end":
                date_str = f"{end_date}"
        # ...
        ```
    -   **定位到第 `690` 行附近**，修改日期字符串解析逻辑。
        ```python
        # 将:
        start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d") + datetime.timedelta(...)

        # 替换为:
        if len(start_str.split()) == 1:
            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
        else:
            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d %H-%M-%S")
        if len(end_str.split()) == 1:
            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d") + datetime.timedelta(days=1, seconds=-1)
        else:
            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d %H-%M-%S")
        ```
3.  **修改 `tencent_uploader/main.py` 文件**
    -   找到 `Upload/uploader/tencent_uploader/main.py` 文件。
    -   **定位到第 `191` 行附近**，延长页面等待超时时间。
        ```python
        # 将:
        await page.wait_for_url(".../post/list", timeout=1500)
        
        # 替换为:
        await page.wait_for_url(".../post/list", timeout=10000)
        ```

#### 第4步：🔑 配置密钥与Cookie

1.  **阿里云百炼 API Key**
    -   前往阿里云百炼大模型平台申请 API Key。
    -   打开 `Upload/vx_upload.py` 文件，将你的 `api_key` 填入相应位置。
2.  **TikTok Cookie**
    -   在浏览器中登录 TikTok 网页版。
    -   打开开发者工具 (F12)，找到并复制 `Cookie` 值。
    -   打开根目录下的 `my_apps.yaml` 文件，将复制的 `Cookie` 替换掉原有内容。
3.  **网络代理 (可选)**
    -   如果需要，在 `my_apps.yaml` 文件中修改 `Proxy` 配置项。

### ▶️ 运行项目 (Running the Project)

1.  双击运行根目录下的 `start.bat` 脚本。
2.  程序会自动打开浏览器并开始执行任务。请根据提示进行登录等操作。
3.  在开发者工具中，点击绿色的三角形箭头（通常是 "Resume script execution"）以继续执行自动化流程。

### 💬 交流与支持

如果你希望交流短视频创作技术，欢迎通过以下方式联系我。

<table>
    <td align="center">
        <a href="https://llxoxll.com/">
            <img src="images/toki-plus.jpg" width="200px" alt="微信"/>
            <br />
            <sub><b>微信入群</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://llxoxll.com/">
            <img src="images/yqkj.jpg" width="200px" alt="公众号"/>
            <br />
            <sub><b>公众号</b></sub>
        </a>
    </td>
    <td align="center">
        <a href="https://llxoxll.com/">
            <img src="images/zanzhu.jpg" width="200px" alt="赞赏码"/>
            <br />
            <sub><b>支持项目</b></sub>
        </a>
    </td>
</table>
