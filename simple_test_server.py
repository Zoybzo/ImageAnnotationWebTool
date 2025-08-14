#!/usr/bin/env python3
"""
简单的测试服务器
"""

from flask import Flask, Response
import os
import mimetypes

app = Flask(__name__)


@app.route("/test/<path:image_path>")
def test_image(image_path):
    """测试图片访问"""
    from urllib.parse import unquote

    original_path = image_path
    image_path = unquote(image_path)

    print(f"原始路径: {original_path}")
    print(f"解码后路径: {image_path}")
    print(f"路径是否存在: {os.path.exists(image_path)}")

    if not os.path.exists(image_path):
        return f"文件不存在: {image_path}", 404

    try:
        with open(image_path, "rb") as f:
            file_data = f.read()

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        response = Response(file_data, mimetype=mime_type)
        response.headers["Content-Disposition"] = (
            f'inline; filename="{os.path.basename(image_path)}"'
        )
        return response

    except Exception as e:
        return f"读取文件失败: {e}", 500


if __name__ == "__main__":
    print("测试服务器启动在 http://localhost:5001")
    app.run(debug=True, port=5001)
