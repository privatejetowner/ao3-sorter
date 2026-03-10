#!/usr/bin/env python3
"""
扫描指定目录下的 ao3_sorted_*.html 文件，生成 tags.json
由 update.bat 自动调用，也可手动运行: python gen_tags.py [目录]
"""
import os
import sys
import json
import re


def count_works(filepath):
    """从HTML文件中统计作品数量"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 统计 work_id 出现次数（每篇作品有一个）
        count = len(re.findall(r'"work_id"', content))
        if count == 0:
            # 备选：统计 work-card 出现次数
            count = content.count("work-card")
        return count
    except:
        return 0


def extract_tag_name(filename):
    """从文件名提取tag名: ao3_sorted_桂瑞.html → 桂瑞"""
    name = filename
    name = re.sub(r"^ao3_sorted_", "", name)
    name = re.sub(r"\.html$", "", name)
    return name


def main():
    # 目录：命令行参数 或 当前目录
    target_dir = sys.argv[1] if len(sys.argv) >= 2 else os.getcwd()
    target_dir = os.path.abspath(target_dir)

    # 扫描文件
    files = [
        f for f in os.listdir(target_dir)
        if f.startswith("ao3_sorted_") and f.endswith(".html")
    ]
    files.sort()

    tags = []
    for f in files:
        filepath = os.path.join(target_dir, f)
        name = extract_tag_name(f)
        count = count_works(filepath)
        tags.append({
            "name": name,
            "file": f,
            "count": count,
        })
        print(f"  📄 {name}: {count} 篇作品")

    # 写入 tags.json
    output = os.path.join(target_dir, "tags.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已生成 tags.json（{len(tags)} 个tag）")


if __name__ == "__main__":
    main()
