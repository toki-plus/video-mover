### 前置条件

- dotnet：https://dotnet.microsoft.com/en-us/download/dotnet-framework/thank-you/net48-web-installer
- V2rayn：https://github.com/2dust/v2rayN/releases/download/5.39/v2rayN-Core.zip
- Chrome：https://www.google.com/
- Python：https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
- Node.js：https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi
- Git：https://git-scm.com/downloads/win
- VSCode：https://code.visualstudio.com/Download
- ffmpeg：https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-full_build.7z

### 修改步骤

1. 双击`setup.bat`安装环境

2. 修改`C:/Program Files/Python312/Lib/site-packages/f2/apps/tiktok/handler.py`第389行，将`cursor`改为`int(cursor)`

3. 修改`C:/Program Files/Python312/Lib/site-packages/f2/utils/utils.py`

   ```python
   # 第200行，将：
   if date_type == "start":
       date_str = f"{start_date} 00-00-00"
   elif date_type == "end":
       date_str = f"{end_date} 23-59-59"
   else:
       logger.warning(_("不支持的日期类型：{0}").format(date_type))
       return 0
   # 改为：
   if len(start_date.split()) == 1:
       if date_type == "start":
           date_str = f"{start_date} 00-00-00"
       elif date_type == "end":
           date_str = f"{end_date} 23-59-59"
       else:
           logger.warning(_("不支持的日期类型：{0}").format(date_type))
           return 0
   else:
       if date_type == "start":
           date_str = f"{start_date}"
       elif date_type == "end":
           date_str = f"{end_date}"
       else:
           logger.warning(_("不支持的日期类型：{0}").format(date_type))
           return 0
   

   # 第690行，将：
   start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
   end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d") + datetime.timedelta(
       days=1, seconds=-1
   )
   
   # 改为：
   if len(start_str.split()) == 1:
       start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
   else:
       start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d %H-%M-%S")
   if len(end_str.split()) == 1:
       end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d") + datetime.timedelta(days=1, seconds=-1)
   else:
       end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d %H-%M-%S")
   ```

4. 修改`C:\Users\Administrator\Desktop\mover_v3\Upload\uploader\tencent_uploader\main.py`

   ```python
   # 第191行，将：
   await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=1500)
   
   # 改为：
   await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=10000)
   ```

5. 访问`TikTok`网页获取`Cookie`并将其替换到`my_apps.yaml`中

6. 双击`start.bat`，等待登陆后点击开发者工具的绿色三角形箭头

7. （可选）修改`mover_v3`目录下`my_apps.yaml`中的`Proxy`配置

