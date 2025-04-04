import os
import sys
import time
import signal
import psutil
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict
from zoneinfo import ZoneInfo
from functools import lru_cache
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logging.handlers import RotatingFileHandler

if os.name == 'nt':
    import win32api

# 模块级导出定义
__all__ = ['AppConfig', 'HandlerBase', 'TaskPlugin', 'FileManager', 'FlushHandler', 
           'MainCommandHandler', 'UploadHandler', 'SchedulerManager']

# 配置日志（同时输出到终端和文件）
handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,
    backupCount=5,
    encoding='utf-8'  # 文件使用 UTF-8 编码
)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))  # 终端输出格式与文件一致

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[handler, console_handler]
)

# 配置类
class AppConfig:
    """应用程序配置类，负责加载和解析配置文件，并验证路径有效性。

    Attributes:
        DOWNLOAD_DIR (Path): 下载目录路径。
        DEDUP_DIR (Path): 去重目录路径。
        UPLOAD_DIR (Path): 上传目录路径。
        FLUSH_SCRIPT (Path): 刷新脚本路径。
        DEDUP_SCRIPT (Path): 去重脚本路径。
        UPLOAD_SCRIPT (Path): 上传脚本路径。
        MAIN_COMMAND (list): 主抓取命令。
        SCHEDULE_INTERVAL (int): 调度间隔（分钟，取值范围：1-1440）。
        TIMEZONE (str): 时区，默认 Asia/Singapore。
        MAX_WORKERS (int): 最大工作线程数，默认 CPU 核心数。
    """
    def __init__(self):
        base_dir = Path(__file__).parent.resolve()

        self.DOWNLOAD_DIR = (base_dir / 'Download/tiktok/post/astrospaceq').resolve()
        self.DEDUP_DIR = (base_dir / 'Dedup').resolve()
        self.UPLOAD_DIR = (base_dir / 'Upload').resolve()
        self.FLUSH_SCRIPT = (base_dir / 'flush_device_id.py').resolve()
        self.DEDUP_SCRIPT = (base_dir / 'Dedup/dedup.py').resolve()
        self.UPLOAD_SCRIPT = (base_dir / 'Upload/vx_upload.py').resolve()
        self.MAIN_COMMAND = ['f2', 'tk', '-c', 'my_apps.yaml', '-u', 'https://www.tiktok.com/@astrospaceq']
        self.SCHEDULE_INTERVAL = 300
        self.TIMEZONE = 'Asia/Singapore'
        self.MAX_WORKERS = os.cpu_count()

        for path, name in [
            (self.DOWNLOAD_DIR, "下载目录"), (self.DEDUP_DIR, "去重目录"), 
            (self.UPLOAD_DIR, "上传目录"), (self.FLUSH_SCRIPT, "刷新脚本"), 
            (self.DEDUP_SCRIPT, "去重脚本"), (self.UPLOAD_SCRIPT, "上传脚本")
        ]:
            if not path.exists():
                raise FileNotFoundError(f"{name}不存在: {path}")

# 抽象基类
class HandlerBase(ABC):
    """Handler基类，提供通用的子进程参数构建方法。"""
    def _build_subprocess_args(self) -> Dict[str, any]:
        return {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'encoding': 'utf-8',
            'errors': 'replace',
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        }

    @abstractmethod
    def run(self) -> bool:
        pass

# 任务插件接口
class TaskPlugin(ABC):
    """任务插件抽象基类，用于动态扩展任务类型。"""
    @abstractmethod
    def execute(self, context: Dict[str, any]) -> bool:
        pass

# 文件变化监控处理器
class FileChangeHandler(FileSystemEventHandler):
    """监控文件变化的事件处理器。"""
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

