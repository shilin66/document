#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minio上传工具模块
用于将生成的报告文件上传到Minio存储桶
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from minio import Minio
from minio.error import S3Error


class MinioUploader:
    """Minio文件上传器"""
    
    def __init__(self, minio_config: Dict[str, Any]):
        """
        初始化Minio上传器
        
        Args:
            minio_config: Minio连接配置
        """
        self.config = minio_config
        self.client = Minio(
            endpoint=minio_config.get('endpoint'),
            access_key=minio_config.get('access_key'),
            secret_key=minio_config.get('secret_key'),
            secure=minio_config.get('secure', True)
        )
        self.bucket_name = minio_config.get('bucket_name', 'report')
    
    def upload_report(self, local_file_path: str, minio_path: Optional[str] = None, 
                     preserve_local_structure: bool = True) -> str:
        """
        上传报告文件到Minio
        
        Args:
            local_file_path: 本地文件路径
            minio_path: Minio中的目标路径，如果为None则自动生成
            preserve_local_structure: 是否保持本地目录结构
            
        Returns:
            str: Minio中的文件路径
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"本地文件不存在: {local_file_path}")
        
        # 生成Minio路径
        if minio_path is None:
            if preserve_local_structure:
                # 保持本地目录结构
                minio_path = local_file_path.replace('\\', '/')
            else:
                # 只使用文件名
                minio_path = os.path.basename(local_file_path)
        
        try:
            # 确保存储桶存在
            if not self.client.bucket_exists(self.bucket_name):
                print(f"存储桶 '{self.bucket_name}' 不存在，正在创建...")
                self.client.make_bucket(self.bucket_name)
            
            # 上传文件
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=minio_path,
                file_path=local_file_path
            )
            
            print(f"✓ 文件上传成功: {local_file_path} -> minio://{self.bucket_name}/{minio_path}")
            return f"minio://{self.bucket_name}/{minio_path}"
            
        except S3Error as e:
            print(f"✗ Minio上传失败: {e}")
            raise
        except Exception as e:
            print(f"✗ 文件上传失败: {e}")
            raise
    
    def upload_with_date_structure(self, local_file_path: str, base_upload_path: str = "核心网络部运维报告/输出") -> str:
        """
        按日期结构上传文件到Minio
        
        Args:
            local_file_path: 本地文件路径
            base_upload_path: Minio中的基础路径
            
        Returns:
            str: Minio中的文件路径
        """
        # 生成日期路径
        date_str = datetime.now().strftime('%Y%m%d')
        filename = os.path.basename(local_file_path)
        
        # 构建Minio路径
        minio_path = f"{base_upload_path}/{date_str}/{filename}"
        
        return self.upload_report(local_file_path, minio_path, preserve_local_structure=False)
    
    def get_upload_url(self, minio_path: str, expires_days: int = 7) -> str:
        """
        生成文件的预签名下载URL
        
        Args:
            minio_path: Minio中的文件路径
            expires_days: URL有效期（天）
            
        Returns:
            str: 预签名URL
        """
        try:
            from datetime import timedelta
            expires = timedelta(days=expires_days)
            
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=minio_path,
                expires=expires
            )
            
            return url
            
        except Exception as e:
            print(f"生成下载URL失败: {e}")
            return ""
    
    def list_uploaded_reports(self, prefix: str = "核心网络部运维报告/输出") -> list:
        """
        列出已上传的报告文件
        
        Args:
            prefix: 路径前缀
            
        Returns:
            list: 文件列表
        """
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            
            files = []
            for obj in objects:
                files.append({
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'etag': obj.etag
                })
            
            return files
            
        except Exception as e:
            print(f"列出文件失败: {e}")
            return []
    
    def delete_report(self, minio_path: str) -> bool:
        """
        删除Minio中的报告文件
        
        Args:
            minio_path: Minio中的文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            self.client.remove_object(self.bucket_name, minio_path)
            print(f"✓ 文件删除成功: minio://{self.bucket_name}/{minio_path}")
            return True
            
        except Exception as e:
            print(f"✗ 文件删除失败: {e}")
            return False