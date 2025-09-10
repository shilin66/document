#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件模块
用于管理Minio连接配置和其他系统配置
"""

import os
import json
from typing import Dict, Any, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "minio": {
                "endpoint": "localhost:9000",
                "access_key": "",
                "secret_key": "",
                "secure": False,
                "bucket_name": "report",
                "base_prefix": "核心网络部运维报告"
            },
            "local": {
                "base_path": "核心网络部运维报告"
            },
            "output": {
                "base_directory": "核心网络部运维报告",
                "create_date_folder": True,
                "date_format": "%Y%m%d",
                "upload_to_minio": True,
                "minio_upload_path": "核心网络部运维报告/输出"
            },
            "pdf_api_url": "http://187.9.9.8:7434/v2/parse/file",
            "pdf_parse_mode": "api",
            "pdf_to_image_dpi": 200,
            "temp_dir": "./tmp/minio_files"
        }
        
        # 只在Windows系统上设置默认poppler_path
        import sys
        if sys.platform == 'win32':
            default_config["poppler_path"] = "D:/poppler-25.07.0/Library/bin"
        
        # 如果配置文件存在，加载配置
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # 合并默认配置和文件配置
                    default_config.update(file_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}，使用默认配置")
        else:
            # 创建默认配置文件
            self.save_config(default_config)
            print(f"已创建默认配置文件: {self.config_file}")
        
        # 从环境变量覆盖配置
        env_config = self.load_env_config()
        if env_config:
            self._deep_update(default_config, env_config)
        
        return default_config
    
    def load_env_config(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        env_config = {}
        
        # Minio配置
        minio_config = {}
        if os.getenv('MINIO_ENDPOINT'):
            minio_config['endpoint'] = os.getenv('MINIO_ENDPOINT')
        if os.getenv('MINIO_ACCESS_KEY'):
            minio_config['access_key'] = os.getenv('MINIO_ACCESS_KEY')
        if os.getenv('MINIO_SECRET_KEY'):
            minio_config['secret_key'] = os.getenv('MINIO_SECRET_KEY')
        if os.getenv('MINIO_SECURE'):
            minio_config['secure'] = os.getenv('MINIO_SECURE').lower() == 'true'
        if os.getenv('MINIO_BUCKET_NAME'):
            minio_config['bucket_name'] = os.getenv('MINIO_BUCKET_NAME')
        
        if minio_config:
            env_config['minio'] = minio_config
        
        # 其他配置
        if os.getenv('PDF_API_URL'):
            env_config['pdf_api_url'] = os.getenv('PDF_API_URL')
        if os.getenv('PDF_PARSE_MODE'):
            env_config['pdf_parse_mode'] = os.getenv('PDF_PARSE_MODE')
        if os.getenv('PDF_TO_IMAGE_DPI'):
            try:
                env_config['pdf_to_image_dpi'] = int(os.getenv('PDF_TO_IMAGE_DPI'))
            except ValueError:
                pass
        if os.getenv('POPPLER_PATH'):
            env_config['poppler_path'] = os.getenv('POPPLER_PATH')
        if os.getenv('TEMP_DIR'):
            env_config['temp_dir'] = os.getenv('TEMP_DIR')
        if os.getenv('OUTPUT_BASE_DIR'):
            if 'output' not in env_config:
                env_config['output'] = {}
            env_config['output']['base_directory'] = os.getenv('OUTPUT_BASE_DIR')
        if os.getenv('LOCAL_BASE_PATH'):
            if 'local' not in env_config:
                env_config['local'] = {}
            env_config['local']['base_path'] = os.getenv('LOCAL_BASE_PATH')
        
        return env_config
    
    def save_config(self, config: Dict[str, Any] = None):
        """保存配置到文件"""
        config_to_save = config or self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_minio_config(self) -> Dict[str, Any]:
        """获取Minio配置"""
        return self.config.get('minio', {})
    
    def get_poppler_path(self) -> str:
        """获取Poppler路径"""
        import sys
        
        # 在Linux系统上，poppler通常通过包管理器安装，不需要指定路径
        if sys.platform.startswith('linux'):
            return None
        
        # Windows系统需要指定poppler路径
        return self.config.get('poppler_path', '')
    
    def get_temp_dir(self) -> str:
        """获取临时目录路径"""
        return self.config.get('temp_dir', './tmp/minio_files')
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.config.get('output', {})
    
    def get_local_config(self) -> Dict[str, Any]:
        """获取本地配置"""
        return self.config.get('local', {})
    
    def get_pdf_api_url(self) -> str:
        """获取PDF解析API地址"""
        return self.config.get('pdf_api_url', 'http://187.9.9.8:7434/v2/parse/file')
    
    def get_pdf_parse_mode(self) -> str:
        """获取PDF解析模式: 'api' 或 'image'"""
        return self.config.get('pdf_parse_mode', 'api')
    
    def get_pdf_to_image_dpi(self) -> int:
        """获取PDF转图片的DPI设置"""
        return self.config.get('pdf_to_image_dpi', 200)
    
    def validate_minio_config(self) -> bool:
        """验证Minio配置是否完整"""
        minio_config = self.get_minio_config()
        required_fields = ['endpoint', 'access_key', 'secret_key']
        
        for field in required_fields:
            if not minio_config.get(field):
                print(f"Minio配置缺少必需字段: {field}")
                return False
        
        return True
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """递归更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def update_config(self, new_config: Dict[str, Any], save_to_file: bool = True):
        """更新配置"""
        self._deep_update(self.config, new_config)
        if save_to_file:
            self.save_config()


def create_sample_config():
    """创建示例配置文件"""
    sample_config = {
        "minio": {
            "endpoint": "your-minio-server:9000",
            "access_key": "your-access-key",
            "secret_key": "your-secret-key",
            "secure": True,
            "bucket_name": "report"
        },
        "pdf_api_url": "http://187.9.9.8:7434/v2/parse/file",
        "pdf_parse_mode": "api",
        "pdf_to_image_dpi": 200,
        "temp_dir": "./tmp/minio_files"
    }
    
    # 只在Windows系统上添加poppler_path配置
    import sys
    if sys.platform == 'win32':
        sample_config["poppler_path"] = "D:/poppler-25.07.0/Library/bin"
    
    config_file = "config.sample.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    print(f"已创建示例配置文件: {config_file}")
    print("请复制为 config.json 并修改相应配置")


if __name__ == "__main__":
    # 创建示例配置文件
    create_sample_config()
    
    # 测试配置加载
    config = Config()
    print("当前配置:")
    print(json.dumps(config.config, indent=2, ensure_ascii=False))