# 文件管理类
class FileManager(HandlerBase):
    """文件管理类，负责生成时间范围和去重视频。"""
    def __init__(self, config: AppConfig):
        self.config = config
        self.observer = Observer()
        self.observer.schedule(
            FileChangeHandler(self._on_file_changed), 
            str(self.config.DOWNLOAD_DIR), 
            recursive=True
        )
        self.observer.start()

    def _on_file_changed(self, file_path: str) -> None:
        logging.debug(f"检测到文件变化: {file_path}")

    def generate_time_range(self, interval_minutes: int) -> str:
        tz = ZoneInfo(self.config.TIMEZONE)
        now = datetime.now(tz)
        start_time = now - timedelta(minutes=interval_minutes)
        return f"{start_time.strftime('%Y-%m-%d %H-%M-%S')}|{now.strftime('%Y-%m-%d %H-%M-%S')}"

    def dedup_videos(self, time_range_str: str) -> int:
        try:
            start_str, end_str = time_range_str.split('|')
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H-%M-%S")
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H-%M-%S")
        except ValueError as e:
            logging.error(f"时间范围解析失败: {e}")
            return 0

        video_files = self._get_video_files(start_time, end_time)
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = [executor.submit(self._process_video, file) for file in video_files]
            total_processed = sum(f.result() for f in futures if f.result() is not None)
        logging.info(f"已处理 {total_processed} 个视频")
        return total_processed

    def _get_video_files(self, start_time: datetime, end_time: datetime) -> List[Path]:
        video_files = []
        for folder_path in self.config.DOWNLOAD_DIR.glob('*'):
            if not folder_path.is_dir():
                continue
            folder_time = self._parse_folder_time(folder_path.name)
            if folder_time and start_time <= folder_time <= end_time:
                for file in folder_path.glob('*.mp4'):
                    video_files.append(file)
        return video_files

    @lru_cache(maxsize=100)
    def _parse_folder_time(self, folder_name: str) -> Optional[datetime]:
        try:
            return datetime.strptime(folder_name, "%Y-%m-%d %H-%M-%S")
        except ValueError:
            return None

    def _process_video(self, input_file: Path) -> bool:
        output_dir = self.config.UPLOAD_DIR / 'videos'
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / input_file.name
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.config.DEDUP_SCRIPT), "-i", str(input_file), "-o", str(output_file)],
                cwd=self.config.DEDUP_DIR,
                stdout=None,
                stderr=None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            process.wait()
            if process.returncode == 0:
                logging.info(f"已去重并导出: {input_file.name}")
                return True
            else:
                logging.error(f"去重失败: {input_file.name}，返回码: {process.returncode}")
                return False
        except Exception as e:
            logging.error(f"处理视频失败: {input_file.name} -> {e}")
            return False

    def run(self) -> bool:
        """实现抽象方法，执行去重任务。"""
        time_range = self.generate_time_range(self.config.SCHEDULE_INTERVAL)
        return self.dedup_videos(time_range) > 0

