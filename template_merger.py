#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心模板合并器模块
专注于保持源文件格式的模板变量替换
"""

import os
import re
from datetime import datetime
from typing import Dict, Any
from docx import Document
from docx.shared import Cm
from docxtpl import DocxTemplate, InlineImage

try:
    from minio_uploader import MinioUploader
except ImportError:
    MinioUploader = None


class CoreTemplateMerger:
    """核心模板合并器类，专注于格式保持的变量替换"""
    
    def __init__(self, template_path: str = "template.docx", config=None):
        """
        初始化模板合并器
        
        Args:
            template_path: 模板文件路径
            config: 配置对象
        """
        self.template_path = template_path
        self.config = config
        self.variable_pattern = re.compile(r'\{\{(\w+)\}\}')
    
    def merge_template(self, variables: Dict[str, any], output_path: str = None, create_date_folder: bool = True, upload_to_minio: bool = None) -> str:
        """
        合并模板和变量，生成最终文档，完全保持模板格式
        
        Args:
            variables: 变量字典
            output_path: 输出文件路径，如果None则自动生成
            create_date_folder: 是否在"核心网络部运维报告"下创建日期目录
            upload_to_minio: 是否上传到Minio，如果为None则使用配置
            
        Returns:
            str: 生成的文件路径
        """
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"模板文件不存在: {self.template_path}")
        
        # 生成输出文件名
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"核心网络部运维报告汇总_{timestamp}.docx"
            
            if create_date_folder:
                # 在"核心网络部运维报告"下创建日期目录
                date_str = datetime.now().strftime('%Y%m%d')
                base_dir = "核心网络部运维报告"
                output_dir = os.path.join(base_dir, date_str)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, filename)
            else:
                output_path = filename
        
        try:
            # 加载模板文档
            doc = DocxTemplate(self.template_path)

            self._replace_sub_document(doc, variables)

            # 保存文档
            doc.save(output_path)
            
            # 检查是否需要上传到Minio
            if upload_to_minio is None and self.config:
                output_config = self.config.get_output_config()
                upload_to_minio = output_config.get('upload_to_minio', False)
            
            if upload_to_minio and MinioUploader and self.config:
                try:
                    minio_config = self.config.get_minio_config()
                    uploader = MinioUploader(minio_config)
                    
                    # 使用配置中的上传路径
                    output_config = self.config.get_output_config()
                    upload_path = output_config.get('minio_upload_path', '核心网络部运维报告/')
                    
                    minio_url = uploader.upload_with_date_structure(output_path, upload_path)
                    print(f"✓ 报告已上传到Minio: {minio_url}")
                    
                except Exception as e:
                    print(f"⚠ Minio上传失败: {e}")
                    print(f"报告仍然已保存在本地: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"合并模板时发生错误: {e}")
            raise

    def _replace_sub_document(self, doc: DocxTemplate, variables: Dict[str, Any]):
        """递归处理子文档中的变量，保持原始格式"""
        # 将variables中的变量替换成以下格式{var_name: doc.new_subdoc(var_value)}
        processed_variables = {}
        
        for var_name, var_value in variables.items():
            # 检查变量类型
            if isinstance(var_value, dict) and 'type' in var_value:
                if var_value['type'] == 'sub_doc':
                    processed_variables[var_name] = doc.new_subdoc(var_value['value'])
                elif var_value['type'] == 'image':
                    processed_variables[var_name] = InlineImage(doc, var_value['value'], width=Cm(20))
                elif var_value['type'] == 'image_array' and isinstance(var_value['value'], list):
                    processed_variables[var_name] = self._process_image_array(doc, var_value['value'])
                else:
                    # 其他类型，作为文本处理
                    processed_variables[var_name] = str(var_value.get('value', var_value))
            else:
                # 简单字符串变量
                processed_variables[var_name] = str(var_value)
        
        doc.render(processed_variables)

    def _process_image_array(self, doc: DocxTemplate, image_paths: list):
        """
        将图片路径数组转换为InlineImage数组，支持Jinja数组语法
        
        Args:
            doc: DocxTemplate对象
            image_paths: 图片路径列表 ['img1.png', 'img2.png']
            
        Returns:
            InlineImage数组或单个图片对象
        """
        try:
            if not image_paths:
                return []
            
            # 转换为InlineImage数组
            inline_images = []
            for image_path in image_paths:
                if os.path.exists(image_path):
                    try:
                        # 创建InlineImage对象，设置合适的宽度
                        inline_image = InlineImage(doc, image_path, width=Cm(20))
                        inline_images.append(inline_image)
                    except Exception as e:
                        print(f"创建InlineImage失败 {image_path}: {e}")
                        continue
                else:
                    print(f"图片文件不存在: {image_path}")
                    continue
            
            # 如果只有一张图片，返回单个对象（兼容旧行为）
            if len(inline_images) == 1:
                return inline_images[0]
            
            # 多张图片，返回数组供Jinja循环使用
            return inline_images
            
        except Exception as e:
            print(f"处理图片数组失败: {e}")
            return []

    def validate_template(self) -> Dict[str, Any]:
        """
        验证模板文件，返回模板信息
        
        Returns:
            Dict[str, Any]: 模板信息
        """
        if not os.path.exists(self.template_path):
            return {'error': f"模板文件不存在: {self.template_path}"}
        
        try:
            doc = DocxTemplate(self.template_path)
            
            # 收集所有变量
            variables_found = doc.get_undeclared_template_variables()
            

            return {
                'template_path': self.template_path,
                'variables_count': len(variables_found),
                'variables': sorted(list(variables_found))
            }
            
        except Exception as e:
            return {'error': f"读取模板文件时发生错误: {e}"}
    
    def generate_variable_report(self, variables: Dict[str, str]) -> str:
        """生成变量替换报告"""
        template_info = self.validate_template()
        
        if 'error' in template_info:
            return f"模板验证失败: {template_info['error']}"
        
        template_vars = set(template_info.get('variables', []))
        provided_vars = set(variables.keys())
        
        report_lines = []
        report_lines.append("=== 变量替换报告 ===")
        report_lines.append(f"模板文件: {template_info['template_path']}")
        report_lines.append(f"模板中的变量数量: {len(template_vars)}")
        report_lines.append(f"提供的变量数量: {len(provided_vars)}")
        
        # 匹配的变量
        matched_vars = template_vars & provided_vars
        report_lines.append(f"\\n✓ 成功匹配的变量 ({len(matched_vars)}):")
        for var in sorted(matched_vars):
            report_lines.append(f"  - {var}")
        
        # 缺失的变量
        missing_vars = template_vars - provided_vars
        if missing_vars:
            report_lines.append(f"\\n✗ 缺失的变量 ({len(missing_vars)}):")
            for var in sorted(missing_vars):
                report_lines.append(f"  - {var}")
        
        return '\\n'.join(report_lines)