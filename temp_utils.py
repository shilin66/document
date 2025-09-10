#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时目录管理工具
统一管理项目中的临时文件和目录创建
"""

import os
from datetime import datetime
from typing import Optional


def get_project_temp_dir(sub_dir: Optional[str] = None) -> str:
    """
    获取项目临时目录路径
    
    Args:
        sub_dir: 子目录名称（可选）
        
    Returns:
        str: 临时目录路径
    """
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 创建tmp目录
    temp_base = os.path.join(current_dir, 'tmp')
    
    if sub_dir:
        temp_dir = os.path.join(temp_base, sub_dir)
    else:
        temp_dir = temp_base
    
    # 确保目录存在
    os.makedirs(temp_dir, exist_ok=True)
    
    return temp_dir


def create_date_temp_dir(prefix: str = "") -> str:
    """
    创建带日期的临时目录
    
    Args:
        prefix: 目录前缀
        
    Returns:
        str: 临时目录路径
    """
    date_str = datetime.now().strftime('%Y%m%d')
    
    if prefix:
        sub_dir = f"{prefix}_{date_str}"
    else:
        sub_dir = date_str
    
    return get_project_temp_dir(sub_dir)


def create_minio_temp_dir() -> str:
    """
    创建MinIO文件下载临时目录
    
    Returns:
        str: MinIO临时目录路径
    """
    return get_project_temp_dir('minio_files')


def create_pdf_images_temp_dir() -> str:
    """
    创建PDF图片临时目录
    
    Returns:
        str: PDF图片临时目录路径
    """
    date_str = datetime.now().strftime('%Y%m%d')
    return get_project_temp_dir(f'pdf_images_{date_str}')


def create_excel_temp_dir() -> str:
    """
    创建Excel处理临时目录
    
    Returns:
        str: Excel临时目录路径
    """
    date_str = datetime.now().strftime('%Y%m%d')
    return get_project_temp_dir(f'excel_{date_str}')


def cleanup_temp_dir(temp_dir: str):
    """
    清理临时目录
    
    Args:
        temp_dir: 要清理的临时目录路径
    """
    import shutil
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"已清理临时目录: {temp_dir}")
    except Exception as e:
        print(f"清理临时目录失败: {e}")


# 向后兼容的函数
def get_temp_dir_path(sub_path: str = "") -> str:
    """
    获取临时目录路径（向后兼容）
    
    Args:
        sub_path: 子路径
        
    Returns:
        str: 临时目录路径
    """
    return get_project_temp_dir(sub_path)