# 核心网络部运维报告合并工具

## 简介

这是一个专注于模板变量替换和格式保留的文档处理工具，用于自动化合并核心网络部的运维报告。

## 功能特性

- ✅ 支持命令行模式（传统用法）
- ✅ 支持HTTP API模式（新增功能）
- ✅ 模板变量替换
- ✅ 格式保留（包括字体、颜色、表格等）
- ✅ 支持Minio和本地文件系统
- ✅ 自动处理Excel、Word和PDF文件
- ✅ 自动生成带时间戳的输出文件
- ✅ 支持上传到Minio存储桶

## 安装依赖

### 基础依赖

```bash
# Linux系统
apt-get update && apt-get install -y poppler-utils

# Windows系统
# 需要安装poppler并添加到PATH

# Python依赖
pip install python-docx pdf2image pandas openpyxl docxtpl pillow minio
```

### API模式依赖（可选）

```bash
# 安装FastAPI和Uvicorn
pip install fastapi uvicorn

# 或使用安装脚本
python install_api_deps.py
```

## 使用方法

### 命令行模式

```bash
# 基本用法
python main.py --minio --verbose

# 自定义输出文件名
python main.py --output "自定义文件名.docx" --verbose

# 查看所有参数
python main.py --help
```

### API模式

```bash
# 启动API服务器
python main.py --api

# 启动API服务器（自定义地址和端口）
python main.py --api --host 0.0.0.0 --port 8080

# 查看API文档
# 浏览器访问: http://127.0.0.1:8000/docs
```

## API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API健康检查 |
| `/health` | GET | 健康状态检查 |
| `/config` | GET | 获取当前配置 |
| `/merge` | GET | 通过查询参数合并报告 |
| `/merge` | POST | 通过JSON请求体合并报告 |

## API使用示例

### Python示例

```python
import requests

# 合并报告
response = requests.post("http://127.0.0.1:8000/merge", 
                        json={
                            "use_minio": True,
                            "verbose": True,
                            "template_path": "template.docx"
                        })
result = response.json()

if result['success']:
    print(f"✓ 合并成功: {result['output_file']}")
else:
    print(f"✗ 合并失败: {result['error']}")
```

### curl示例

```bash
# 健康检查
curl -X GET "http://127.0.0.1:8000/health"

# 合并报告
curl -X POST "http://127.0.0.1:8000/merge" \
     -H "Content-Type: application/json" \
     -d '{"use_minio": true, "verbose": true}'
```

## 配置文件

配置文件 `config.json` 包含Minio连接信息和其他系统配置。

## 故障排除

1. 如果看到"FastAPI 未安装"警告，运行 `python install_api_deps.py`
2. 如果端口被占用，使用 `--port` 参数指定其他端口
3. 确保poppler已正确安装并添加到PATH

## 许可证

MIT License