# 刷新处理器
class FlushHandler(HandlerBase):
    """刷新处理类，负责执行刷新脚本并检查设备ID更新。"""
    def __init__(self, config: AppConfig):
        self.config = config

    def run(self) -> bool:
        logging.info(f"\n{'='*35}\n开始执行刷新脚本 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}")
        process = subprocess.Popen(
            [sys.executable, str(self.config.FLUSH_SCRIPT)],
            stdout=None,
            stderr=None,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        process.wait()
        success = process.returncode == 0
        if success:
            logging.info("✅ 刷新脚本执行成功")
        else:
            logging.error(f"刷新脚本执行失败，返回码: {process.returncode}")
        logging.info(f"\n{'='*35}\n刷新脚本执行结束 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}")
        return success

# 主命令处理器
class MainCommandHandler(HandlerBase):
    """主命令处理类，负责执行主抓取命令。"""
    def __init__(self, config: AppConfig):
        self.config = config
        self.current_process = None

    def execute_main_command(self, time_range_str: str) -> tuple[bool, bool]:
        command = self.config.MAIN_COMMAND + ["-i", time_range_str]
        logging.info(f"\n{'='*35}\n开始执行主命令 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}")
        self.current_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,          # 捕获标准输出
            stderr=subprocess.STDOUT,        # 将标准错误合并到标准输出
            text=True,                       # 以文本模式读取
            bufsize=1,                       # 逐行缓冲
            universal_newlines=True,         # 跨平台换行符处理
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        forbidden_found = False
        while True:
            output = self.current_process.stdout.readline()
            if output == '' and self.current_process.poll() is not None:
                break
            if output:
                print(output, end='')        # 实时输出到终端
                sys.stdout.flush()           # 确保输出不缓冲
                if "403 Forbidden" in output:
                    forbidden_found = True   # 检测到 "403 Forbidden"
        self.current_process.wait()
        success = self.current_process.returncode == 0
        logging.info(f"\n{'='*35}\n主命令执行结束 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}")
        return success, forbidden_found      # 返回成功状态和是否检测到 "403 Forbidden"

    def run(self) -> bool:
        """实现抽象方法，执行主命令。"""
        time_range = self.generate_time_range(self.config.SCHEDULE_INTERVAL)
        return self.execute_main_command(time_range)

    def generate_time_range(self, interval_minutes: int) -> str:
        tz = ZoneInfo(self.config.TIMEZONE)
        now = datetime.now(tz)
        start_time = now - timedelta(minutes=interval_minutes)
        return f"{start_time.strftime('%Y-%m-%d %H-%M-%S')}|{now.strftime('%Y-%m-%d %H-%M-%S')}"

# 上传处理器
class UploadHandler(HandlerBase):
    """视频上传处理类，负责执行上传脚本。"""
    def __init__(self, config: AppConfig):
        self.config = config

    def run(self) -> bool:
        self.config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        logging.info(f"\n{'='*35}\n开始执行上传脚本 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}")
        process = subprocess.Popen(
            [sys.executable, str(self.config.UPLOAD_SCRIPT)],
            stdout=None,
            stderr=None,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        process.wait()
        success = process.returncode == 0
        if success:
            logging.info("✅ 上传脚本执行成功")
        else:
            logging.error(f"上传脚本执行失败，返回码: {process.returncode}")
        logging.info(f"\n{'='*35}\n上传脚本执行结束 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}")
        return success

# 调度管理类
class SchedulerManager:
    """调度管理类，负责调度任务的执行和信号处理。"""
    PROCESS_TERMINATE_TIMEOUT = 5

    def __init__(self, config: AppConfig, file_manager: FileManager, flush_handler: FlushHandler, 
                 main_handler: MainCommandHandler, upload_handler: UploadHandler):
        self.config = config
        self.file_manager = file_manager
        self.flush_handler = flush_handler
        self.main_handler = main_handler
        self.upload_handler = upload_handler
        self.scheduler = BlockingScheduler(timezone=self.config.TIMEZONE)
        self.shutdown_flag = False
        self.plugins = [DedupPlugin(file_manager)]

    def start(self) -> None:
        self._print_banner()
        self._setup_jobs()
        self._register_signals()
        logging.info("调度器启动中...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logging.info("接收到中断信号，正在关闭...")
            self.shutdown()
        except Exception as e:
            logging.error(f"调度器异常: {e}", exc_info=True)
            self.shutdown()

    def _print_banner(self) -> None:
        logging.info(
            f"\n{'=' * 35}\n"
            "TikTok数据抓取调度器\n"
            f"动态时间范围: 滚动{self.config.SCHEDULE_INTERVAL}分钟窗口\n"
            f"执行间隔: 每{self.config.SCHEDULE_INTERVAL}分钟\n"
            "退出方式: Ctrl+C\n"
            f"{'=' * 35}"
        )

    def _setup_jobs(self) -> None:
        self.scheduler.add_job(
            self._job_wrapper,
            'interval',
            minutes=self.config.SCHEDULE_INTERVAL,
            next_run_time=datetime.now(ZoneInfo(self.config.TIMEZONE)),
            misfire_grace_time=600,
            max_instances=2
        )

    def _job_wrapper(self) -> None:
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        start_mem = psutil.virtual_memory().used
        logging.info(f"开始执行任务 - 时间: {datetime.now(ZoneInfo(self.config.TIMEZONE))}")
        try:
            if self.shutdown_flag:
                logging.info("调度器已标记为关闭，跳过任务执行")
                return
            time_range = self.file_manager.generate_time_range(self.config.SCHEDULE_INTERVAL)
            context = {'time_range': time_range}
            success, forbidden_found = self.main_handler.execute_main_command(time_range)
            if forbidden_found:  # 仅在失败且检测到 "403 Forbidden" 时执行
                logging.info("检测到 '403 Forbidden'，执行 flush_handler")
                if self.flush_handler.run():
                    logging.info("flush_handler 执行成功，准备重试 execute_main_command")
                    success, forbidden_found = self.main_handler.execute_main_command(time_range)
                else:
                    logging.warning("flush_handler 执行失败，跳过重试")
            if success:  # 仅当最终成功时执行后续任务
                for plugin in self.plugins:
                    plugin.execute(context)
                self.upload_handler.run()
            else:
                logging.warning("主命令执行失败，跳过后续任务")
        except Exception as e:
            logging.error(f"任务执行失败: {e}", exc_info=True)
        finally:
            end_time = time.time()
            end_cpu = psutil.cpu_percent()
            end_mem = psutil.virtual_memory().used
            logging.info(f"任务执行耗时: {end_time - start_time:.2f} 秒")
            logging.info(f"CPU使用变化: {end_cpu - start_cpu:.2f}%")
            logging.info(f"内存占用变化: {(end_mem - start_mem) / 1024 / 1024:.2f} MB")
            
    def _register_signals(self) -> None:
        if os.name == 'nt':
            win32api.SetConsoleCtrlHandler(self._windows_signal_handler, True)
        else:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        logging.info(f"接收到信号 {signum}，正在关闭调度器...")
        self.shutdown(signum)

    def _windows_signal_handler(self, dwCtrlType: int) -> bool:
        if dwCtrlType in (0, 1):  # CTRL_C_EVENT 或 CTRL_BREAK_EVENT
            logging.info("接收到 Windows 控制信号，正在关闭调度器...")
            self.shutdown()
            return True
        return False

    def shutdown(self, signum: Optional[int] = None) -> None:
        self.shutdown_flag = True
        logging.info("正在关闭调度器...")
        if self.main_handler.current_process and self.main_handler.current_process.poll() is None:
            try:
                parent = psutil.Process(self.main_handler.current_process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                parent.wait(timeout=self.PROCESS_TERMINATE_TIMEOUT)
                logging.info("子进程已正常终止")
            except psutil.NoSuchProcess:
                logging.warning("子进程已不存在")
            except psutil.TimeoutExpired:
                parent.kill()
                logging.warning("子进程未在超时时间内终止，已强制杀死")
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logging.info("调度器已关闭")
        self.file_manager.observer.stop()
        self.file_manager.observer.join()
        logging.info("文件监控已停止")
        sys.exit(0)

# 去重插件
class DedupPlugin(TaskPlugin):
    """去重任务插件。"""
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def execute(self, context: Dict[str, any]) -> bool:
        time_range = context['time_range']
        processed_count = self.file_manager.dedup_videos(time_range)
        context['processed_count'] = processed_count
        return processed_count > 0

if __name__ == "__main__":
    config = AppConfig()
    file_manager = FileManager(config)
    flush_handler = FlushHandler(config)
    main_handler = MainCommandHandler(config)
    upload_handler = UploadHandler(config)
    scheduler = SchedulerManager(config, file_manager, flush_handler, main_handler, upload_handler)
    scheduler.start()