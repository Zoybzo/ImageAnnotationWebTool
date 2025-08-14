#!/usr/bin/env python3
"""
测试文件访问权限
"""

import os
import mimetypes
from pathlib import Path


def test_file_access():
    """测试文件访问"""
    test_path = "/Users/lingrun.1/Datasets/InnoAdData/20250813_merge_0807_0811_400sampled_images_500subset/000001_other_3_10143592196502.jpg"

    print(f"测试文件路径: {test_path}")
    print(f"文件是否存在: {os.path.exists(test_path)}")
    print(f"是否为绝对路径: {os.path.isabs(test_path)}")
    print(f"是否为文件: {os.path.isfile(test_path)}")
    print(f"是否可读: {os.access(test_path, os.R_OK)}")

    if os.path.exists(test_path):
        print(f"文件大小: {os.path.getsize(test_path)} bytes")
        print(f"文件权限: {oct(os.stat(test_path).st_mode)[-3:]}")

        # 测试MIME类型
        mime_type, _ = mimetypes.guess_type(test_path)
        print(f"MIME类型: {mime_type}")

        # 测试文件扩展名
        suffix = Path(test_path).suffix.lower()
        print(f"文件扩展名: {suffix}")

        # 测试是否为图片文件
        supported_formats = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
        is_image = suffix in supported_formats
        print(f"是否为支持的图片格式: {is_image}")

        # 尝试读取文件头
        try:
            with open(test_path, "rb") as f:
                header = f.read(10)
                print(f"文件头: {header}")
        except Exception as e:
            print(f"读取文件失败: {e}")


if __name__ == "__main__":
    test_file_access()
