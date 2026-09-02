"""
后端启动脚本

用法（在 backend 目录下执行）：
    python run.py                 # 默认 0.0.0.0:8000
    python run.py --port 9000     # 指定端口
    python run.py --reload        # 开发模式（代码改动自动重启）
"""
import argparse
import os
import sys

# Windows 下强制 UTF-8，避免中文日志/文件名乱码
os.environ.setdefault("PYTHONUTF8", "1")

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="智能车间缺陷检测系统 - 后端启动脚本")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    parser.add_argument("--reload", action="store_true", help="开发模式：代码改动自动重启")
    args = parser.parse_args()

    print("=" * 60)
    print("智能车间产品外观缺陷检测与报告系统 - 后端服务")
    print(f"  地址: http://localhost:{args.port}")
    print(f"  接口文档: http://localhost:{args.port}/docs")
    print("=" * 60)

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
