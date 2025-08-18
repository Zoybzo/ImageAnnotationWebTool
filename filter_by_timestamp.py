#!/usr/bin/env python3
"""
CSV时间戳过滤程序
根据指定的时间点过滤CSV文件中的行，将时间戳在该时间点之后的行保存到新文件
"""

import pandas as pd
import argparse
from datetime import datetime
import os
import sys


def parse_timestamp(timestamp_str):
    """
    解析时间戳字符串，支持多种格式
    """
    # 尝试多种时间格式
    formats = [
        "%Y-%m-%d %H:%M:%S.%f%z",  # 2025-08-18 02:03:32.457000+00:00
        "%Y-%m-%d %H:%M:%S%z",  # 2025-08-18 02:03:32+00:00
        "%Y-%m-%d %H:%M:%S",  # 2025-08-18 02:03:32
        "%Y-%m-%d",  # 2025-08-18
        "%Y/%m/%d %H:%M:%S",  # 2025/08/18 02:03:32
        "%Y/%m/%d",  # 2025/08/18
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"无法解析时间戳格式: {timestamp_str}")


def filter_csv_by_timestamp(
    input_file, output_file, cutoff_timestamp, timestamp_column="timestamp"
):
    """
    根据时间戳过滤CSV文件

    Args:
        input_file (str): 输入CSV文件路径
        output_file (str): 输出CSV文件路径
        cutoff_timestamp (str): 截止时间点（字符串格式）
        timestamp_column (str): 时间戳列名，默认为'timestamp'
    """
    try:
        # 读取CSV文件
        print(f"正在读取文件: {input_file}")
        df = pd.read_csv(input_file)

        # 检查时间戳列是否存在
        if timestamp_column not in df.columns:
            print(f"错误: 列 '{timestamp_column}' 不存在于CSV文件中")
            print(f"可用的列: {list(df.columns)}")
            return False

        # 解析截止时间点
        print(f"解析截止时间点: {cutoff_timestamp}")
        cutoff_dt = parse_timestamp(cutoff_timestamp)
        print(f"截止时间点: {cutoff_dt}")

        # 将时间戳列转换为datetime类型
        print("正在转换时间戳列...")
        df[timestamp_column] = pd.to_datetime(df[timestamp_column])

        # 过滤数据
        print("正在过滤数据...")
        filtered_df = df[df[timestamp_column] > cutoff_dt]

        # 保存结果
        print(f"正在保存结果到: {output_file}")
        filtered_df.to_csv(output_file, index=False)

        print(f"过滤完成!")
        print(f"原始数据行数: {len(df)}")
        print(f"过滤后行数: {len(filtered_df)}")
        print(f"保留的行数: {len(filtered_df)}")

        return True

    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="根据时间戳过滤CSV文件")
    parser.add_argument("input_file", help="输入CSV文件路径")
    parser.add_argument("output_file", help="输出CSV文件路径")
    parser.add_argument(
        "cutoff_timestamp", help="截止时间点 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)"
    )
    parser.add_argument(
        "--timestamp-column", default="timestamp", help="时间戳列名 (默认: timestamp)"
    )

    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        sys.exit(1)

    # 执行过滤
    success = filter_csv_by_timestamp(
        args.input_file, args.output_file, args.cutoff_timestamp, args.timestamp_column
    )

    if success:
        print("程序执行成功!")
    else:
        print("程序执行失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
