import os
import re
import math
import cv2
import ffmpeg
import opencc
import tempfile
import random
import logging
import numpy as np
import pysrt
import whisper
import argparse
from typing import List, Tuple, Generator
from pydub import AudioSegment
from pydub.silence import split_on_silence
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

# 配置日志记录，用于调试和监控程序运行状态
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VideoConfig:
    """
    视频配置类，用于管理音频、视频特效、字幕等参数。
    """
    def __init__(self):
        # GPU加速
        self.enable_gpu: bool = False  # 是否启用 GPU 加速

        # 字幕参数
        self.include_subtitles: bool = False                # 是否添加字幕
        self.subtitles_opacity: float = 0.10                # 字幕透明度，范围0-1，默认1.0
        self.use_whisper: bool = True                       # 是否使用 Whisper 自动生成字幕
        self.whisper_model_name: str = 'base'               # 默认使用 'base' 模型
        self.subtitles_file: str = 'assets/subtitles.srt'   # 字幕文件路径
        self.subtitles_color: str = 'yellow'                # 字幕字体颜色
        self.subtitles_duration: int = 5                    # 字幕持续时间（秒），视频时长超过此值时添加字幕。

        # 标题参数
        self.include_titles: bool = False                   # 是否添加标题
        self.titles_opacity: float = 0.10                   # 标题透明度，范围0-1
        self.top_title: str = 'YANQU'                       # 顶部标题文本
        self.top_title_margin: int = 5                      # 顶部标题与顶部的间隙百分比，范围 0-100。
        self.bottom_title: str = 'YANQU'                    # 底部标题文本
        self.bottom_title_margin: int = 5                   # 底部标题与底部的间隙百分比，范围 0-100。
        self.titles_color: str = 'red'                      # 标题颜色，支持颜色名称或 HEX 码。

        # 水印参数
        self.include_watermark: bool = True                         # 是否添加水印
        self.watermark_opacity: float = 0.06                        # 水印透明度，范围0-1，文字0.10，图片视频0.05
        self.watermark_direction: str = 'random'                    # 水印移动方向
        self.watermark_color: str = 'white'                         # 水印颜色，支持颜色名称或 HEX 码。
        self.watermark_text: str = 'YANQU'                          # 水印文本内容
        self.watermark_type: str = 'image'                          # 水印类型，根据类型设置对应路径，text、image、video。
        self.watermark_image_path: str = 'assets/watermark.png'     # 图片水印文件路径，当 watermark_type 为 'image' 时使用。
        self.watermark_video_path: str = ''                         # 视频水印文件路径，当 watermark_type 为 'video' 时使用。

        # 字体
        self.custom_font_enabled: bool = True               # 是否使用自定义字体
        self.font_file: str = 'assets/fonts/simkai.ttf'     # 字体文件路径

        # 文字外边框
        self.text_border_size: int = 1                      # 文字外边框像素大小

        # 静音消除
        self.enable_silence_check: bool = False     # 是否启用静音检测
        self.silence_retention_ratio: float = 0.5   # 保留的静音比例，范围 0-0.5，0.5 表示保留 50% 的静音片段。
        self.silence_threshold: int = -50           # 静音检测阈值（分贝），绝对值越大保留的声音越多。
        self.silent_duration: int = 500             # 静音持续时间（毫秒），超过此时间触发静音处理。建议不低于 300ms，过小可能导致音频频繁中断。

        # 背景音乐
        self.include_background_music: bool = True          # 是否添加背景音乐
        self.background_music_file: str = 'assets/bgm.mp3'  # 背景音乐文件路径
        self.background_music_volume: float = 0.1           # 背景音乐音量，范围0-1。

        # 视频镜像与旋转
        self.flip_horizontal: bool = False                  # 是否启用水平镜像
        self.rotation_angle: int = -6                       # 旋转角度（度），建议值 -3 到 3。

        # 视频裁剪
        self.crop_percentage: float = 0.1                   # 裁剪百分比，范围 0-0.5，例如 0.1 表示裁剪每边 10% 的区域。

        # 淡入淡出
        self.fade_in_frames: int = 5                        # 淡入效果持续的帧数，建议 10-30 帧。
        self.fade_out_frames: int = 20                      # 淡出效果持续的帧数，建议 10-30 帧。

        # 画中画
        self.include_hzh: bool = True        # 是否启用画中画
        self.hzh_opacity: float = 0.1        # 画中画透明度
        self.hzh_scale: float = 1.0          # 画中画大小因子
        self.hzh_video_file: str = 'assets/hzh.mp4'  # 画中画视频文件路径

        # 颜色调整
        self.enable_sbc: bool = True         # 是否启用饱和度、亮度、对比度调整
        self.saturation: float = 1.05        # 饱和度调整因子，建议 0.8-1.2。值越小颜色越淡，值越大颜色越鲜艳。
        self.brightness: float = 0.05        # 亮度调整因子，建议 -0.3 到 0.3。负值降低亮度，正值增加亮度。
        self.contrast: float = 1.05          # 对比度调整因子，建议 0.8-1.2。值越小对比度越低，值越大对比度越高。

        # 背景模糊
        self.blur_background_enabled: bool = True           # 是否启用背景模糊
        self.top_blur_percentage: int = 3                   # 顶部模糊区域百分比，范围 0-100。
        self.bottom_blur_percentage: int = 3                # 底部模糊区域百分比，范围 0-100。
        self.side_blur_percentage: int = 3                  # 侧边模糊区域百分比，范围 0-100。

        # 高斯模糊
        self.gaussian_blur_interval: int = 15               # 高斯模糊帧步长，0 表示禁用。
        self.gaussian_blur_kernel_size: int = 3             # 高斯模糊核大小，必须为正奇数（如 1, 3, 5）。
        self.gaussian_blur_area_percentage: int = 15        # 高斯模糊区域大小百分比，范围 0-100。

        # 帧交换
        self.enable_frame_swap: bool = True                 # 是否启用帧交换
        self.frame_swap_interval: int = 15                  # 帧交换步长。建议值 5-20，每隔指定步长交换帧，增加动态效果。

        # 颜色偏移
        self.enable_color_shift: bool = True                # 是否启用颜色偏移
        self.color_shift_range: int = 3                     # 颜色偏移区间，3代表[-3,3]，该值越大颜色差距越明显

        # 高级效果
        self.scramble_frequency: float = 0.0                # 频域扰乱参数，0.0表示禁用，范围0.0-1.0，开启后处理时间较长。
        self.enable_texture_noise: bool = False             # 是否启用纹理噪声
        self.texture_noise_strength: float = 0.5            # 纹理噪声强度，范围 0-1，默认 0.5
        self.enable_blur_edge: bool = True                  # 是否启用边缘模糊

    def validate(self):
        """
        验证配置参数的有效性，确保所有参数和文件路径合法。
        """
        # GPU 加速
        if not isinstance(self.enable_gpu, bool):
            raise ValueError("enable_gpu 必须是布尔值")

        # 字幕参数
        if not isinstance(self.include_subtitles, bool):
            raise ValueError("include_subtitles 必须是布尔值")
        if not 0 <= self.subtitles_opacity <= 1:
            raise ValueError("subtitles_opacity 必须在 0 到 1 之间")
        if not isinstance(self.use_whisper, bool):
            raise ValueError("use_whisper 必须是布尔值")
        if not isinstance(self.whisper_model_name, str):
            raise ValueError("whisper_model_name 必须是字符串")
        if not isinstance(self.subtitles_file, str):
            raise ValueError("subtitles_file 必须是字符串")
        if not isinstance(self.subtitles_duration, (int, float)) or self.subtitles_duration < 0:
            raise ValueError("subtitles_duration 必须是非负数")
        if not self.is_valid_color(self.subtitles_color):
            raise ValueError("subtitles_color 必须是有效的颜色")

        # 标题参数
        if not isinstance(self.include_titles, bool):
            raise ValueError("include_titles 必须是布尔值")
        if not 0 <= self.titles_opacity <= 1:
            raise ValueError("titles_opacity 必须在 0 到 1 之间")
        if not isinstance(self.top_title, str):
            raise ValueError("top_title 必须是字符串")
        if not 0 <= self.top_title_margin <= 100:
            raise ValueError("top_title_margin 必须在 0 到 100 之间")
        if not isinstance(self.bottom_title, str):
            raise ValueError("bottom_title 必须是字符串")
        if not 0 <= self.bottom_title_margin <= 100:
            raise ValueError("bottom_title_margin 必须在 0 到 100 之间")
        if not self.is_valid_color(self.titles_color):
            raise ValueError("titles_color 必须是有效的颜色")

        # 水印参数
        if not isinstance(self.include_watermark, bool):
            raise ValueError("include_watermark 必须是布尔值")
        if not 0 <= self.watermark_opacity <= 1:
            raise ValueError("watermark_opacity 必须在 0 到 1 之间")
        if self.watermark_type not in ['text', 'image', 'video']:
            raise ValueError("watermark_type 必须是 'text', 'image' 或 'video'")
        if not self.is_valid_color(self.watermark_color):
            raise ValueError("watermark_color 必须是有效的颜色")
        if self.watermark_type == 'image' and not os.path.exists(self.watermark_image_path):
            raise FileNotFoundError(f"图片水印文件 {self.watermark_image_path} 不存在")
        if self.watermark_type == 'video' and not os.path.exists(self.watermark_video_path):
            raise FileNotFoundError(f"视频水印文件 {self.watermark_video_path} 不存在")

        # 字体
        if not isinstance(self.custom_font_enabled, bool):
            raise ValueError("custom_font_enabled 必须是布尔值")
        if self.custom_font_enabled and not os.path.exists(self.font_file):
            raise FileNotFoundError(f"字体文件 {self.font_file} 不存在")

        # 文字外边框
        if not isinstance(self.text_border_size, int) or self.text_border_size < 0:
            raise ValueError("text_border_size 必须是非负整数")

        # 音频参数
        if not isinstance(self.enable_silence_check, bool):
            raise ValueError("enable_silence_check 必须是布尔值")
        if not isinstance(self.silence_threshold, (int, float)):
            raise ValueError("silence_threshold 必须是数字")
        if not 0 <= self.silence_retention_ratio <= 1:
            raise ValueError("silence_retention_ratio 必须在 0 到 1 之间")
        if not isinstance(self.silent_duration, int) or self.silent_duration < 0:
            raise ValueError("silent_duration 必须是非负整数")

        # 背景音乐
        if not isinstance(self.include_background_music, bool):
            raise ValueError("include_background_music 必须是布尔值")
        if self.include_background_music and not os.path.exists(self.background_music_file):
            raise FileNotFoundError(f"背景音乐文件 {self.background_music_file} 不存在")
        if not 0 <= self.background_music_volume <= 1:
            raise ValueError("background_music_volume 必须在 0 到 1 之间")

        # 视频镜像与旋转
        if not isinstance(self.flip_horizontal, bool):
            raise ValueError("flip_horizontal 必须是布尔值")
        if not isinstance(self.rotation_angle, (int, float)):
            raise ValueError("rotation_angle 必须是数字")

        # 视频裁剪
        if not 0 <= self.crop_percentage <= 0.5:
            raise ValueError("crop_percentage 必须在 0 到 0.5 之间")

        # 淡入淡出
        if not isinstance(self.fade_in_frames, int) or self.fade_in_frames < 0:
            raise ValueError("fade_in_frames 必须是非负整数")
        if not isinstance(self.fade_out_frames, int) or self.fade_out_frames < 0:
            raise ValueError("fade_out_frames 必须是非负整数")

        # 画中画
        if not isinstance(self.include_hzh, bool):
            raise ValueError("include_hzh 必须是布尔值")
        if not 0 <= self.hzh_opacity <= 1:
            raise ValueError("hzh_opacity 必须在 0 到 1 之间")
        if not 0 < self.hzh_scale <= 1:
            raise ValueError("hzh_scale 必须在 0 到 1 之间")
        if self.include_hzh and not os.path.exists(self.hzh_video_file):
            raise FileNotFoundError(f"画中画视频文件 {self.hzh_video_file} 不存在")

        # 颜色调整
        if not isinstance(self.enable_sbc, bool):
            raise ValueError("enable_sbc 必须是布尔值")
        if self.saturation < 0:
            raise ValueError("saturation 必须是非负数")
        if self.brightness < -1 or self.brightness > 1:
            raise ValueError("brightness 必须在 -1 到 1 之间")
        if self.contrast < 0:
            raise ValueError("contrast 必须是非负数")

        # 背景模糊
        if not isinstance(self.blur_background_enabled, bool):
            raise ValueError("blur_background_enabled 必须是布尔值")
        if not 0 <= self.top_blur_percentage <= 100:
            raise ValueError("top_blur_percentage 必须在 0 到 100 之间")
        if not 0 <= self.bottom_blur_percentage <= 100:
            raise ValueError("bottom_blur_percentage 必须在 0 到 100 之间")
        if not 0 <= self.side_blur_percentage <= 100:
            raise ValueError("side_blur_percentage 必须在 0 到 100 之间")

        # 高斯模糊
        if not isinstance(self.gaussian_blur_interval, int) or self.gaussian_blur_interval < 0:
            raise ValueError("gaussian_blur_interval 必须是非负整数")
        if self.gaussian_blur_kernel_size < 1 or self.gaussian_blur_kernel_size % 2 == 0:
            raise ValueError("gaussian_blur_kernel_size 必须是正奇数")
        if not 0 <= self.gaussian_blur_area_percentage <= 100:
            raise ValueError("gaussian_blur_area_percentage 必须在 0 到 100 之间")

        # 帧交换
        if not isinstance(self.enable_frame_swap, bool):
            raise ValueError("enable_frame_swap 必须是布尔值")
        if not isinstance(self.frame_swap_interval, int) or self.frame_swap_interval < 1:
            raise ValueError("frame_swap_interval 必须是正整数")

        # 颜色偏移
        if not isinstance(self.enable_color_shift, bool):
            raise ValueError("enable_color_shift 必须是布尔值")
        if not isinstance(self.color_shift_range, int) or self.color_shift_range < 0:
            raise ValueError("color_shift_range 必须是非负整数")

        # 高级效果
        if not 0 <= self.scramble_frequency <= 1:
            raise ValueError("scramble_frequency 必须在 0 到 1 之间")
        if not isinstance(self.enable_texture_noise, bool):
            raise ValueError("enable_texture_noise 必须是布尔值")
        if not 0 <= self.texture_noise_strength <= 1:
            raise ValueError("texture_noise_strength 必须在 0 到 1 之间")
        if not isinstance(self.enable_blur_edge, bool):
            raise ValueError("enable_blur_edge 必须是布尔值")

        # 验证文件路径
        paths_to_check = [
            (self.background_music_file, "背景音乐文件"),
            (self.subtitles_file, "字幕文件"),
            (self.font_file, "字体文件"),
            (self.hzh_video_file if self.include_hzh else "", "画中画视频文件"),
            (self.watermark_image_path if self.watermark_type == 'image' else "", "图片水印文件"),
            (self.watermark_video_path if self.watermark_type == 'video' else "", "视频水印文件")
        ]
        for path, desc in paths_to_check:
            if path and not os.path.exists(path):
                raise FileNotFoundError(f"{desc} {path} 不存在")

    @staticmethod
    def is_valid_color(color_str: str) -> bool:
        """
        检查颜色字符串是否有效（支持颜色名称或 HEX 码）。

        参数:
            color_str: 颜色字符串，例如 'yellow' 或 '#FFFF00'

        返回:
            bool: True 表示颜色有效，False 表示无效
        """
        if color_str.startswith('#'):
            return bool(re.match(r'^#[0-9A-Fa-f]{6}$', color_str))
        valid_colors = ['yellow', 'red', 'green', 'blue', 'white', 'black']
        return color_str.lower() in valid_colors

