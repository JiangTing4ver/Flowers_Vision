
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
花卉数据集下载脚本

使用方法:
1. 在命令行中进入此文件所在目录
2. 执行: python load.py

此脚本会:
- 从Roboflow下载花卉数据集
- 解压数据集到当前目录
- 删除临时zip文件
"""

import os
import sys
import time
import requests
from zipfile import ZipFile

# 数据集URL和文件名
DATASET_URL = "https://universe.roboflow.com/ds/C7LjJMLjrb?key=6M8uGq2WmO"
ZIP_FILE = "roboflow.zip"

print("开始下载花卉数据集...")

# 使用requests下载文件，添加用户代理避免403错误
try:
    # 添加用户代理和其他headers以避免403禁止访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2'
    }
    
    print(f"正在尝试访问: {DATASET_URL}")
    print("提示: 如果下载失败，您可以手动访问此URL下载数据集")
    
    # 设置超时和重试机制
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.get(DATASET_URL, stream=True, headers=headers, timeout=30)
            
            # 检查状态码
            if response.status_code == 403:
                print(f"错误: 403 禁止访问 (尝试 {retry_count + 1}/{max_retries})")
                print("这通常意味着服务器拒绝了请求，可能是因为:")
                print("1. 链接可能已过期或无效")
                print("2. 需要登录后才能访问")
                print("3. 请求频率过高")
                
                retry_count += 1
                if retry_count < max_retries:
                    print(f"等待5秒后重试...")
                    time.sleep(5)
                    continue
                else:
                    print("已达到最大重试次数")
                    response.raise_for_status()
            else:
                response.raise_for_status()  # 检查其他错误
                break  # 成功则跳出循环
                
        except requests.exceptions.Timeout:
            retry_count += 1
            print(f"错误: 连接超时 (尝试 {retry_count}/{max_retries})")
            if retry_count < max_retries:
                print(f"等待5秒后重试...")
                time.sleep(5)
            else:
                print("已达到最大重试次数")
                raise
    
    # 获取文件大小（如果服务器提供）
    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0
    
    with open(ZIP_FILE, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                # 显示下载进度（如果知道总大小）
                if total_size > 0:
                    progress = (downloaded_size / total_size) * 100
                    sys.stdout.write(f"\r下载进度: {progress:.1f}% ({downloaded_size/1024/1024:.1f} MB)")
                    sys.stdout.flush()
    
    print(f"\n数据集下载完成，保存为 {ZIP_FILE}")
    
    # 解压文件
    print("开始解压数据集...")
    with ZipFile(ZIP_FILE, 'r') as zip_ref:
        zip_ref.extractall('.')
    
    print("数据集解压完成")
    
    # 删除zip文件
    os.remove(ZIP_FILE)
    print(f"已删除临时文件 {ZIP_FILE}")
    print("数据集准备完成，可以开始使用了！")
    
except requests.exceptions.RequestException as e:
    print(f"网络请求错误: {e}")
    print("\n建议手动下载解决方案:")
    print(f"1. 打开浏览器，访问: {DATASET_URL}")
    print("2. 下载zip文件并保存为 'roboflow.zip'")
    print("3. 将zip文件放在此脚本所在目录")
    print("4. 再次运行脚本，它将尝试解压已下载的文件")
    
except Exception as e:
    print(f"出现错误: {e}")
finally:
    # 确保在出现错误时也清理临时文件
    if os.path.exists(ZIP_FILE):
        os.remove(ZIP_FILE)
        print(f"\n已清理临时文件 {ZIP_FILE}")