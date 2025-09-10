#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心网络部运维报告合并工具 - 优化版主程序
专注于模板变量替换和格式保留的核心功能
"""

import os
import sys
import argparse
from typing import Optional, Dict, Any
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Body
from pydantic import BaseModel

# 导入核心模块
from data_processor import CoreDataProcessor
from template_merger import CoreTemplateMerger
from config import Config


class CoreReportMerger:
    """核心报告合并器类"""

    def __init__(self, template_path: str = "template.docx", use_minio: bool = False, config: Config = None):
        """
        初始化报告合并器

        Args:
            template_path: 模板文件路径
            use_minio: 是否使用Minio作为文件源
            config: 配置对象
        """
        self.template_path = template_path
        self.use_minio = use_minio
        self.config = config or Config()

        # 初始化数据处理器
        if use_minio:
            if not self.config.validate_minio_config():
                raise ValueError("使用Minio模式需要完整的Minio配置")
            self.data_processor = CoreDataProcessor(use_minio=True, minio_config=self.config.get_minio_config(),
                                                    config=self.config)
        else:
            self.data_processor = CoreDataProcessor(use_minio=False, config=self.config)

        self.template_merger = CoreTemplateMerger(template_path, config=self.config)

    def merge_reports(self, output_path: Optional[str] = None, verbose: bool = False, create_date_folder: bool = True,
                      upload_to_minio: bool = None, target_date: str = None) -> str:
        """
        执行核心报告合并流程

        Args:
            output_path: 输出文件路径，如果为None则自动生成
            verbose: 是否显示详细信息
            create_date_folder: 是否在"核心网络部运维报告"下创建日期目录
            upload_to_minio: 是否上传到Minio
            target_date: 目标日期，格式为YYYYMM。如果为None，则使用上个月

        Returns:
            str: 生成的文件路径
        """
        if verbose:
            print("=" * 50)
            print("核心网络部运维报告合并工具")
            print("=" * 50)

        try:
            # 验证模板文件
            if verbose:
                print("\\n验证模板文件...")
            template_info = self.template_merger.validate_template()

            if 'error' in template_info:
                raise Exception(f"模板文件验证失败: {template_info['error']}")

            if verbose:
                print(f"✓ 模板验证成功 - {template_info['variables_count']}个变量")

            # 处理所有文件并生成变量
            if verbose:
                print("\n处理文件...")
            variables = self.data_processor.process_all_files(set(template_info.get('variables', [])), target_date)

            # 生成变量报告
            if verbose:
                print("\n变量替换报告:")
                variable_report = self.template_merger.generate_variable_report(variables)
                print(variable_report)

            # 合并模板
            if verbose:
                print("\n合并模板...")
            output_file = self.template_merger.merge_template(variables, output_path, create_date_folder,
                                                              upload_to_minio)

            return output_file

        except Exception as e:
            print(f"报告合并失败: {e}")
            raise

    def _print_summary(self, output_file: str, file_dict: dict, variables: dict):
        """打印摘要信息"""
        print("\n" + "=" * 50)
        print("合并摘要")
        print("=" * 50)

        print(f"输出文件: {output_file}")
        print(f"文件大小: {os.path.getsize(output_file) / 1024:.1f} KB")

        total_files = sum(len(files) for files in file_dict.values())
        print(f"处理文件数: {total_files}")

        filled_vars = 0
        for v in variables.values():
            if isinstance(v, dict):
                # 对于字典类型的变量（如PDF、DOCX等）
                if v.get('type') and v.get('value'):
                    filled_vars += 1
            elif isinstance(v, str):
                # 对于字符串类型的变量
                if not v.startswith('['):
                    filled_vars += 1
            else:
                # 其他类型都认为是有效的
                filled_vars += 1
        total_vars = len(variables)
        print(f"变量替换: {filled_vars}/{total_vars} ({filled_vars / total_vars * 100:.1f}%)")


# FastAPI 应用实例
app = FastAPI(
    title="核心网络部运维报告合并工具 API",
    description="专注于模板变量替换和格式保留的核心功能",
    version="1.0.0"
)

# 全局配置
global_config = None


class MergeRequest(BaseModel):
    """报告合并请求模型"""
    template_path: Optional[str] = "template.docx"
    output_path: Optional[str] = None
    use_minio: bool = False
    verbose: bool = False
    create_date_folder: bool = True
    upload_to_minio: Optional[bool] = None
    target_date: Optional[str] = None
    config_path: str = "config.json"


class MergeResponse(BaseModel):
    """报告合并响应模型"""
    success: bool
    message: str
    output_file: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global global_config
    try:
        global_config = Config()
        print("API服务启动成功")
    except Exception as e:
        print(f"API服务启动失败: {e}")


@app.get("/", summary="API健康检查")
async def root():
    """根路径健康检查"""
    return {
        "message": "核心网络部运维报告合并工具 API",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", summary="健康状态检查")
async def health_check():
    """健康状态检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "config_loaded": global_config is not None
    }


