import os
import json
import shutil
import asyncio
import dashscope
from pathlib import Path
from dashscope import MultiModalConversation

from conf import BASE_DIR
from utils.constant import TencentZoneTypes
from uploader.tencent_uploader.main import weixin_setup, TencentVideo

class AIAnalyzer:
    """AI分析类：负责视频分析生成标题与标签"""

    @staticmethod
    def ai_analyze_video(video_path: str, title_and_tags: str) -> dict:
        """使用AI分析视频，生成标题和标签

        Args:
            video_path (str): 视频文件路径

        Returns:
            dict: 包含标题和标签的字典，例如 {'title': '标题', 'tag': '标签1,标签2'}
        """

        try:
            # api_key需要在阿里百云炼里面注册获取：https://bailian.console.aliyun.com/
            dashscope.api_key = "sk-5b85fdd313xxxxxx8f4e0e1a37722230"
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": """
                        你是一位拥有10年经验的资深短视频运营专家，擅长跨平台内容重构与爆款公式设计，你会分析TikTok短视频的内容及其标题、标签的好奇心触发点，结合中国用户心理、利用悬念前置、感官刺激、认知冲突等钩子设计爆款中文标题和热门中文标签（标题中可以适当使用1-2个表情图标，标签数量大于8个），严格按照以下格式且仅输出以下格式的结果：
                            {
                                \"title\": \"标题\",
                                \"tag\": \"标签1,标签2,标签3...\"
                            }
                        """}]
                },
                {
                    "role": "user",
                    "content": [
                        {"video": f"file://{video_path}"},
                        {"text": f"{title_and_tags}"}
                    ]
                }
            ]
            responses = MultiModalConversation.call(
                model="qwen-vl-max-latest",
                messages=messages,
                stream=True,
                incremental_output=True,
                timeout=30
            )
            full_content = []
            for response in responses:
                try:
                    content = response["output"]["choices"][0]["message"]["content"]
                    if content and isinstance(content, list) and "text" in content[0]:
                        text_content = content[0]["text"]
                        full_content.append(text_content)
                except (KeyError, IndexError) as error:
                    print(f"解析响应时出错: {error}")
                except Exception as e:
                    print(f"未知错误: {e}")
            return json.loads(''.join(full_content))
        except Exception as e:
            print(f"AI生成标题+标签失败: {str(e)}")
            return {'title': '', 'tag': ''}

class Uploader:
    """上传类：负责视频上传到腾讯视频平台"""

    @staticmethod
    async def upload_video(file_path: Path, title: str, tags: list[str], account_file: Path) -> None:
        """上传视频到腾讯视频平台

        Args:
            file_path (Path): 视频文件路径
            title (str): 视频标题
            tags (list[str]): 视频标签列表
            account_file (Path): 账号配置文件路径
        """
        app = TencentVideo(
            title=title,
            file_path=file_path,
            tags=tags,
            publish_date=0,
            account_file=account_file,
            category=TencentZoneTypes.CUTE_PETS.value
        )
        await app.main()

class Utils:
    """工具类：提供通用工具函数"""

    @staticmethod
    def empty_directory(upload_video_path: Path) -> None:
        """清空指定目录中的所有文件和子目录

        Args:
            upload_video_path (Path): 要清空的目录路径
        """
        if os.path.exists(upload_video_path) and os.path.isdir(upload_video_path):
            for root, dirs, files in os.walk(upload_video_path, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"删除 {file_path} 发生错误: {e}")
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        shutil.rmtree(dir_path)
                    except Exception as e:
                        print(f"删除 {dir_path} 发生错误: {e}")
        else:
            print(f"{upload_video_path} 不存在!")

async def main() -> None:
    """主程序：协调视频上传流程"""
    upload_video_path = Path(BASE_DIR) / "videos"
    download_video_path = Path(BASE_DIR).parent / 'Download/tiktok/post/astrospaceq'
    account_file = Path(BASE_DIR / "cookies/tencent_uploader/account.json")


    try:
        await weixin_setup(account_file, handle=True)

        video_path_list = list(upload_video_path.glob("*.mp4"))

        if not upload_video_path.exists() or len(video_path_list) == 0:
            print("没有需要上传的视频文件")
            exit(0)

        for video_path in video_path_list:
            print("AI生成标题+标签开始...")
            video_time = video_path.name.replace('_video.mp4', '')
            with open(file=str(download_video_path / video_time / f'{video_time}_desc.txt'), mode='r') as f:
                title_and_tags = f.read()
            ai_result = AIAnalyzer.ai_analyze_video(video_path=str(video_path), title_and_tags=title_and_tags)
            title = ai_result['title']
            tags = ai_result['tag'].split(',')
            print(f"AI生成标题+标签完成: \n标题: {title}\n标签: {tags}")

            await Uploader.upload_video(video_path, title, tags, account_file)

        Utils.empty_directory(upload_video_path)

    except Exception as e:
        print(f"上传过程中发生严重错误: {str(e)}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
