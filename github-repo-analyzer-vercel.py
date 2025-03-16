# api/analyze.py (续)
                    # 只添加特定类型的文件
                    if any(item.endswith(ext) for ext in ['.py', '.js', '.java', '.go', '.rs', '.cs', '.php', '.rb', 
                                                         '.md', '.txt', '.json', '.yml', '.yaml']):
                        result[item] = None
        except Exception as e:
            logger.error(f"分析目录结构时出错: {e}")
            return str(e)
        
        return result
    
    structure = _analyze_dir(repo_dir)
    return structure

def analyze_repo(repo_url):
    """主分析函数，分析给定的GitHub仓库"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo")
    
    try:
        # 克隆仓库
        if not clone_repo(repo_url, repo_dir):
            return {"error": "克隆仓库失败"}
        
        # 获取仓库名称
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        # 分析结果
        result = {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "file_extensions": dict(get_file_extensions(repo_dir)),
            "config_files": analyze_config_files(repo_dir),
            "technologies": dict(find_technologies(repo_dir)),
            "architecture_patterns": dict(find_architecture_patterns(repo_dir)),
            "directory_structure": analyze_directory_structure(repo_dir)
        }
        
        # 清理
        shutil.rmtree(temp_dir)
        
        return result
    except Exception as e:
        logger.error(f"分析仓库时出错: {e}")
        # 清理
        shutil.rmtree(temp_dir)
        return {"error": str(e)}

# 创建一个从HTTP请求处理的入口点
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # 解析URL参数
        query_components = parse_qs(urlparse(self.path).query)
        repo_url = query_components.get('url', [''])[0]
        
        if not repo_url:
            self.wfile.write(json.dumps({"error": "请提供GitHub仓库URL"}).encode())
            return
        
        # 分析仓库
        result = analyze_repo(repo_url)
        
        # 发送结果
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
        return

# 如果直接运行脚本，则提供一个简单的命令行接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python analyze.py <GitHub仓库URL>")
        sys.exit(1)
    
    repo_url = sys.argv[1]
    result = analyze_repo(repo_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