@app.post("/merge", response_model=MergeResponse, summary="合并报告")
async def merge_reports_api(request: MergeRequest):
    """
    执行报告合并

    Args:
        request: 合并请求参数

    Returns:
        MergeResponse: 合并结果
    """
    start_time = datetime.now()

    try:
        # 加载配置
        config = Config(request.config_path)

        if request.verbose:
            print(f"\n使用API模式执行报告合并")
            if request.use_minio:
                print(f"使用Minio模式")
                minio_config = config.get_minio_config()
                print(f"Minio端点: {minio_config.get('endpoint')}")
                print(f"存储桶: {minio_config.get('bucket_name')}")

        # 执行报告合并
        merger = CoreReportMerger(
            template_path=request.template_path,
            use_minio=request.use_minio,
            config=config
        )

        output_file = merger.merge_reports(
            output_path=request.output_path,
            verbose=request.verbose,
            create_date_folder=request.create_date_folder,
            upload_to_minio=request.upload_to_minio,
            target_date=request.target_date
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        return MergeResponse(
            success=True,
            message="报告合并完成",
            output_file=output_file,
            processing_time=processing_time
        )

    except Exception as e:
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        error_msg = str(e)
        print(f"API错误: {error_msg}")

        return MergeResponse(
            success=False,
            message="报告合并失败",
            error=error_msg,
            processing_time=processing_time
        )


def cli_main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description='核心网络部运维报告合并工具')
    parser.add_argument(
        '--api', '-a',
        action='store_true',
        help='启动HTTP API服务器模式'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='API服务器主机地址 (默认: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='API服务器端口 (默认: 8000)'
    )
    parser.add_argument(
        '--template', '-t',
        default='template.docx',
        help='模板文件路径 (默认: template.docx)'
    )
    parser.add_argument(
        '--output', '-o',
        help='输出文件路径 (默认: 自动生成带时间戳的文件名)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细处理信息'
    )
    parser.add_argument(
        '--minio', '-m',
        action='store_true',
        help='使用Minio作为文件源'
    )
    parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='配置文件路径 (默认: config.json)'
    )
    parser.add_argument(
        '--no-date-folder',
        action='store_true',
        help='不在"核心网络部运维报告"下创建日期目录'
    )
    parser.add_argument(
        '--upload-minio',
        action='store_true',
        help='强制上传报告到Minio存储桶'
    )
    parser.add_argument(
        '--target-date',
        help='目标日期，格式为YYYYMM。如果未指定，则使用上个月'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='禁止上传报告到Minio存储桶'
    )

    args = parser.parse_args()

    # 如果指定了API模式，启动HTTP服务器
    if args.api:
        print(f"启动HTTP API服务器...")
        print(f"地址: http://{args.host}:{args.port}")
        print(f"API文档: http://{args.host}:{args.port}/docs")
        print(f"按Ctrl+C停止服务器")

        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=False,
            log_level="info"
        )
        return

    # 确定上传到Minio的设置
    upload_to_minio = None
    if args.upload_minio:
        upload_to_minio = True
    elif args.no_upload:
        upload_to_minio = False

    try:
        # 加载配置
        config = Config(args.config)

        # 创建报告合并器
        merger = CoreReportMerger(
            template_path=args.template,
            use_minio=args.minio,
            config=config
        )

        # 执行报告合并
        output_file = merger.merge_reports(
            output_path=args.output,
            verbose=args.verbose,
            create_date_folder=not args.no_date_folder,
            upload_to_minio=upload_to_minio,
            target_date=args.target_date
        )

        print(f"\n✓ 报告合并完成: {output_file}")

    except Exception as e:
        print(f"\n✗ 报告合并失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """主函数 - 兼容原有调用方式"""
    cli_main()


if __name__ == "__main__":
    main()