#!/usr/bin/env python3
"""
LoTW 数据库自动更新脚本
从 ARRL 下载最新的 LoTW 用户活动数据
"""
import os
import sys
import csv
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# 配置
LOTW_URL = "https://lotw.arrl.org/lotw-user-activity.csv"
CSV_FILE = "/home/jacky/.openclaw/workspace/lotw-user-activity.csv"
BACKUP_DIR = "/home/jacky/.openclaw/workspace/backups/lotw"

def ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)

def download_lotw() -> bool:
    """下载 LoTW 数据"""
    print(f"📥 正在从 ARRL 下载 LoTW 数据...")
    print(f"   URL: {LOTW_URL}")
    
    try:
        req = urllib.request.Request(
            LOTW_URL,
            headers={
                'User-Agent': 'DX-Guardian/1.0 (Amateur Radio Tool)'
            }
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()
        
        # 备份旧文件
        if os.path.exists(CSV_FILE):
            ensure_dir(BACKUP_DIR)
            backup_file = f"{BACKUP_DIR}/lotw-user-activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            os.replace(CSV_FILE, backup_file)
            print(f"   ✅ 已备份旧文件: {backup_file}")
        
        # 写入新文件
        with open(CSV_FILE, 'wb') as f:
            f.write(data)
        
        file_size = len(data)
        print(f"   ✅ 下载成功: {file_size:,} bytes")
        
        # 验证文件
        line_count = 0
        with open(CSV_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    line_count += 1
        
        print(f"   📊 包含 {line_count:,} 条记录")
        return True
        
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP 错误: {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"   ❌ 网络错误: {e.reason}")
        return False
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return False

def main():
    print("=" * 50)
    print("DX Guardian - LoTW 数据库更新")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    success = download_lotw()
    
    if success:
        print("\n🎉 LoTW 数据库更新完成!")
        return 0
    else:
        print("\n💥 更新失败，请检查网络连接")
        return 1

if __name__ == "__main__":
    sys.exit(main())