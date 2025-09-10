#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF解析器模块
通过API解析PDF文件并处理内容中的图片，或直接转换为图片
"""

import os
import re
import base64
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tempfile
from temp_utils import create_pdf_images_temp_dir


class PDFParser:
    """
    PDF解析器类
    支持两种模式：
    1. 'api' - 使用外部API解析PDF内容
    2. 'image' - 将PDF转换为图片
    """
    
    def __init__(self, api_url: str = "http://187.9.9.8:7434/v2/parse/file", parse_mode: str = "api", image_dpi: int = 200, poppler_path: str = None):
        """
        初始化PDF解析器
        
        Args:
            api_url: PDF解析API地址
            parse_mode: 解析模式，'api' 或 'image'
            image_dpi: 图片DPI设置（仅在image模式下使用）
            poppler_path: Poppler工具路径（仅在image模式下使用）
        """
        self.api_url = api_url
        self.parse_mode = parse_mode.lower()
        self.image_dpi = image_dpi
        self.poppler_path = poppler_path
        
        # 验证解析模式
        if self.parse_mode not in ['api', 'image']:
            print(f"警告：不支持的PDF解析模式 '{parse_mode}'，将使用默认的'api'模式")
            self.parse_mode = 'api'
        
        self.image_pattern = re.compile(r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]+)\)')
    
    def parse_pdf(self, pdf_path: str, extract_images: bool = True, 
                  image_output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        解析PDF文件，根据配置的模式选择API解析或图片转换
        
        Args:
            pdf_path: PDF文件路径
            extract_images: 是否提取图片（仅在API模式下使用）
            image_output_dir: 图片输出目录，如果为None则使用临时目录
            
        Returns:
            Dict: 解析结果，包含markdown内容和图片信息
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        print(f"正在使用{self.parse_mode}模式解析PDF文件: {pdf_path}")
        
        try:
            if self.parse_mode == 'api':
                return self._parse_pdf_with_api(pdf_path, extract_images, image_output_dir)
            elif self.parse_mode == 'image':
                return self._parse_pdf_as_images(pdf_path, image_output_dir)
            else:
                raise ValueError(f"不支持的解析模式: {self.parse_mode}")
                
        except Exception as e:
            print(f"✗ PDF解析失败: {e}")
            return {
                'success': False,
                'markdown': '',
                'images': [],
                'error': str(e),
                'pdf_file': pdf_path,
                'parse_mode': self.parse_mode
            }

    def _parse_pdf_with_api(self, pdf_path: str, extract_images: bool, image_output_dir: Optional[str]) -> Dict[str, Any]:
        """使用API模式解析PDF"""
        # 调用API解析PDF
        response_data = self._call_parse_api(pdf_path)
        
        # 提取markdown内容
        markdown_content = response_data.get('markdown', '')
        
        if not markdown_content:
            print("警告: 未从API响应中获取到markdown内容")
            return {
                'success': False,
                'markdown': '',
                'images': [],
                'error': '未获取到解析内容'
            }
        
        print(f"✓ PDF解析成功，内容长度: {len(markdown_content)} 字符")
        
        # 处理图片
        images_info = []
        processed_markdown = markdown_content
        
        if extract_images:
            images_info, processed_markdown = self._extract_and_save_images(
                markdown_content, image_output_dir
            )
        
        return {
            'success': True,
            'markdown': processed_markdown,
            'original_markdown': markdown_content,
            'images': images_info,
            'pdf_file': pdf_path,
            'parsed_at': datetime.now().isoformat(),
            'parse_mode': 'api'
        }

    def _parse_pdf_as_images(self, pdf_path: str, image_output_dir: Optional[str]) -> Dict[str, Any]:
        """使用图片模式解析PDF，只返回图片路径数组"""
        try:
            # 导入pdf2image库
            from pdf2image import convert_from_path
            from PIL import Image, ImageChops
        except ImportError:
            raise Exception("PDF转图片模式需要安装pdf2image和Pillow库: pip install pdf2image pillow")
        
        # 设置输出目录
        if image_output_dir is None:
            image_output_dir = create_pdf_images_temp_dir()
        else:
            os.makedirs(image_output_dir, exist_ok=True)
        
        print(f"PDF转图片输出目录: {image_output_dir}")
        
        # 转换PDF为图片
        try:
            images = convert_from_path(pdf_path, dpi=self.image_dpi, poppler_path=self.poppler_path)
        except Exception as e:
            raise Exception(f"PDF转图片失败: {e}")
        
        if not images:
            raise Exception("PDF转图片结果为空")
        
        # 保存图片并收集路径
        image_paths = []
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        for i, img in enumerate(images, start=1):
            # 裁剪空白边缘
            img_cropped = self._crop_blank(img)
            
            # 生成图片文件名
            image_filename = f"{base_name}_page{i}.png"
            image_path = os.path.join(image_output_dir, image_filename)
            
            # 保存图片
            img_cropped.save(image_path, "PNG")
            
            # 添加到路径数组
            image_paths.append(image_path)
        
        print(f"✓ PDF转图片成功，共{len(images)}页，生成{len(image_paths)}张图片")
        
        return {
            'success': True,
            'markdown': '',  # image模式不生成markdown
            'image_paths': image_paths,  # 返回图片路径数组
            'images': [{'path': path, 'page': i+1} for i, path in enumerate(image_paths)],
            'pdf_file': pdf_path,
            'parsed_at': datetime.now().isoformat(),
            'parse_mode': 'image',
            'page_count': len(images)
        }

    def _crop_blank(self, img, threshold=240):
        """自动裁剪空白边缘（参考excel2img.py）"""
        try:
            from PIL import Image, ImageChops
            
            img = img.convert("RGB")
            bg_color = (255, 255, 255)
            bg = Image.new(img.mode, img.size, bg_color)
            diff = ImageChops.difference(img, bg)
            bbox = diff.getbbox()
            if bbox:
                return img.crop(bbox)
            return img
        except Exception:
            # 如果裁剪失败，返回原图
            return img
    
    def _call_parse_api(self, pdf_path: str) -> Dict[str, Any]:
        """
        调用PDF解析API
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            Dict: API响应数据
        """
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {
                    'file': (os.path.basename(pdf_path), pdf_file, 'application/pdf')
                }
                
                # 发送请求
                response = requests.post(
                    self.api_url,
                    files=files,
                    timeout=300  # 5分钟超时
                )
                
                response.raise_for_status()
                
                # 解析响应
                response_data = response.json()
                
                if 'markdown' not in response_data:
                    raise ValueError("API响应中缺少markdown字段")
                
                return response_data
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败: {e}")
        except Exception as e:
            raise Exception(f"解析API响应失败: {e}")
    
    def _extract_and_save_images(self, markdown_content: str, 
                                output_dir: Optional[str] = None) -> Tuple[List[Dict], str]:
        """
        从markdown内容中提取并保存图片
        
        Args:
            markdown_content: markdown内容
            output_dir: 输出目录
            
        Returns:
            Tuple: (图片信息列表, 处理后的markdown内容)
        """
        if output_dir is None:
            output_dir = create_pdf_images_temp_dir()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        print(f"图片输出目录: {output_dir}")
        
        images_info = []
        processed_markdown = markdown_content
        
        # 查找所有图片
        matches = self.image_pattern.findall(markdown_content)
        
        if not matches:
            print("未发现base64编码的图片")
            return images_info, processed_markdown
        
        print(f"发现 {len(matches)} 个图片")
        
        for i, (alt_text, image_format, base64_data) in enumerate(matches):
            try:
                # 生成图片文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                image_filename = f"image_{timestamp}_{i+1}.{image_format}"
                image_path = os.path.join(output_dir, image_filename)
                
                # 解码并保存图片
                image_data = base64.b64decode(base64_data)
                
                with open(image_path, 'wb') as img_file:
                    img_file.write(image_data)
                
                # 记录图片信息
                image_info = {
                    'alt_text': alt_text,
                    'format': image_format,
                    'filename': image_filename,
                    'path': image_path,
                    'size': len(image_data)
                }
                images_info.append(image_info)
                
                # 替换markdown中的图片链接
                original_pattern = f'![{alt_text}](data:image/{image_format};base64,{base64_data})'
                new_pattern = f'![{alt_text}]({image_path})'
                processed_markdown = processed_markdown.replace(original_pattern, new_pattern)
                
                print(f"✓ 保存图片: {image_filename} ({len(image_data)} bytes)")
                
            except Exception as e:
                print(f"✗ 保存图片失败 {i+1}: {e}")
                continue
        
        return images_info, processed_markdown
    
    def batch_parse_pdfs(self, pdf_directory: str, output_directory: str = None) -> List[Dict[str, Any]]:
        """
        批量解析PDF文件
        
        Args:
            pdf_directory: PDF文件目录
            output_directory: 输出目录
            
        Returns:
            List: 解析结果列表
        """
        if not os.path.exists(pdf_directory):
            raise FileNotFoundError(f"目录不存在: {pdf_directory}")
        
        # 查找所有PDF文件
        pdf_files = []
        for file in os.listdir(pdf_directory):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(pdf_directory, file))
        
        if not pdf_files:
            print(f"在目录 {pdf_directory} 中未找到PDF文件")
            return []
        
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        # 创建输出目录
        if output_directory is None:
            output_directory = os.path.join(pdf_directory, 'parsed_output')
        
        os.makedirs(output_directory, exist_ok=True)
        
        # 批量解析
        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n处理第 {i}/{len(pdf_files)} 个文件: {os.path.basename(pdf_file)}")
            
            # 为每个PDF创建单独的图片目录
            pdf_name = os.path.splitext(os.path.basename(pdf_file))[0]
            image_dir = os.path.join(output_directory, pdf_name + '_images')
            
            result = self.parse_pdf(pdf_file, extract_images=True, image_output_dir=image_dir)
            result['index'] = i
            results.append(result)
        
        print(f"\n批量解析完成，共处理 {len(results)} 个文件")
        return results
    
    def save_markdown_to_file(self, markdown_content: str, output_path: str):
        """
        保存markdown内容到文件
        
        Args:
            markdown_content: markdown内容
            output_path: 输出文件路径
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"✓ markdown内容已保存到: {output_path}")
            
        except Exception as e:
            print(f"✗ 保存markdown文件失败: {e}")
    
    def get_text_summary(self, markdown_content: str, max_length: int = 500) -> str:
        """
        获取文本摘要
        
        Args:
            markdown_content: markdown内容
            max_length: 最大长度
            
        Returns:
            str: 文本摘要
        """
        # 移除图片
        text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_content)
        # 移除标题标记
        text = re.sub(r'#{1,6}\s+', '', text)
        # 移除粗体标记
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # 移除斜体标记
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        # 移除代码标记
        text = re.sub(r'`(.*?)`', r'\1', text)
        # 替换换行为空格
        text = re.sub(r'\n+', ' ', text)
        text = text.strip()
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length] + "..."


def main():
    """命令行测试功能"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PDF解析工具')
    parser.add_argument('pdf_path', help='PDF文件路径')
    parser.add_argument('--output-dir', help='图片输出目录')
    parser.add_argument('--save-markdown', help='保存markdown到指定文件')
    parser.add_argument('--api-url', default='http://187.9.9.8:7434/v2/parse/file', 
                       help='PDF解析API地址')
    
    args = parser.parse_args()
    
    # 创建解析器
    parser_instance = PDFParser(args.api_url)
    
    # 解析PDF
    result = parser_instance.parse_pdf(
        args.pdf_path, 
        extract_images=True,
        image_output_dir=args.output_dir
    )
    
    if result['success']:
        print(f"\n✓ 解析成功")
        print(f"  内容长度: {len(result['markdown'])} 字符")
        print(f"  图片数量: {len(result['images'])}")
        
        if args.save_markdown:
            parser_instance.save_markdown_to_file(result['markdown'], args.save_markdown)
        
        # 显示摘要
        summary = parser_instance.get_text_summary(result['markdown'])
        print(f"\n内容摘要:\n{summary}")
        
    else:
        print(f"\n✗ 解析失败: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    main()