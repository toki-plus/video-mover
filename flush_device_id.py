# -*- coding: utf-8 -*-

import os
import sys
import asyncio
from f2.apps.tiktok.utils import DeviceIdManager
from ruamel.yaml import YAML

async def main():
    device_id = await DeviceIdManager.gen_device_id(full_cookie=True)
    print("device_id:", device_id.get("deviceId"))

    # 初始化ruamel.yaml实例
    yaml = YAML()
    yaml.preserve_quotes = True  # 保留字符串的引号格式

    # 处理 conf.yaml
    conf_dir = os.path.join(
        sys.prefix,  # Python安装目录
        'Lib', 
        'site-packages', 
        'f2', 
        'conf'
    )
    conf_path = os.path.join(conf_dir, 'conf.yaml')
    with open(conf_path, "r") as f:
        data = yaml.load(f) or {}
        # 确保嵌套字典存在
        data.setdefault('f2', {}).setdefault('tiktok', {}).setdefault('BaseRequestModel', {}).setdefault('device', {})['id'] = device_id.get("deviceId")
    
    with open(conf_path, "w") as f:
        yaml.dump(data, f)
        

    # 处理 my_apps.yaml
    apps_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_apps.yaml')

    cookie = device_id.get("cookie")
    new_cookie_dict = dict(
        item.strip().split('=', 1) 
        for item in cookie.split(';') 
        if '=' in item
    )

    with open(apps_path, "r") as f:
        data = yaml.load(f) or {}
        
        # 合并Cookies
        existing_cookie = data.setdefault('tiktok', {}).get('cookie', '')
        existing_cookie_dict = dict(
            item.strip().split('=', 1)
            for item in existing_cookie.split(';')
            if '=' in item
        )
        existing_cookie_dict.update(new_cookie_dict)
        
        data['tiktok']['cookie'] = '; '.join(f"{k}={v}" for k, v in existing_cookie_dict.items())

    with open(apps_path, "w") as f:
        yaml.dump(data, f)

if __name__ == "__main__":
    asyncio.run(main())

