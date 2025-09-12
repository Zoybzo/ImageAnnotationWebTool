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

# 项目根路径（用于解析相对路径）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# CSV文件路径
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = f"data/annotations_{timestamp}.csv"


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

        # 支持相对路径：相对项目根目录解析
        if not os.path.isabs(folder_path):
            folder_path = os.path.normpath(os.path.join(PROJECT_ROOT, folder_path))

        if not os.path.isdir(folder_path):
            return jsonify({"success": False, "error": "指定路径不是文件夹"})

        image_files = get_image_files(folder_path)

        return jsonify(
            {"success": True, "images": image_files, "count": len(image_files)}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/images_from_csv", methods=["POST"])
def get_images_from_csv():
    """从CSV文件读取图片路径列表。CSV需包含列名 'path' 或 'image_path'，可选 'quality' 列"""
    try:
        data = request.get_json()
        csv_path = data.get("csv_path", "").strip()
        filters = data.get("filters", {}) or {}
        order = (data.get("order") or "original").strip().lower()

        if not csv_path:
            return jsonify({"success": False, "error": "CSV文件路径不能为空"})

        if not os.path.exists(csv_path):
            return jsonify({"success": False, "error": "CSV文件不存在"})

        if not os.path.isfile(csv_path) or not csv_path.lower().endswith(".csv"):
            return jsonify({"success": False, "error": "指定路径不是CSV文件"})

        image_paths = []
        # 暂存从CSV读到的quality（键为原始/清洗后的字符串）；稍后会转成绝对路径键
        raw_quality_map = {}

        # 优先使用pandas读取，兼容列名 'path' 或 'image_path'
        if PANDAS_AVAILABLE:
            try:
                df = pd.read_csv(csv_path)
                candidate_cols = [col for col in ["path", "image_path"] if col in df.columns]
                if not candidate_cols:
                    return jsonify({
                        "success": False,
                        "error": "CSV缺少'path'或'image_path'列"
                    })
                path_col = candidate_cols[0]

                # 计算可用的过滤条件（仅对存在于CSV中的列应用）
                applicable_filters = {}
                for k, v in (filters.items() if isinstance(filters, dict) else []):
                    if k in df.columns:
                        # 将所有值转为字符串进行一致性比较
                        values = [str(x).strip() for x in (v if isinstance(v, list) else [v]) if str(x).strip() != ""]
                        if values:
                            applicable_filters[k] = values

                # 应用过滤
                if applicable_filters:
                    mask = pd.Series([True] * len(df))
                    for k, values in applicable_filters.items():
                        mask = mask & df[k].astype(str).isin(values)
                    df = df[mask]

                image_paths = df[path_col].dropna().astype(str).tolist()
                # 如果包含quality列，则记录下来
                if "quality" in df.columns:
                    for _, row in df.iterrows():
                        raw_path = row.get(path_col)
                        if pd.isna(raw_path):
                            continue
                        p = str(raw_path).strip().strip('"').strip("'")
                        q = row.get("quality")
                        if not pd.isna(q):
                            raw_quality_map[p] = str(q)
            except Exception as e:
                return jsonify({"success": False, "error": f"读取CSV失败: {e}"})
        else:
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    header = reader.fieldnames or []
                    path_col = "path" if "path" in header else ("image_path" if "image_path" in header else None)
                    if path_col is None:
                        return jsonify({
                            "success": False,
                            "error": "CSV缺少'path'或'image_path'列"
                        })

                    # 计算可用过滤条件
                    applicable_filters = {}
                    if isinstance(filters, dict):
                        for k, v in filters.items():
                            if k in header:
                                values = [str(x).strip() for x in (v if isinstance(v, list) else [v]) if str(x).strip() != ""]
                                if values:
                                    applicable_filters[k] = set(values)

                    for row in reader:
                        # 如有过滤条件，则校验
                        passes = True
                        if applicable_filters:
                            for k, values in applicable_filters.items():
                                rv = (row.get(k) or "").strip()
                                if rv not in values:
                                    passes = False
                                    break
                        if not passes:
                            continue

                        value = (row.get(path_col) or "").strip()
                        if value:
                            image_paths.append(value)
                            if "quality" in header:
                                q = (row.get("quality") or "").strip()
                                if q:
                                    # 存原始和去引号两种形式，方便匹配
                                    raw_quality_map[value] = q
                                    cleaned = value.strip().strip('"').strip("'")
                                    raw_quality_map[cleaned] = q
            except Exception as e:
                return jsonify({"success": False, "error": f"读取CSV失败: {e}"})

        # 过滤有效的图片路径（支持相对路径，按项目根目录解析）
        valid_images = []
        invalid_entries = 0
        for p in image_paths:
            # 支持可能包含多余空白或引号的情况
            candidate = p.strip().strip('"').strip("'")
            # 若为相对路径，则相对项目根目录解析
            if not os.path.isabs(candidate):
                candidate = os.path.normpath(os.path.join(PROJECT_ROOT, candidate))
            if os.path.exists(candidate) and is_image_file(candidate):
                valid_images.append(candidate)
            else:
                invalid_entries += 1

        # 将raw_quality_map的键统一解析为绝对路径，便于与valid_images匹配
        qualities = {}
        for raw_key, q in raw_quality_map.items():
            k = (raw_key or "").strip().strip('"').strip("'")
            if not os.path.isabs(k):
                k = os.path.normpath(os.path.join(PROJECT_ROOT, k))
            qualities[k] = q

        # 仅保留有效图片的quality
        qualities = {vp: qualities[vp] for vp in valid_images if vp in qualities}

        # 排序逻辑：original 保留 CSV 原顺序；filename 按文件名字典序
        images_out = list(valid_images)
        if order == "filename":
            images_out.sort(key=lambda p: os.path.basename(p))
        # 默认 original：不排序

        return jsonify({
            "success": True,
            "images": images_out,
            "count": len(images_out),
            "invalid": invalid_entries,
            "qualities": qualities
        })

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