class FFmpegHandler:
    """
    FFmpeg 工具类，用于处理音视频流。
    """
    @staticmethod
    def split_av_streams(input_path: str) -> Tuple[ffmpeg.Stream, ffmpeg.Stream]:
        """
        分离输入视频的音频流和视频流。

        参数:
            input_path: 输入视频文件路径

        返回:
            Tuple[ffmpeg.Stream, ffmpeg.Stream]: 视频流和音频流（如果存在）
        """
        try:
            probe = ffmpeg.probe(input_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            if not video_stream:
                raise ValueError("未找到视频流")
            stream = ffmpeg.input(input_path)
            return stream.video, stream.audio if audio_stream else None
        except ffmpeg.Error as e:
            logging.error(f"分离音视频流失败: {e.stderr.decode()}")
            raise

    @staticmethod
    def get_video_properties(input_path: str) -> Tuple[int, int, float]:
        """
        获取视频的宽度、高度和帧率。

        参数:
            input_path: 输入视频文件路径

        返回:
            Tuple[int, int, float]: 宽度、高度和帧率
        """
        try:
            probe = ffmpeg.probe(input_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            return (int(video_info['width']), int(video_info['height']),
                    float(eval(video_info['r_frame_rate'])))
        except ffmpeg.Error as e:
            logging.error(f"获取视频属性失败: {e.stderr.decode()}")
            raise

class AudioHandler:
    """
    音频处理类，用于静音去除和背景音乐混合。
    """
    @staticmethod
    def remove_silence(audio_path: str, config: VideoConfig) -> str:
        """
        删除音频中的静音部分，保留所有非静音内容。

        参数:
            audio_path: 输入音频文件路径
            config: 视频处理配置对象

        返回:
            str: 处理后的音频文件路径
        """
        if not config.enable_silence_check:
            return audio_path

        try:
            audio = AudioSegment.from_file(audio_path)
            chunks = split_on_silence(audio, min_silence_len=config.silent_duration,
                                      silence_thresh=config.silence_threshold)
            if not chunks:
                logging.warning("未检测到非静音片段，返回原始音频")
                return audio_path
            processed_audio = AudioSegment.silent(duration=0)  # 初始化空音频
            for chunk in chunks:
                processed_audio += chunk  # 直接拼接所有非静音片段
                if config.silence_retention_ratio > 0:  # 可选：在片段间添加少量静音
                    silence_duration = int(config.silent_duration * config.silence_retention_ratio)
                    processed_audio += AudioSegment.silent(duration=silence_duration)
            output_path = tempfile.mktemp(suffix='.wav')
            processed_audio.export(output_path, format='wav')
            logging.info(f"静音处理完成，输出到 {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"静音处理失败: {str(e)}")
            raise

    @staticmethod
    def mix_bgm(original_audio_path: str, bgm_path: str, background_music_volume: float = 0.5) -> str:
        """
        将原始音频与背景音乐混合，支持音量调节。
        参数:
            original_audio_path: 原始音频文件路径
            bgm_path: 背景音乐文件路径
            background_music_volume: 背景音乐音量，范围0-1
        返回:
            str: 混合后的音频文件路径
        """
        if not bgm_path or not os.path.exists(bgm_path):
            logging.warning("背景音乐路径无效，返回原始音频")
            return original_audio_path
        try:
            original = AudioSegment.from_file(original_audio_path)
            bgm = AudioSegment.from_file(bgm_path)
            # 调整BGM音量：转换为分贝调整，0时静音，1时保持原音量
            bgm = bgm + 20 * math.log10(background_music_volume) if background_music_volume > 0 else bgm - 60  # -60dB接近静音
            mixed = original.overlay(bgm, loop=True)
            mixed_path = tempfile.mktemp(suffix='.wav')
            mixed.export(mixed_path, format='wav')
            logging.info(f"背景音乐混合完成，输出到 {mixed_path}")
            return mixed_path
        except Exception as e:
            logging.error(f"背景音乐混合失败: {str(e)}")
            raise

class SubtitleHandler:
    """字幕处理类，用于生成和添加字幕"""
    
    @staticmethod
    def generate_subtitles(input_path: str, model_name: str = 'base') -> str:
        """使用 Whisper 生成字幕文件，并将繁体中文转换为简体中文"""
        try:
            import warnings
            # 抑制 FP16 警告
            warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")
            model = whisper.load_model(model_name)
            result = model.transcribe(input_path)
            srt_path = tempfile.NamedTemporaryFile(suffix='.srt', delete=False).name
            converter = opencc.OpenCC('t2s')  # 繁体转简体
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(result['segments']):
                    start = segment['start']
                    end = segment['end']
                    text = converter.convert(segment['text'].strip())  # 转换为简体中文
                    f.write(f"{i+1}\n")
                    f.write(f"{SubtitleHandler.format_time(start)} --> {SubtitleHandler.format_time(end)}\n")
                    f.write(f"{text}\n\n")
            logging.debug(f"字幕文件生成: {srt_path}")
            return srt_path
        except Exception as e:
            logging.error(f"字幕生成失败: {str(e)}")
            raise

    @staticmethod
    def format_time(seconds: float) -> str:
        """将秒数格式化为 SRT 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')

class VideoEffects:
    """
    视频特效类，包含水印、字幕、模糊等效果的实现。
    """
    @staticmethod
    def add_watermark(frame: np.ndarray, config: VideoConfig, frame_idx: int, total_frames: int, handler: 'VideoHandler' = None) -> np.ndarray:
        """
        在视频帧上添加水印（支持文本、图片和视频水印）。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象
            frame_idx: 当前帧索引
            total_frames: 视频总帧数

        返回:
            np.ndarray: 添加水印后的帧
        """
        h, w = frame.shape[:2]
        
        if config.watermark_type == 'text' and config.watermark_text:
            # 保持原有文本水印逻辑不变
            font_size = max(10, min(h // 20, w // len(config.watermark_text)))
            font = ImageFont.truetype(config.font_file, font_size) if config.custom_font_enabled and os.path.exists(config.font_file) else ImageFont.load_default()
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            text_bbox = draw.textbbox((0, 0), config.watermark_text, font=font)
            text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
            x, y = VideoEffects.get_watermark_position(config.watermark_direction, frame_idx, total_frames, w, h, text_width, text_height)
            x, y = max(0, min(x, w - text_width)), max(0, min(y, h - text_height))
            color = VideoEffects.parse_color(config.watermark_color)
            border_size = config.text_border_size
            opacity = config.watermark_opacity
            
            if opacity < 1.0:
                watermark_img = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
                watermark_draw = ImageDraw.Draw(watermark_img)
                border_color = (0, 0, 0, int(255 * opacity))
                for dx in range(-border_size, border_size + 1):
                    for dy in range(-border_size, border_size + 1):
                        if dx != 0 or dy != 0:
                            watermark_draw.text((x + dx, y + dy), config.watermark_text, font=font, fill=border_color)
                text_color = (*color, int(255 * opacity))
                watermark_draw.text((x, y), config.watermark_text, font=font, fill=text_color)
                pil_img = Image.alpha_composite(pil_img.convert('RGBA'), watermark_img).convert('RGB')
            else:
                for dx in range(-border_size, border_size + 1):
                    for dy in range(-border_size, border_size + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), config.watermark_text, font=font, fill=(0, 0, 0))
                draw.text((x, y), config.watermark_text, font=font, fill=color)
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        elif config.watermark_type == 'image' and config.watermark_image_path and handler and handler.wm_rgb is not None:
            wm_width, wm_height = handler.watermark_img.size
            x, y = VideoEffects.get_watermark_position(config.watermark_direction, frame_idx, total_frames, w, h, wm_width, wm_height)
            if x + wm_width > w or y + wm_height > h or x < 0 or y < 0:
                return frame
            roi = frame[y:y+wm_height, x:x+wm_width]
            for c in range(3):
                roi[:, :, c] = (1 - handler.wm_alpha) * roi[:, :, c] + handler.wm_alpha * handler.wm_rgb[:, :, c]
            frame[y:y+wm_height, x:x+wm_width] = roi
        
        elif config.watermark_type == 'video' and config.watermark_video_path:
            # 视频水印（未来扩展）
            # 这里仅提供占位逻辑，实际实现需要同步视频帧
            # 由于需要同步视频帧，复杂度较高，此处仅记录为待实现功能，可在未来通过在 VideoHandler 中加载水印视频帧并传递到此方法实现。
            logging.warning("视频水印功能尚未实现")
            pass
        
        return frame

    @staticmethod
    def parse_color(color_str: str) -> Tuple[int, int, int]:
        """将颜色字符串解析为 BGR 元组"""
        if color_str.startswith('#'):  # 支持 HEX 码
            r, g, b = tuple(int(color_str[i:i+2], 16) for i in (1, 3, 5))
            return (b, g, r)  # 返回 BGR
        colors = {
            'yellow': (0, 255, 255),  # BGR
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'cyan': (255, 255, 0),
            'magenta': (255, 0, 255),
            'orange': (0, 165, 255),
            'purple': (128, 0, 128),
            'brown': (42, 42, 165),
            'gray': (128, 128, 128)
        }
        return colors.get(color_str.lower(), (255, 255, 255))  # 默认白色

    @staticmethod
    def get_watermark_position(direction: str, frame_index: int, total_frames: int,
                               video_width: int, video_height: int, watermark_width: int,
                               watermark_height: int) -> Tuple[int, int]:
        """
        计算动态水印的坐标位置，支持米字形8方向运动。

        参数:
            direction: 运动方向，支持以下模式：
                - 'left_to_right': 从左侧到右侧水平移动
                - 'right_to_left': 从右侧到左侧水平移动
                - 'top_to_bottom': 从顶部到底部垂直移动
                - 'bottom_to_top': 从底部到顶部垂直移动
                - 'lt_to_rb': 左上到右下对角线移动
                - 'rt_to_lb': 右上到左下对角线移动
                - 'lb_to_rt': 左下到右上对角线移动
                - 'rb_to_lt': 右下到左上对角线移动
            frame_index: 当前帧序号 (从0开始)
            total_frames: 视频总帧数
            video_width: 视频宽度 (像素)
            video_height: 视频高度 (像素)
            watermark_width: 水印宽度 (像素)
            watermark_height: 水印高度 (像素)

        返回:
            Tuple[int, int]: 水印的 x, y 坐标
        """
        MARGIN = 20  # 安全边距

        if direction == 'random':
            # 随机生成 x 和 y 坐标，确保在安全边距内
            x = random.randint(MARGIN, video_width - watermark_width - MARGIN)
            y = random.randint(MARGIN, video_height - watermark_height - MARGIN)
        else:
            progress = frame_index / total_frames
            
            # 计算可用移动范围
            range_x = video_width - watermark_width - 2 * MARGIN
            range_y = video_height - watermark_height - 2 * MARGIN
            
            if direction == 'left_to_right':
                x = MARGIN + int(range_x * progress)
                y = (video_height - watermark_height) // 2  # 垂直居中
            elif direction == 'right_to_left':
                x = video_width - MARGIN - watermark_width - int(range_x * progress)
                y = (video_height - watermark_height) // 2
            elif direction == 'top_to_bottom':
                x = (video_width - watermark_width) // 2    # 水平居中
                y = MARGIN + int(range_y * progress)
            elif direction == 'bottom_to_top':
                x = (video_width - watermark_width) // 2
                y = video_height - MARGIN - watermark_height - int(range_y * progress)
            elif direction == 'lt_to_rb':  # 左上→右下
                x = MARGIN + int(range_x * progress)
                y = MARGIN + int(range_y * progress)
            elif direction == 'rt_to_lb':  # 右上→左下
                x = video_width - MARGIN - watermark_width - int(range_x * progress)
                y = MARGIN + int(range_y * progress)
            elif direction == 'lb_to_rt':  # 左下→右上
                x = MARGIN + int(range_x * progress)
                y = video_height - MARGIN - watermark_height - int(range_y * progress)
            elif direction == 'rb_to_lt':  # 右下→左上
                x = video_width - MARGIN - watermark_width - int(range_x * progress)
                y = video_height - MARGIN - watermark_height - int(range_y * progress)
            else:  # 默认居中显示
                x = (video_width - watermark_width) // 2
                y = (video_height - watermark_height) // 2

        return (x, y)

    @staticmethod
    def add_subtitles(frame: np.ndarray, config: VideoConfig, frame_idx: int, 
                    fps: float, subs: pysrt.SubRipFile) -> np.ndarray:
        """
        在视频帧上添加字幕。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象
            frame_idx: 当前帧索引
            fps: 视频帧率
            subs: 字幕文件对象

        返回:
            np.ndarray: 添加字幕后的帧
        """
        if not config.subtitles_file or not os.path.exists(config.subtitles_file) or not subs:
            return frame
        current_time = frame_idx / fps
        def time_to_seconds(time_obj):
            return (time_obj.hours * 3600 + time_obj.minutes * 60 + 
                    time_obj.seconds + time_obj.milliseconds / 1000.0)
        for sub in subs:
            start_time = time_to_seconds(sub.start)
            end_time = time_to_seconds(sub.end)
            if start_time <= current_time <= end_time:
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil_img)
                font = ImageFont.truetype(config.font_file, 30) if config.custom_font_enabled and os.path.exists(config.font_file) else ImageFont.load_default()
                text_bbox = draw.textbbox((0, 0), sub.text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                x = (frame.shape[1] - text_width) // 2
                y = frame.shape[0] - text_height - 20
                color = VideoEffects.parse_color(config.subtitles_color)
                border_size = config.text_border_size
                opacity = config.subtitles_opacity
                if opacity < 1.0:
                    # 创建透明的字幕层
                    subtitle_img = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
                    subtitle_draw = ImageDraw.Draw(subtitle_img)
                    # 绘制外边框，透明度一致
                    border_color = (0, 0, 0, int(255 * opacity))
                    for dx in range(-border_size, border_size + 1):
                        for dy in range(-border_size, border_size + 1):
                            if dx != 0 or dy != 0:
                                subtitle_draw.text((x + dx, y + dy), sub.text, font=font, fill=border_color)
                    # 绘制文字，透明度一致
                    text_color = (*color, int(255 * opacity))
                    subtitle_draw.text((x, y), sub.text, font=font, fill=text_color)
                    # 合成图像
                    pil_img = Image.alpha_composite(pil_img.convert('RGBA'), subtitle_img).convert('RGB')
                else:
                    # 无透明度，直接绘制
                    for dx in range(-border_size, border_size + 1):
                        for dy in range(-border_size, border_size + 1):
                            if dx != 0 or dy != 0:
                                draw.text((x + dx, y + dy), sub.text, font=font, fill=(0, 0, 0))
                    draw.text((x, y), sub.text, font=font, fill=color)
                return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return frame

    @staticmethod
    def add_titles(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        在视频帧上添加顶部和底部标题。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 添加标题后的帧
        """
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.truetype(config.font_file, 30) if config.custom_font_enabled and os.path.exists(config.font_file) else ImageFont.load_default()
        color = VideoEffects.parse_color(config.titles_color)
        border_size = config.text_border_size
        opacity = config.titles_opacity

        if config.top_title:
            text_bbox = draw.textbbox((0, 0), config.top_title, font=font)
            text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
            x = (frame.shape[1] - text_width) // 2
            y = int(frame.shape[0] * config.top_title_margin / 100)
            if opacity < 1.0:
                # 创建透明的标题层
                title_img = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
                title_draw = ImageDraw.Draw(title_img)
                # 绘制外边框，透明度一致
                border_color = (0, 0, 0, int(255 * opacity))
                for dx in range(-border_size, border_size + 1):
                    for dy in range(-border_size, border_size + 1):
                        if dx != 0 or dy != 0:
                            title_draw.text((x + dx, y + dy), config.top_title, font=font, fill=border_color)
                # 绘制文字，透明度一致
                text_color = (*color, int(255 * opacity))
                title_draw.text((x, y), config.top_title, font=font, fill=text_color)
                # 合成图像
                pil_img = Image.alpha_composite(pil_img.convert('RGBA'), title_img).convert('RGB')
            else:
                # 无透明度，直接绘制
                for dx in range(-border_size, border_size + 1):
                    for dy in range(-border_size, border_size + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), config.top_title, font=font, fill=(0, 0, 0))
                draw.text((x, y), config.top_title, font=font, fill=color)

        if config.bottom_title:
            text_bbox = draw.textbbox((0, 0), config.bottom_title, font=font)
            text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
            x = (frame.shape[1] - text_width) // 2
            y = frame.shape[0] - text_height - int(frame.shape[0] * config.bottom_title_margin / 100)
            if opacity < 1.0:
                # 创建透明的标题层
                title_img = Image.new('RGBA', pil_img.size, (0, 0, 0, 0))
                title_draw = ImageDraw.Draw(title_img)
                # 绘制外边框，透明度一致
                border_color = (0, 0, 0, int(255 * opacity))
                for dx in range(-border_size, border_size + 1):
                    for dy in range(-border_size, border_size + 1):
                        if dx != 0 or dy != 0:
                            title_draw.text((x + dx, y + dy), config.bottom_title, font=font, fill=border_color)
                # 绘制文字，透明度一致
                text_color = (*color, int(255 * opacity))
                title_draw.text((x, y), config.bottom_title, font=font, fill=text_color)
                # 合成图像
                pil_img = Image.alpha_composite(pil_img.convert('RGBA'), title_img).convert('RGB')
            else:
                # 无透明度，直接绘制
                for dx in range(-border_size, border_size + 1):
                    for dy in range(-border_size, border_size + 1):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y + dy), config.bottom_title, font=font, fill=(0, 0, 0))
                draw.text((x, y), config.bottom_title, font=font, fill=color)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    @staticmethod
    def apply_gaussian_blur(frame: np.ndarray, config: VideoConfig, frame_idx: int) -> np.ndarray:
        """
        在指定帧上应用高斯模糊效果。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象
            frame_idx: 当前帧索引

        返回:
            np.ndarray: 应用高斯模糊后的帧
        """
        if config.gaussian_blur_interval == 0 or frame_idx % config.gaussian_blur_interval != 0:
            return frame
        kernel = config.gaussian_blur_kernel_size if config.gaussian_blur_kernel_size % 2 == 1 else config.gaussian_blur_kernel_size + 1
        area_size = config.gaussian_blur_area_percentage / 100
        h, w = frame.shape[:2]
        blur_h = int(h * area_size)
        blur_w = int(w * area_size)
        # 只模糊指定区域，避免重复处理整个帧
        frame[0:blur_h, :] = cv2.GaussianBlur(frame[0:blur_h, :], (kernel, kernel), 0)
        frame[h-blur_h:h, :] = cv2.GaussianBlur(frame[h-blur_h:h, :], (kernel, kernel), 0)
        frame[:, 0:blur_w] = cv2.GaussianBlur(frame[:, 0:blur_w], (kernel, kernel), 0)
        frame[:, w-blur_w:w] = cv2.GaussianBlur(frame[:, w-blur_w:w], (kernel, kernel), 0)
        return frame

    @staticmethod
    def rotate_frame(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        旋转视频帧。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 旋转后的帧
        """
        if config.rotation_angle != 0:
            h, w = frame.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, config.rotation_angle, 1.0)
            frame = cv2.warpAffine(frame, matrix, (w, h))
        return frame

    @staticmethod
    def adjust_sbc(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        调整视频帧的饱和度、亮度和对比度。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 调整后的帧
        """
        if config.enable_sbc:
            frame = cv2.convertScaleAbs(frame, alpha=config.contrast, beta=config.brightness * 255)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * config.saturation, 0, 255)
            frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return frame

    @staticmethod
    def blur_background(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        对视频帧的背景应用模糊效果。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 应用背景模糊后的帧
        """
        if not config.blur_background_enabled:
            return frame
        h, w = frame.shape[:2]
        top = int(h * config.top_blur_percentage / 100)
        bottom = int(h * config.bottom_blur_percentage / 100)
        side = int(w * config.side_blur_percentage / 100)
        frame[:top, :] = cv2.GaussianBlur(frame[:top, :], (21, 21), 0)
        frame[-bottom:, :] = cv2.GaussianBlur(frame[-bottom:, :], (21, 21), 0)
        frame[:, :side] = cv2.GaussianBlur(frame[:, :side], (21, 21), 0)
        frame[:, -side:] = cv2.GaussianBlur(frame[:, -side:], (21, 21), 0)
        return frame

    @staticmethod
    def apply_fade_effect(frame: np.ndarray, config: VideoConfig, frame_idx: int, total_frames: int) -> np.ndarray:
        """
        在单帧级别应用淡入淡出效果。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象
            frame_idx: 当前帧索引
            total_frames: 视频总帧数

        返回:
            np.ndarray: 应用淡入淡出效果后的帧
        """
        if frame_idx < config.fade_in_frames:
            alpha = frame_idx / config.fade_in_frames
            frame = cv2.addWeighted(frame, alpha, np.zeros_like(frame), 1 - alpha, 0)
        elif frame_idx >= total_frames - config.fade_out_frames:
            alpha = (total_frames - frame_idx) / config.fade_out_frames
            frame = cv2.addWeighted(frame, alpha, np.zeros_like(frame), 1 - alpha, 0)
        return frame

    @staticmethod
    def color_shift(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        对视频帧应用颜色偏移效果。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 应用颜色偏移后的帧
        """
        if config.enable_color_shift:
            b, g, r = cv2.split(frame)
            shift = random.randint(-config.color_shift_range, config.color_shift_range)
            b = b.astype(np.int16)
            g = g.astype(np.int16)
            b = np.clip(b + shift, 0, 255).astype(np.uint8)
            g = np.clip(g - shift, 0, 255).astype(np.uint8)
            frame = cv2.merge((b, g, r))
        return frame

    @staticmethod
    def add_hzh_effect(frame: np.ndarray, config: VideoConfig, frame_idx: int, total_frames: int) -> np.ndarray:
        """
        在视频帧上添加画中画效果。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象
            frame_idx: 当前帧索引
            total_frames: 视频总帧数

        返回:
            np.ndarray: 添加画中画效果后的帧
        """
        if not config.include_hzh or not os.path.exists(config.hzh_video_file):
            return frame
        cap = cv2.VideoCapture(config.hzh_video_file)
        hzh_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        hzh_idx = frame_idx % hzh_frame_count
        cap.set(cv2.CAP_PROP_POS_FRAMES, hzh_idx)
        ret, hzh_frame = cap.read()
        cap.release()
        if ret:
            h, w = frame.shape[:2]
            hzh_h, hzh_w = int(h * config.hzh_scale), int(w * config.hzh_scale)
            hzh_frame = cv2.resize(hzh_frame, (hzh_w, hzh_h))
            hzh_frame = cv2.cvtColor(hzh_frame, cv2.COLOR_BGR2RGB)  # 转换为 RGB
            # 计算居中位置
            x = (w - hzh_w) // 2
            y = (h - hzh_h) // 2
            # 检查画中画是否超出原视频尺寸
            if x < 0 or y < 0 or x + hzh_w > w or y + hzh_h > h:
                # 当尺寸超出时，直接覆盖整个画面
                frame = cv2.resize(hzh_frame, (w, h))
            else:
                # 正常情况下，使用透明度混合
                roi = frame[y:y+hzh_h, x:x+hzh_w]
                blended = cv2.addWeighted(roi, 1 - config.hzh_opacity, hzh_frame, config.hzh_opacity, 0)
                frame[y:y+hzh_h, x:x+hzh_w] = blended
        return frame

    @staticmethod
    def scramble_phase(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        在频域中对视频帧进行扰乱处理。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 应用频域扰乱后的帧
        """
        if not config.scramble_frequency:
            return frame
        # 将元组转换为列表，以便修改
        channels = list(cv2.split(frame))
        
        # 处理每个通道
        for i in range(len(channels)):
            # 傅里叶变换
            f = np.fft.fft2(channels[i])
            fshift = np.fft.fftshift(f)
            # 获取幅度和相位
            magnitude = np.abs(fshift)
            phase = np.angle(fshift)
            # 扰动相位
            phase += np.random.uniform(-config.scramble_frequency, config.scramble_frequency, phase.shape)
            # 重构频域信号
            fshift_new = magnitude * np.exp(1j * phase)
            f_ishift = np.fft.ifftshift(fshift_new)
            # 逆傅里叶变换并更新通道
            img_back = np.fft.ifft2(f_ishift)
            channels[i] = np.abs(img_back).astype(np.uint8)
        # 合并处理后的通道
        return cv2.merge(channels)
    
    @staticmethod
    def add_texture_noise(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        为视频帧添加纹理噪声。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 添加纹理噪声后的帧
        """
        if not config.enable_texture_noise:
            return frame
        # 生成高斯噪声并乘以强度系数
        noise = np.random.normal(0, 1, frame.shape).astype(np.float32) * config.texture_noise_strength
        # 限制噪声范围并转换为整数
        noise = np.clip(noise, -255, 255).astype(np.int16)
        # 将帧转换为 int16 类型以避免溢出
        frame = frame.astype(np.int16)
        frame += noise
        # 裁剪回 uint8 范围
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        return frame

    @staticmethod
    def apply_edge_blur(frame: np.ndarray, config: VideoConfig) -> np.ndarray:
        """
        对视频帧的边缘应用模糊效果。

        参数:
            frame: 当前视频帧
            config: 视频处理配置对象

        返回:
            np.ndarray: 应用边缘模糊后的帧
        """
        if not config.enable_blur_edge:
            return frame
        edges = cv2.Canny(frame, 100, 200)
        blurred = cv2.GaussianBlur(edges, (21, 21), 0)
        return cv2.addWeighted(frame, 0.9, cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR), 0.1, 0)

class VideoHandler:
    """
    视频处理主类，协调音频和视频的处理流程。
    """
    def __init__(self, config: VideoConfig):
        """
        初始化视频处理器，验证配置。

        参数:
            config: 视频处理配置对象
        """
        self.config = config
        self.config.validate()
        self.subs = None        # 字幕对象，延迟到 process_video 中加载
        self.batch_size = min(100, max(10, os.cpu_count() * 10))  # 动态调整

        # 预加载图片水印
        self.watermark_img = None
        self.wm_rgb = None
        self.wm_alpha = None
        if config.watermark_type == 'image' and config.watermark_image_path:
            self.watermark_img = Image.open(config.watermark_image_path).convert("RGBA")

    def process_video(self, input_path: str, output_path: str) -> None:
        """
        处理整个视频，包括音频和视频的处理，并将结果保存。

        参数:
            input_path: 输入视频文件路径
            output_path: 输出视频文件路径
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入视频 {input_path} 不存在")
        
        # 检查并启用 GPU 加速
        if self.config.enable_gpu:
            try:
                cv2.ocl.setUseOpenCL(True)
                logging.info("GPU 加速已启用")
            except Exception as e:
                logging.warning(f"启用 GPU 加速失败: {str(e)}")
        
        video_stream, audio_stream = FFmpegHandler.split_av_streams(input_path)
        width, height, fps = FFmpegHandler.get_video_properties(input_path)
        cap = cv2.VideoCapture(input_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        temp_files = []
        subtitles_file = None

        try:
            # 预处理图片水印大小
            if self.config.watermark_type == 'image' and self.watermark_img:
                wm_width = width // 5
                wm_height = int(wm_width * self.watermark_img.height / self.watermark_img.width)
                self.watermark_img = self.watermark_img.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
                wm_array = np.array(self.watermark_img)
                self.wm_rgb = cv2.cvtColor(wm_array[:, :, :3], cv2.COLOR_RGB2BGR)
                self.wm_alpha = wm_array[:, :, 3] / 255.0 * self.config.watermark_opacity
            # 获取视频时长并根据 subtitles_duration 决定是否加载字幕
            probe = ffmpeg.probe(input_path)
            duration = float(probe['format']['duration'])
            if self.config.include_subtitles and duration > self.config.subtitles_duration:
                if self.config.use_whisper:
                    subtitles_file = SubtitleHandler.generate_subtitles(input_path, self.config.whisper_model_name)
                    temp_files.append(subtitles_file)
                    logging.info(f"使用 Whisper 生成字幕: {subtitles_file}")
                else:
                    subtitles_file = self.config.subtitles_file
                
                if subtitles_file and os.path.exists(subtitles_file):
                    self.subs = pysrt.open(subtitles_file)
                    logging.info(f"字幕文件已加载: {subtitles_file}")
                else:
                    logging.warning(f"字幕文件 {subtitles_file} 不存在，跳过字幕加载")
                    self.subs = None
            else:
                logging.info(f"不添加字幕：include_subtitles={self.config.include_subtitles}, duration={duration}, subtitles_duration={self.config.subtitles_duration}")
                self.subs = None

            # 处理音频
            audio_path = tempfile.mktemp(suffix='.wav')
            temp_files.append(audio_path)
            if audio_stream:
                audio_stream.output(audio_path, format='wav').run(overwrite_output=True)
                processed_audio_path = AudioHandler.remove_silence(audio_path, self.config)
                temp_files.append(processed_audio_path)
                if self.config.include_background_music and self.config.background_music_file and os.path.exists(self.config.background_music_file):
                    mixed_audio_path = AudioHandler.mix_bgm(processed_audio_path, self.config.background_music_file, self.config.background_music_volume)
                    temp_files.append(mixed_audio_path)
                    audio_stream = ffmpeg.input(mixed_audio_path)
                else:
                    audio_stream = ffmpeg.input(processed_audio_path)

            # 定义帧交换索引映射函数
            def get_original_idx(output_idx, interval, total_frames):
                if interval <= 0 or not self.config.enable_frame_swap:
                    return output_idx
                k = output_idx // interval
                if output_idx % interval == 0 and k * interval + 1 < total_frames:
                    return k * interval + 1
                elif output_idx % interval == 1 and k * interval + 1 < total_frames:
                    return k * interval
                else:
                    return output_idx

            # 定义交换帧生成器
            def swapped_frame_generator(cap, total_frames, interval):
                output_idx = 0
                while output_idx < total_frames:
                    original_idx = get_original_idx(output_idx, interval, total_frames)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, original_idx)
                    ret, frame = cap.read()
                    if ret:
                        yield output_idx, frame
                        output_idx += 1
                    else:
                        break

            # 根据 enable_frame_swap 选择帧生成器
            if self.config.enable_frame_swap:
                frame_generator = swapped_frame_generator(cap, total_frames, self.config.frame_swap_interval)
            else:
                frame_generator = self._frame_generator(cap)

            # 分批处理视频帧
            processed_frame_generator = self._process_frames(frame_generator, total_frames, fps, height, width)
            self._write_frames(processed_frame_generator, output_path, width, height, fps, audio_stream)

        finally:
            cap.release()
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def _frame_generator(self, cap: cv2.VideoCapture) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        生成器：逐帧读取视频帧。

        参数:
            cap: OpenCV 视频捕获对象

        返回:
            Generator[Tuple[int, np.ndarray], None, None]: 帧索引和帧数据的生成器
        """
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            yield frame_idx, frame
            frame_idx += 1

    def _process_frames(self, frame_generator: Generator[Tuple[int, np.ndarray], None, None], 
                        total_frames: int, fps: float, orig_height: int, orig_width: int) -> Generator[np.ndarray, None, None]:
        """
        分批处理视频帧，并返回处理后的帧生成器。

        参数:
            frame_generator: 原始帧生成器
            total_frames: 视频总帧数
            fps: 视频帧率
            orig_height: 原始视频高度
            orig_width: 原始视频宽度

        返回:
            Generator[np.ndarray, None, None]: 处理后的帧生成器
        """
        batch = []
        for frame_idx, frame in frame_generator:
            batch.append((frame_idx, frame))
            if len(batch) >= self.batch_size:
                processed_batch = self._process_batch(batch, total_frames, fps, orig_height, orig_width)
                for _, processed_frame in processed_batch:
                    yield processed_frame
                batch = []
        if batch:
            processed_batch = self._process_batch(batch, total_frames, fps, orig_height, orig_width)
            for _, processed_frame in processed_batch:
                yield processed_frame

    def _process_batch(self, batch: List[Tuple[int, np.ndarray]], total_frames: int, fps: float, 
                       orig_height: int, orig_width: int) -> List[Tuple[int, np.ndarray]]:
        """
        并行处理一批视频帧。

        参数:
            batch: 待处理的帧批次
            total_frames: 视频总帧数
            fps: 视频帧率
            orig_height: 原始视频高度
            orig_width: 原始视频宽度

        返回:
            List[Tuple[int, np.ndarray]]: 处理后的帧列表，按帧索引排序
        """
        with ThreadPoolExecutor(max_workers=min(4, os.cpu_count())) as executor:
            futures = [executor.submit(self._process_single_frame, frame, idx, self.config, fps, total_frames, orig_height, orig_width)
                       for idx, frame in batch]
            return sorted([f.result() for f in futures], key=lambda x: x[0])

    def _process_single_frame(self, frame: np.ndarray, frame_idx: int, config: VideoConfig, 
                          fps: float, total_frames: int, orig_height: int, orig_width: int) -> Tuple[int, np.ndarray]:
        """
        处理单个视频帧，应用所有特效。
        
        参数:
            frame: 当前视频帧
            frame_idx: 当前帧索引
            config: 视频处理配置对象
            fps: 视频帧率
            total_frames: 视频总帧数
            orig_height: 原始视频高度
            orig_width: 原始视频宽度
        
        返回:
            Tuple[int, np.ndarray]: 帧索引和处理后的帧
        """
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if config.flip_horizontal:
            frame = cv2.flip(frame, 1)
        frame = VideoEffects.rotate_frame(frame, config)
        h, w = frame.shape[:2]
        
        # 应用按比例裁剪
        crop_h = int(orig_height * config.crop_percentage)
        crop_w = int(orig_width * config.crop_percentage)
        top, bottom, left, right = crop_h, crop_h, crop_w, crop_w
        if top + bottom < h and left + right < w:
            frame = frame[top:h - bottom, left:w - right]
        
        # 缩放回原始尺寸
        if frame.shape[0] != orig_height or frame.shape[1] != orig_width:
            frame = cv2.resize(frame, (orig_width, orig_height), interpolation=cv2.INTER_AREA)
        
        frame = VideoEffects.adjust_sbc(frame, config)
        if config.include_watermark:
            frame = VideoEffects.add_watermark(frame, config, frame_idx, total_frames, self)  # 传递 self
        if self.config.include_subtitles and self.subs:
            frame = VideoEffects.add_subtitles(frame, config, frame_idx, fps, self.subs)
        if self.config.include_titles:
            frame = VideoEffects.add_titles(frame, config)
        frame = VideoEffects.add_hzh_effect(frame, config, frame_idx, total_frames)
        frame = VideoEffects.color_shift(frame, config)
        frame = VideoEffects.blur_background(frame, config)
        frame = VideoEffects.scramble_phase(frame, config)
        frame = VideoEffects.add_texture_noise(frame, config)
        frame = VideoEffects.apply_edge_blur(frame, config)
        frame = VideoEffects.apply_gaussian_blur(frame, config, frame_idx)
        frame = VideoEffects.apply_fade_effect(frame, config, frame_idx, total_frames)
        
        return (frame_idx, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def _write_frames(self, frame_generator: Generator[np.ndarray, None, None], output_path: str, 
                      width: int, height: int, fps: float, audio_stream: ffmpeg.Stream) -> None:
        """
        将处理后的帧写入输出视频。

        参数:
            frame_generator: 处理后的帧生成器
            output_path: 输出视频文件路径
            width: 原始视频宽度
            height: 原始视频高度
            fps: 视频帧率
            audio_stream: 处理后的音频流
        """
        first_frame = next(frame_generator)
        adjusted_width, adjusted_height = first_frame.shape[1], first_frame.shape[0]
        video_stream = ffmpeg.input('pipe:', format='rawvideo', pix_fmt='bgr24', 
                                    s=f'{adjusted_width}x{adjusted_height}', framerate=fps)
        process = video_stream.output(
            audio_stream, output_path, vcodec='libx264', acodec='aac', preset='fast', 
            crf=23, **{'b:v': '2M'}, r=fps, s=f'{adjusted_width}x{adjusted_height}'
        ).overwrite_output().run_async(pipe_stdin=True)
        process.stdin.write(first_frame.tobytes())
        for frame in frame_generator:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        process.wait()
        logging.info(f"视频处理完成，输出到 {output_path}")

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="python dedup.py -i input.mp4 -o output.mp4")
    parser.add_argument("-i", "--input", required=True, help="输入视频文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出视频文件路径")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 创建配置对象
    config = VideoConfig()
    # 初始化视频处理器
    processor = VideoHandler(config)
    # 处理视频并保存
    processor.process_video(args.input, args.output)