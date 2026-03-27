# -*- coding: utf-8 -*-
"""
快速启动脚本 - 用于检查环境和启动应用
"""

import subprocess
import sys
import os


def check_environment():
    """检查运行环境"""
    print("正在检查运行环境...")

    # 检查Python版本
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("   请使用 Python 3.8 或更高版本")
        return False
    print(f"✓ Python版本: {version.major}.{version.minor}.{version.micro}")

    # 检查必要模块
    required_modules = [
        'streamlit',
        'langchain',
        'chromadb',
        'dashscope'
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module} 已安装")
        except ImportError:
            print(f"✗ {module} 未安装")
            missing_modules.append(module)

    if missing_modules:
        print(f"\n缺少以下模块: {', '.join(missing_modules)}")
        print("正在安装...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])

    return True


def check_data_files():
    """检查数据文件"""
    print("\n正在检查数据文件...")

    required_files = [
        'data/external/records.csv',
        'data/products.json',
    ]

    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 不存在")

    # 检查知识库
    if os.path.exists('chroma_db'):
        print("✓ 向量知识库已存在")
    else:
        print("! 向量知识库不存在，首次运行会自动创建")


def main():
    print("=" * 50)
    print("智扫通机器人智能客服系统 - 环境检查")
    print("=" * 50)
    print()

    if check_environment():
        check_data_files()
        print("\n" + "=" * 50)
        print("环境检查完成！")
        print("=" * 50)
        print("\n启动应用: streamlit run app.py")
        print("或运行: 启动应用.bat")
    else:
        print("\n环境检查失败，请解决上述问题后重试")


if __name__ == "__main__":
    main()