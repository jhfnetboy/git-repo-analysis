#!/usr/bin/env python3
import os
import sys
import json
import logging
from api.analyze import analyze_repo

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_analyze.py <GitHub仓库URL>")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    print(f"测试分析仓库: {repo_url}")
    
    # 打印环境信息
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python版本: {sys.version}")
    
    # 创建临时目录
    temp_dir = os.path.join(os.getcwd(), "temp_repos")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"临时目录: {temp_dir}")
    print(f"临时目录是否存在: {os.path.exists(temp_dir)}")
    
    # 分析仓库
    try:
        result = analyze_repo(repo_url)
        
        # 检查结果
        if "error" in result:
            print(f"分析返回错误: {result['error']}")
            sys.exit(1)
        
        # 打印结果
        print(f"分析成功，结果包含 {len(result)} 个键")
        print(f"结果键: {', '.join(result.keys())}")
        
        # 格式化输出
        formatted_json = json.dumps(result, ensure_ascii=False, indent=2)
        print("\n分析结果:")
        print(formatted_json)
        
        # 保存到文件
        output_file = f"{repo_url.split('/')[-1]}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_json)
        print(f"\n结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 