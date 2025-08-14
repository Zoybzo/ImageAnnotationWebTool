from flask import Flask, request, jsonify, send_file, render_template_string, Response
import os
import csv
import json
from datetime import datetime
from pathlib import Path
import mimetypes

# 尝试导入pandas，如果不可用则使用标准库
try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

app = Flask(__name__)

# 支持的图片格式
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

# CSV文件路径
CSV_FILE = "annotations.csv"


def is_image_file(file_path):
    """检查文件是否为图片"""
    return Path(file_path).suffix.lower() in SUPPORTED_FORMATS


def get_image_files(folder_path):
    """获取文件夹中的所有图片文件"""
    if not os.path.exists(folder_path):
        return []

    image_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if is_image_file(file_path):
                image_files.append(file_path)

    return sorted(image_files)


def save_to_csv(annotations):
    """保存标注到CSV文件"""
    try:
        # 检查CSV文件是否存在，如果不存在则创建表头
        file_exists = os.path.exists(CSV_FILE)

        with open(CSV_FILE, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["image_path", "image_name", "quality", "timestamp"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            # 写入新的标注数据
            for image_path, annotation in annotations.items():
                image_name = os.path.basename(image_path)
                writer.writerow(
                    {
                        "image_path": image_path,
                        "image_name": image_name,
                        "quality": annotation["quality"],
                        "timestamp": annotation["timestamp"],
                    }
                )

        return True
    except Exception as e:
        print(f"保存CSV时出错: {e}")
        return False


def deduplicate_csv_file(input_file, output_file=None):
    """对CSV文件进行去重处理"""
    try:
        if not os.path.exists(input_file):
            return False, "输入文件不存在"

        if PANDAS_AVAILABLE:
            # 使用pandas进行去重
            return deduplicate_with_pandas(input_file, output_file)
        else:
            # 使用标准库进行去重
            return deduplicate_with_stdlib(input_file, output_file)

    except Exception as e:
        return False, f"去重处理失败: {str(e)}"


def deduplicate_with_pandas(input_file, output_file=None):
    """使用pandas进行去重"""
    try:
        # 读取CSV文件
        df = pd.read_csv(input_file)

        # 检查必要的列是否存在
        required_columns = ["image_path", "image_name", "quality", "timestamp"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"CSV文件缺少必要的列: {missing_columns}"

        original_count = len(df)

        # 将timestamp转换为datetime以便排序
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # 按image_path分组，保留最新的记录
        df_deduplicated = (
            df.sort_values("timestamp")
            .groupby("image_path")
            .tail(1)
            .reset_index(drop=True)
        )

        # 按原始顺序排序（按image_path）
        df_deduplicated = df_deduplicated.sort_values("image_path").reset_index(
            drop=True
        )

        deduplicated_count = len(df_deduplicated)

        # 生成输出文件名
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{base_name}_deduplicated_{timestamp}.csv"

        # 保存去重后的数据
        df_deduplicated.to_csv(output_file, index=False)

        # 计算质量分布
        quality_counts = df_deduplicated["quality"].value_counts()
        quality_distribution = ", ".join(
            [f"{k}: {v}" for k, v in quality_counts.items()]
        )

        return True, {
            "output_file": output_file,
            "original_count": original_count,
            "deduplicated_count": deduplicated_count,
            "removed_count": original_count - deduplicated_count,
            "quality_distribution": quality_distribution,
        }

    except Exception as e:
        return False, f"pandas去重失败: {str(e)}"


def deduplicate_with_stdlib(input_file, output_file=None):
    """使用标准库进行去重"""
    try:
        # 读取CSV文件
        records = []
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)

        original_count = len(records)

        # 按图片路径分组，保留最新的记录
        image_groups = {}
        for record in records:
            image_path = record["image_path"]
            timestamp = datetime.fromisoformat(
                record["timestamp"].replace("Z", "+00:00")
            )

            if (
                image_path not in image_groups
                or timestamp > image_groups[image_path]["timestamp"]
            ):
                image_groups[image_path] = {"record": record, "timestamp": timestamp}

        # 提取去重后的记录
        deduplicated_records = [group["record"] for group in image_groups.values()]
        deduplicated_records.sort(key=lambda x: x["image_path"])

        deduplicated_count = len(deduplicated_records)

        # 生成输出文件名
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{base_name}_deduplicated_{timestamp}.csv"

        # 保存去重后的数据
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            if deduplicated_records:
                fieldnames = deduplicated_records[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(deduplicated_records)

        # 计算质量分布
        quality_counts = {}
        for record in deduplicated_records:
            quality = record["quality"]
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

        quality_distribution = ", ".join(
            [f"{k}: {v}" for k, v in quality_counts.items()]
        )

        return True, {
            "output_file": output_file,
            "original_count": original_count,
            "deduplicated_count": deduplicated_count,
            "removed_count": original_count - deduplicated_count,
            "quality_distribution": quality_distribution,
        }

    except Exception as e:
        return False, f"标准库去重失败: {str(e)}"


@app.route("/")
def index():
    """主页"""
    return send_file("index.html")


@app.route("/script.js")
def script():
    """JavaScript文件"""
    return send_file("script.js")


@app.route("/api/images", methods=["POST"])
def get_images():
    """获取指定文件夹中的图片列表"""
    try:
        data = request.get_json()
        folder_path = data.get("folder_path", "").strip()

        if not folder_path:
            return jsonify({"success": False, "error": "文件夹路径不能为空"})

        if not os.path.exists(folder_path):
            return jsonify({"success": False, "error": "文件夹不存在"})

        if not os.path.isdir(folder_path):
            return jsonify({"success": False, "error": "指定路径不是文件夹"})

        image_files = get_image_files(folder_path)

        return jsonify(
            {"success": True, "images": image_files, "count": len(image_files)}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/image/")
def serve_image():
    """提供图片文件"""
    try:
        # 从查询参数获取图片路径
        image_path = request.args.get("path")
        if not image_path:
            return jsonify({"error": "缺少图片路径参数"}), 400

        # 解码URL路径
        from urllib.parse import unquote

        original_path = image_path
        image_path = unquote(image_path)

        # 安全检查：确保路径是绝对路径且存在
        print(f"检查路径: {image_path}")
        print(f"是否为绝对路径: {os.path.isabs(image_path)}")
        print(f"路径是否存在: {os.path.exists(image_path)}")

        if not os.path.isabs(image_path):
            return jsonify({"error": f"无效的图片路径: {image_path}"}), 400

        if not os.path.exists(image_path):
            return jsonify({"error": f"图片文件不存在: {image_path}"}), 404

        if not is_image_file(image_path):
            return jsonify({"error": "不是有效的图片文件"}), 400

            # 获取文件的MIME类型
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        # 使用更直接的方法读取和返回文件
        try:
            with open(image_path, "rb") as f:
                file_data = f.read()

            response = Response(file_data, mimetype=mime_type)
            response.headers["Content-Disposition"] = (
                f'inline; filename="{os.path.basename(image_path)}"'
            )
            response.headers["Cache-Control"] = "no-cache"
            return response
        except Exception as e:
            print(f"读取文件失败: {e}")
            return jsonify({"error": f"读取文件失败: {e}"}), 500

    except Exception as e:
        print(f"图片加载错误: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/save", methods=["POST"])
def save_annotations():
    """保存标注到CSV文件"""
    try:
        data = request.get_json()
        annotations = data.get("annotations", {})

        if not annotations:
            return jsonify({"success": False, "error": "没有标注数据"})

        success = save_to_csv(annotations)

        if success:
            return jsonify({"success": True, "message": "标注已保存"})
        else:
            return jsonify({"success": False, "error": "保存失败"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/status")
def get_status():
    """获取服务器状态"""
    return jsonify({"status": "running", "timestamp": datetime.now().isoformat()})


@app.route("/api/deduplicate", methods=["POST"])
def api_deduplicate():
    """API端点：对CSV文件进行去重"""
    try:
        # 检查CSV文件是否存在
        if not os.path.exists(CSV_FILE):
            return jsonify({"success": False, "error": "没有找到标注文件"})

        # 执行去重
        success, result = deduplicate_csv_file(CSV_FILE)

        if success:
            return jsonify({"success": True, **result})
        else:
            return jsonify({"success": False, "error": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    print("图片标注工具服务器启动中...")
    print("请在浏览器中访问: http://localhost:5000")
    print("支持的图片格式:", ", ".join(SUPPORTED_FORMATS))
    print("标注结果将保存到:", CSV_FILE)
    print("\n按 Ctrl+C 停止服务器")

    app.run(debug=True, host="0.0.0.0", port=5000)
