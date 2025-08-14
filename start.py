#!/usr/bin/env python3
"""
图片标注工具启动脚本
"""

import subprocess
import sys
import os


def install_requirements():
    """安装依赖包"""
    print("正在安装依赖包...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("依赖包安装完成！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖包失败: {e}")
        return False


def start_server():
    """启动Flask服务器"""
    print("正在启动图片标注工具服务器...")
    try:
        subprocess.run([sys.executable, "server.py"])
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动服务器失败: {e}")


def main():
    print("=" * 50)
    print("图片标注工具")
    print("=" * 50)

    # 检查requirements.txt是否存在
    if not os.path.exists("requirements.txt"):
        print("错误: 找不到 requirements.txt 文件")
        return

    # 安装依赖
    if not install_requirements():
        print("请手动安装依赖: pip install -r requirements.txt")
        return

    print("\n" + "=" * 50)
    print("启动说明:")
    print("1. 服务器将在 http://localhost:5000 启动")
    print("2. 支持的图片格式: JPG, PNG, GIF, BMP, TIFF, WebP")
    print("3. 标注结果将保存到 annotations.csv 文件")
    print("4. 按 Ctrl+C 停止服务器")
    print("=" * 50)

    # 启动服务器
    start_server()


if __name__ == "__main__":
    main()
