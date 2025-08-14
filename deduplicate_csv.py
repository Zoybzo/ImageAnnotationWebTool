#!/usr/bin/env python3
"""
CSV文件去重工具
对图片标注CSV文件进行去重，保留每个图片的最后一次标签
"""

import pandas as pd
import os
import sys
from datetime import datetime


def deduplicate_annotations(input_file, output_file=None):
    """
    对CSV文件进行去重处理

    Args:
        input_file (str): 输入的CSV文件路径
        output_file (str): 输出的CSV文件路径，如果为None则自动生成
    """

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        return False

    try:
        # 读取CSV文件
        print(f"正在读取文件: {input_file}")
        df = pd.read_csv(input_file)

        # 检查必要的列是否存在
        required_columns = ["image_path", "image_name", "quality", "timestamp"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"错误: CSV文件缺少必要的列: {missing_columns}")
            return False

        print(f"原始数据行数: {len(df)}")
        print(f"唯一图片数量: {df['image_path'].nunique()}")

        # 按图片路径分组，保留最后一次标注（最新的timestamp）
        print("正在进行去重处理...")

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

        print(f"去重后数据行数: {len(df_deduplicated)}")
        print(f"去重后唯一图片数量: {df_deduplicated['image_path'].nunique()}")

        # 生成输出文件名
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{base_name}_deduplicated_{timestamp}.csv"

        # 保存去重后的数据
        df_deduplicated.to_csv(output_file, index=False)
        print(f"去重后的数据已保存到: {output_file}")

        # 显示去重统计信息
        print("\n去重统计:")
        print(f"  原始记录数: {len(df)}")
        print(f"  去重后记录数: {len(df_deduplicated)}")
        print(f"  删除的重复记录数: {len(df) - len(df_deduplicated)}")

        # 显示质量分布
        print("\n质量分布:")
        quality_counts = df_deduplicated["quality"].value_counts()
        for quality, count in quality_counts.items():
            print(f"  {quality}: {count}")

        return True

    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("CSV文件去重工具")
    print("=" * 50)

    # 检查命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        # 交互式输入
        input_file = input("请输入CSV文件路径 (默认: annotations.csv): ").strip()
        if not input_file:
            input_file = "annotations.csv"

        output_file = input("请输入输出文件路径 (留空自动生成): ").strip()
        if not output_file:
            output_file = None

    # 执行去重
    success = deduplicate_annotations(input_file, output_file)

    if success:
        print("\n去重处理完成！")
    else:
        print("\n去重处理失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
