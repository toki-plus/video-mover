# Video Mover

A configurable video-processing and publishing workflow for multi-platform content operations.

The project connects file monitoring, media processing, metadata generation, scheduling, and platform-specific publishing in one pipeline. It explores how repetitive content operations can be made more consistent and observable.

> Use this project only with content and accounts you are authorized to manage. Users are responsible for complying with copyright requirements, platform policies, and applicable laws.

## Context

Multi-platform publishing often involves disconnected manual steps: receiving assets, normalizing media, preparing copy, scheduling posts, and uploading the same content through different interfaces. This creates repetitive work and inconsistent execution.

Video Mover models these steps as composable tasks that can be automated, monitored, and extended.

## Capabilities

- Monitor directories and trigger processing jobs
- Normalize and process video with FFmpeg and OpenCV
- Generate titles and tags with an LLM
- Configure job queues and publishing schedules
- Support adapters for TikTok, Douyin, Kuaishou, Bilibili, WeChat Channels, and Xiaohongshu
- Extend processing and publishing behavior through plugins and handlers
- Record execution status and logs

## Workflow

```text
Content input
    -> File watcher
    -> Video processing
    -> Metadata generation
    -> Scheduling
    -> Platform adapters
    -> Execution logs
```

## Technical Design

- `main.py`: orchestration, file management, scheduling, and plugin entry point
- `Dedup/`: FFmpeg- and OpenCV-based media processing
- `Upload/`: platform adapters and account configuration
- `my_apps.yaml`: application and network settings

Core technologies: Python, FFmpeg, OpenCV, Playwright, Watchdog, APScheduler, and LLM APIs.

## Quick Start

### Requirements

- Windows
- Python 3.12+
- Node.js 22.x
- FFmpeg available on `PATH`
- Chrome

### Installation

```bash
git clone https://github.com/toki-plus/video-mover.git
cd video-mover
```

Run `setup.bat` to install Python, Playwright, and related dependencies. An isolated virtual environment is recommended.

### Configuration

1. Configure input folders, target platforms, account files, proxy settings, and schedules in `my_apps.yaml`.
2. If AI-assisted copy is enabled, provide API credentials through secure local configuration.
3. Initialize account sessions and cookies when running a platform adapter for the first time.

```bash
python main.py
```

## Current Limitations

- Platform adapters may require updates when third-party pages or interfaces change.
- Some upstream dependencies have version-specific compatibility requirements.
- The project does not yet include comprehensive automated tests or CI.
- API keys, cookies, and account configuration must never be committed to the repository.

## What This Project Demonstrates

The primary focus is workflow decomposition and cross-system orchestration: defining task boundaries, integrating third-party systems, recording failures, and leaving clear extension points. It is not intended as a showcase of a single media-processing algorithm.

## License

See [LICENSE](./LICENSE).
