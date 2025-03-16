import os
import sys
import json
import http.server
import socketserver
import traceback
from urllib.parse import urlparse, parse_qs
from api.analyze import analyze_repo
import subprocess

# 设置端口
PORT = 8000

class GitRepoAnalyzerHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """重写日志方法，添加更多信息"""
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format % args))
    
    def do_GET(self):
        # 解析URL
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        print(f"收到请求: {self.path}")
        
        # 处理API请求
        if path.startswith('/api/analyze'):
            print(f"处理API请求: {self.path}")
            self.handle_api_request(parsed_url)
            return
        
        # 处理静态文件请求
        if path == '/':
            print("处理根路径请求，返回index.html")
            self.path = '/index.html'
        
        try:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            print(f"处理静态文件请求时出错: {str(e)}")
            traceback.print_exc()
            self.send_error_response(500, f"服务器内部错误: {str(e)}")
    
    def handle_api_request(self, parsed_url):
        # 解析查询参数
        query_params = parse_qs(parsed_url.query)
        repo_url = query_params.get('url', [''])[0]
        
        print(f"分析仓库: {repo_url}")
        
        if not repo_url:
            print("未提供仓库URL")
            self.send_error_response(400, "请提供GitHub仓库URL")
            return
        
        try:
            # 打印当前工作目录和临时目录
            current_dir = os.getcwd()
            temp_dir = os.path.join(current_dir, "temp_repos")
            print(f"当前工作目录: {current_dir}")
            print(f"临时目录: {temp_dir}")
            print(f"临时目录是否存在: {os.path.exists(temp_dir)}")
            
            # 检查git是否可用
            try:
                git_version = subprocess.run(['git', '--version'], capture_output=True, text=True, check=True)
                print(f"Git版本: {git_version.stdout.strip()}")
            except Exception as e:
                print(f"检查Git版本时出错: {e}")
            
            # 检查仓库名称
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            expected_repo_dir = os.path.join(temp_dir, repo_name)
            print(f"预期的仓库目录: {expected_repo_dir}")
            print(f"预期的仓库目录是否存在: {os.path.exists(expected_repo_dir)}")
            
            # 分析仓库
            print(f"开始分析仓库: {repo_url}")
            result = analyze_repo(repo_url)
            print(f"仓库分析完成: {repo_url}")
            
            # 检查结果
            if "error" in result:
                print(f"分析返回错误: {result['error']}")
            else:
                print(f"分析成功，结果包含 {len(result)} 个键")
                print(f"结果键: {', '.join(result.keys())}")
            
            # 发送响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_json = json.dumps(result, ensure_ascii=False)
            print(f"发送响应 (长度: {len(response_json)})")
            self.wfile.write(response_json.encode('utf-8'))
        except Exception as e:
            print(f"分析仓库时出错: {str(e)}")
            traceback.print_exc()
            self.send_error_response(500, f"分析仓库时出错: {str(e)}")
    
    def send_error_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_json = json.dumps({"error": message}, ensure_ascii=False)
        self.wfile.write(error_json.encode('utf-8'))

def run_server():
    # 确保当前工作目录是项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查index.html是否存在
    if os.path.exists('index.html'):
        print("找到index.html文件")
    else:
        print("警告: index.html文件不存在!")
    
    # 创建临时目录
    temp_repos_dir = os.path.join(script_dir, "temp_repos")
    os.makedirs(temp_repos_dir, exist_ok=True)
    print(f"创建临时目录: {temp_repos_dir}")
    
    # 检查临时目录权限
    try:
        test_file = os.path.join(temp_repos_dir, "test_write.txt")
        with open(test_file, 'w') as f:
            f.write("测试写入权限")
        os.remove(test_file)
        print("临时目录写入权限正常")
    except Exception as e:
        print(f"警告: 临时目录写入测试失败: {e}")
    
    # 打印环境信息
    print(f"Python版本: {sys.version}")
    print(f"系统平台: {sys.platform}")
    print(f"脚本目录: {script_dir}")
    print(f"临时目录: {temp_repos_dir}")
    
    # 启动服务器，自动尝试不同端口
    handler = GitRepoAnalyzerHandler
    port = PORT
    max_port = PORT + 10  # 最多尝试10个端口
    
    while port <= max_port:
        try:
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"服务器启动在 http://localhost:{port}")
                print(f"按 Ctrl+C 停止服务器")
                httpd.serve_forever()
                break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"端口 {port} 已被占用，尝试下一个端口...")
                port += 1
            else:
                print(f"启动服务器时出错: {str(e)}")
                traceback.print_exc()
                break
        except Exception as e:
            print(f"启动服务器时出错: {str(e)}")
            traceback.print_exc()
            break
    
    if port > max_port:
        print(f"无法找到可用端口 ({PORT}-{max_port})，请手动指定其他端口")

if __name__ == "__main__":
    run_server() 