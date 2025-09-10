#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件扫描器模块
用于扫描指定目录下的docx和xlsx文件
"""

import os
from typing import Dict, List

class FileScanner:
    """文件扫描器类"""
    
    def __init__(self, base_path: str = "核心网络部运维报告"):
        self.base_path = base_path
        self.supported_extensions = ['.docx', '.xlsx', '.pdf']
    
    def scan_files(self) -> Dict[str, List[str]]:
        """
        扫描所有子目录中的docx、xlsx和pdf文件
        
        Returns:
            Dict[str, List[str]]: 以目录名为键，文件路径列表为值的字典
        """
        file_dict = {}
        
        if not os.path.exists(self.base_path):
            return file_dict
        
        # 遍历所有子目录
        for item in os.listdir(self.base_path):
            item_path = os.path.join(self.base_path, item)
            
            if os.path.isdir(item_path):
                files = self._scan_directory(item_path)
                if files:
                    file_dict[item] = files
        
        return file_dict
    
    def _scan_directory(self, directory_path: str) -> List[str]:
        """
        扫描单个目录中的文件
        
        Args:
            directory_path: 目录路径
            
        Returns:
            List[str]: 符合条件的文件路径列表
        """
        files = []
        
        try:
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                
                if os.path.isfile(file_path):
                    # 过滤掉Word临时文件（以~$开头的文件）
                    if file.startswith('~$'):
                        continue
                        
                    # 检查文件扩展名
                    _, ext = os.path.splitext(file)
                    if ext.lower() in self.supported_extensions:
                        files.append(file_path)
        
        except Exception:
            pass
        
        return files