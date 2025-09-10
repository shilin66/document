#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出Minio存储桶内容
"""

from minio import Minio
import json

def list_bucket_contents():
    """列出存储桶所有内容"""
    
    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    minio_config = config['minio']
    
    try:
        # 创建客户端
        client = Minio(
            endpoint=minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config['secure']
        )
        
        bucket_name = minio_config['bucket_name']
        print(f"=== 存储桶 '{bucket_name}' 内容 ===")
        
        # 列出所有对象
        objects = client.list_objects(bucket_name, recursive=True)
        
        count = 0
        for obj in objects:
            print(f"  {obj.object_name}")
            count += 1
        
        if count == 0:
            print("  存储桶为空")
        else:
            print(f"\n总计: {count} 个对象")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    list_bucket_contents()