#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minio文件扫描器模块
用于从Minio存储桶中扫描和下载docx和xlsx文件
"""

import os
import tempfile
from typing import Dict, List
from minio import Minio
from minio.error import S3Error
from temp_utils import create_minio_temp_dir
from datetime import datetime, timedelta


class MinioFileScanner:
    """Minio文件扫描器类"""
    
    def __init__(self, minio_config: dict, bucket_name: str = "report", base_prefix: str = "核心网络部运维报告"):
        """
        初始化Minio文件扫描器
        
        Args:
            minio_config: Minio连接配置
            bucket_name: 存储桶名称，默认为'report'
            base_prefix: 基础目录前缀，默认为'核心网络部运维报告'
        """
        self.bucket_name = bucket_name
        self.base_prefix = base_prefix
        self.supported_extensions = ['.docx', '.xlsx', '.pdf']
        
        # 初始化Minio客户端
        self.client = Minio(
            endpoint=minio_config.get('endpoint'),
            access_key=minio_config.get('access_key'),
            secret_key=minio_config.get('secret_key'),
            secure=minio_config.get('secure', True)
        )
        
        # 创建临时目录用于存储下载的文件
        self.temp_dir = create_minio_temp_dir()
        print(f"临时文件目录: {self.temp_dir}")
    
    def scan_files(self, target_date: str = None) -> Dict[str, List[str]]:
        """
        扫描Minio存储桶中的所有docx、xlsx和pdf文件，并下载到本地临时目录
        
        Args:
            target_date: 目标日期，格式为YYYYMM。如果为None，则使用上个月
            
        Returns:
            Dict[str, List[str]]: 以目录名为键，本地文件路径列表为值的字典
        """
        file_dict = {}
        
        # 如果没有指定日期，则使用上个月
        if target_date is None:
            # 获取上个月的年月
            today = datetime.today()
            first_day_current_month = today.replace(day=1)
            last_month = first_day_current_month - timedelta(days=1)
            target_date = last_month.strftime("%Y%m")
        
        print(f"目标日期目录: {target_date}")
        
        try:
            # 检查存储桶是否存在
            if not self.client.bucket_exists(self.bucket_name):
                print(f"存储桶 '{self.bucket_name}' 不存在")
                return file_dict
            
            # 列出指定前缀下的所有对象
            prefix = f"{self.base_prefix}/" if self.base_prefix else ""
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)

            for obj in objects:
                object_name = obj.object_name
                print(f"正在处理: {object_name}")
                # 过滤掉临时文件（以~$开头的文件）
                if os.path.basename(object_name).startswith('~$'):
                    continue
                
                # 查是否在目标日期目录下
                # 精确匹配：确保目标日期是作为目录层级出现的，而不是文件名的一部分
                target_date_dir = f"/{target_date}/"
                if target_date_dir not in object_name:
                    continue
                
                # 排除目录本身
                if object_name.endswith(target_date_dir):
                    continue
                
                # 检查文件扩展名
                _, ext = os.path.splitext(object_name)
                if ext.lower() not in self.supported_extensions:
                    continue
                
                # 下载文件到本地临时目录
                local_file_path = self._download_file(object_name)
                if local_file_path:
                    # 根据Minio路径结构组织文件
                    directory_name = self._extract_directory_name(object_name)
                    
                    if directory_name not in file_dict:
                        file_dict[directory_name] = []
                    
                    file_dict[directory_name].append(local_file_path)
            
            print(f"从Minio扫描到 {sum(len(files) for files in file_dict.values())} 个文件")
            
        except S3Error as e:
            print(f"Minio连接错误: {e}")
        except Exception as e:
            print(f"文件扫描出错: {e}")
        
        return file_dict
    
    def _download_file(self, object_name: str) -> str:
        """
        下载单个文件到本地临时目录
        
        Args:
            object_name: Minio中的对象名称
            
        Returns:
            str: 本地文件路径，失败时返回None
        """
        try:
            # 安全地处理文件名，移除路径中的特殊字符
            safe_object_name = object_name.replace('/', os.sep)
            
            # 创建本地文件路径，保持目录结构
            local_path = os.path.join(self.temp_dir, safe_object_name)
            
            # 规范化路径以确保在Linux和Windows上都能正常工作
            local_path = os.path.normpath(local_path)
            
            # 确保目录存在
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            # 下载文件
            self.client.fget_object(self.bucket_name, object_name, local_path)
            
            # 验证文件确实已下载
            if os.path.exists(local_path):
                print(f"已下载: {object_name} -> {local_path}")
                return local_path
            else:
                print(f"下载文件失败，文件不存在: {local_path}")
                return None
            
        except Exception as e:
            print(f"下载文件失败 {object_name}: {e}")
            return None
    
    def _extract_directory_name(self, object_name: str) -> str:
        """
        从对象名称中提取目录名称，处理基础前缀
        
        Args:
            object_name: Minio对象名称
            
        Returns:
            str: 目录名称
        """
        # 移除基础前缀
        if self.base_prefix and object_name.startswith(f"{self.base_prefix}/"):
            relative_path = object_name[len(f"{self.base_prefix}/"):]
        else:
            relative_path = object_name
        
        # 去除文件名，只保留目录部分
        directory_path = os.path.dirname(relative_path)
        
        if not directory_path:
            return "根目录"
        
        # 返回最后一级目录名（跳过日期目录）
        path_parts = directory_path.split('/')
        if len(path_parts) >= 2 and path_parts[-1].isdigit() and len(path_parts[-1]) == 6:
            # 如果最后一级是6位数字的日期目录，则返回上一级目录
            return path_parts[-2]
        else:
            # 否则返回最后一级目录
            return path_parts[-1]
    
    def cleanup(self):
        """清理临时文件"""
        from temp_utils import cleanup_temp_dir
        cleanup_temp_dir(self.temp_dir)
    
    def __del__(self):
        """析构函数，自动清理临时文件"""
        self.cleanup()


class MinioConfig:
    """Minio配置类"""
    
    @staticmethod
    def load_from_env():
        """从环境变量加载Minio配置"""
        return {
            'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            'access_key': os.getenv('MINIO_ACCESS_KEY'),
            'secret_key': os.getenv('MINIO_SECRET_KEY'),
            'secure': os.getenv('MINIO_SECURE', 'True').lower() == 'true'
        }
    
    @staticmethod
    def create_config(endpoint: str, access_key: str, secret_key: str, secure: bool = True):
        """创建Minio配置"""
        return {
            'endpoint': endpoint,
            'access_key': access_key,
            'secret_key': secret_key,
            'secure': secure
        }