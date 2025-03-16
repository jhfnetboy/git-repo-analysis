import os
import re
import json
import subprocess
import logging
from collections import Counter, defaultdict
import argparse
from pathlib import Path
import tempfile
import shutil
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from tqdm import tqdm
import traceback

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 技术栈关键词映射
TECH_KEYWORDS = {
    # 编程语言
    'python': ['python', '.py', 'requirements.txt', 'setup.py', 'pytest', 'pipenv', 'pip'],
    'javascript': ['javascript', '.js', 'node_modules', 'package.json', 'npm', 'yarn', 'webpack', 'babel', 'eslint'],
    'typescript': ['typescript', '.ts', 'tsconfig.json', 'tslint'],
    'java': ['java', '.java', 'maven', 'gradle', 'pom.xml', 'build.gradle', 'spring', 'jakarta', 'javax'],
    'go': ['golang', '.go', 'go.mod', 'go.sum'],
    'rust': ['rust', '.rs', 'cargo.toml', 'rustc'],
    'c++': ['c++', '.cpp', '.hpp', 'cmake', 'makefile', 'clang', 'gcc'],
    'c#': ['c#', '.cs', '.net', 'dotnet', 'nuget', 'csproj', 'sln'],
    
    # 前端框架
    'react': ['react', 'jsx', 'tsx', 'react-dom', 'create-react-app', 'next.js'],
    'vue': ['vue', 'vuex', 'nuxt', '.vue'],
    'angular': ['angular', 'ng', 'ngmodule', '@angular'],
    'svelte': ['svelte', '.svelte'],
    
    # 后端框架
    'django': ['django', 'settings.py', 'urls.py', 'views.py', 'models.py'],
    'flask': ['flask', 'app.py', 'wsgi.py'],
    'express': ['express', 'app.js', 'routes'],
    'spring boot': ['spring-boot', 'springboot', 'application.properties', 'application.yml'],
    'laravel': ['laravel', '.blade.php', 'artisan'],
    'fastapi': ['fastapi', 'uvicorn'],
    
    # 数据库
    'postgresql': ['postgresql', 'postgres', 'psql', 'pg'],
    'mysql': ['mysql', 'mariadb'],
    'mongodb': ['mongodb', 'mongo', 'mongoose'],
    'redis': ['redis', 'redisio'],
    'elasticsearch': ['elasticsearch', 'elastic', 'elk'],
    'sqlite': ['sqlite', '.db', '.sqlite'],
    
    # 消息队列
    'kafka': ['kafka', 'kclient'],
    'rabbitmq': ['rabbitmq', 'amqp'],
    'celery': ['celery', 'celeryconfig'],
    
    # 容器化
    'docker': ['docker', 'dockerfile', 'docker-compose'],
    'kubernetes': ['kubernetes', 'k8s', 'kubectl', 'helm'],
    
    # CI/CD
    'jenkins': ['jenkins', 'jenkinsfile'],
    'github actions': ['github actions', 'workflows', '.github/workflows'],
    'gitlab ci': ['gitlab-ci', '.gitlab-ci.yml'],
    'travis': ['travis', '.travis.yml'],
    
    # 云服务
    'aws': ['aws', 'amazon web services', 's3', 'ec2', 'lambda', 'cloudformation', 'dynamodb'],
    'azure': ['azure', 'microsoft azure', 'cosmos db', 'azure functions'],
    'gcp': ['gcp', 'google cloud', 'google cloud platform', 'bigquery', 'cloud run'],
    
    # 其他工具
    'graphql': ['graphql', '.gql', 'apollo'],
    'rest api': ['rest', 'restful', 'api', 'endpoint'],
    'websocket': ['websocket', 'ws', 'socket.io'],
    'oauth': ['oauth', 'jwt', 'authentication', 'authorization'],
    'webpack': ['webpack', 'webpack.config.js'],
    'babel': ['babel', '.babelrc'],
    'sass': ['sass', 'scss', '.scss'],
    'less': ['less', '.less'],
    'tensorflow': ['tensorflow', 'tf', 'keras'],
    'pytorch': ['pytorch', 'torch'],
}

# 架构模式关键词
ARCHITECTURE_PATTERNS = {
    'microservices': ['microservice', 'service discovery', 'api gateway', 'circuit breaker'],
    'monolith': ['monolith', 'monolithic'],
    'serverless': ['serverless', 'faas', 'function as a service', 'lambda'],
    'mvc': ['model', 'view', 'controller', 'mvc'],
    'mvvm': ['model', 'view', 'viewmodel', 'mvvm'],
    'event driven': ['event', 'subscriber', 'publisher', 'event driven', 'event sourcing'],
    'domain driven': ['domain driven', 'ddd', 'bounded context', 'aggregate'],
    'clean architecture': ['clean architecture', 'usecase', 'entity', 'repository', 'presenter'],
    'hexagonal': ['hexagonal', 'ports and adapters', 'adapter', 'port'],
}

def clone_repo(repo_url, target_dir):
    """克隆GitHub仓库到本地"""
    logger.info(f"准备克隆仓库 {repo_url} 到 {target_dir}")
    
    # 检查目标目录是否已存在
    if os.path.exists(target_dir):
        logger.info(f"目标目录已存在: {target_dir}")
        # 检查是否是有效的git仓库
        git_dir = os.path.join(target_dir, ".git")
        if os.path.exists(git_dir):
            logger.info(f"目标目录是有效的git仓库: {target_dir}")
            return target_dir
        else:
            logger.warning(f"目标目录存在但不是有效的git仓库，将删除: {target_dir}")
            try:
                shutil.rmtree(target_dir)
                logger.info(f"已删除无效目录: {target_dir}")
            except Exception as e:
                logger.error(f"删除无效目录时出错: {e}")
                return None
    
    # 确保父目录存在
    parent_dir = os.path.dirname(target_dir)
    if not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
            logger.info(f"已创建父目录: {parent_dir}")
        except Exception as e:
            logger.error(f"创建父目录时出错: {e}")
            return None
    
    # 执行克隆
    logger.info(f"开始克隆仓库 {repo_url} 到 {target_dir}")
    try:
        # 使用subprocess克隆
        result = subprocess.run(
            ['git', 'clone', '--depth=1', repo_url, target_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False  # 不自动抛出异常
        )
        
        # 检查结果
        if result.returncode != 0:
            logger.error(f"克隆失败，返回码: {result.returncode}")
            logger.error(f"错误输出: {result.stderr}")
            return None
        
        # 验证目录是否存在且包含.git
        if os.path.exists(target_dir) and os.path.exists(os.path.join(target_dir, ".git")):
            logger.info(f"克隆成功: {target_dir}")
            return target_dir
        else:
            logger.error(f"克隆似乎成功，但目录不存在或不是有效的git仓库: {target_dir}")
            return None
    except Exception as e:
        logger.error(f"克隆过程中出错: {e}")
        return None

def get_file_extensions(repo_dir):
    """获取仓库中的文件扩展名统计"""
    extensions = Counter()
    
    for root, _, files in os.walk(repo_dir):
        # 排除 .git 目录和 node_modules
        if '.git' in root or 'node_modules' in root:
            continue
        
        for file in files:
            extension = os.path.splitext(file)[1].lower()
            if extension:
                extensions[extension] += 1
    
    return extensions

def get_language_stats(repo_dir):
    """使用git-linguist获取语言统计（如果可用）"""
    try:
        result = subprocess.run(['linguist', repo_dir], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        
        languages = {}
        for line in lines:
            if ':' in line:
                lang, percentage = line.split(':')
                languages[lang.strip()] = float(percentage.strip().replace('%', ''))
        
        return languages
    except:
        logger.warning("git-linguist不可用，跳过语言统计")
        return None

def analyze_config_files(repo_dir):
    """分析常见配置文件确定技术栈"""
    config_files = {
        'package.json': 'Node.js/JavaScript',
        'requirements.txt': 'Python',
        'Pipfile': 'Python',
        'pom.xml': 'Java/Maven',
        'build.gradle': 'Java/Gradle',
        'composer.json': 'PHP',
        'Gemfile': 'Ruby',
        'go.mod': 'Go',
        'cargo.toml': 'Rust',
        'Dockerfile': 'Docker',
        'docker-compose.yml': 'Docker Compose',
        'Jenkinsfile': 'Jenkins',
        '.github/workflows': 'GitHub Actions',
        '.gitlab-ci.yml': 'GitLab CI',
        'kubernetes': 'Kubernetes',
        'helm': 'Helm Charts',
        'terraform': 'Terraform',
        'angular.json': 'Angular',
        'vue.config.js': 'Vue.js',
        'next.config.js': 'Next.js',
        'nuxt.config.js': 'Nuxt.js',
        'tsconfig.json': 'TypeScript',
        'webpack.config.js': 'Webpack',
        '.babelrc': 'Babel',
    }
    
    found_configs = {}
    
    for root, dirs, files in os.walk(repo_dir):
        # 排除隐藏文件夹和node_modules
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
        
        for filename in files:
            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath, repo_dir)
            
            for config_pattern, tech in config_files.items():
                if config_pattern in relpath:
                    found_configs[config_pattern] = tech
                    
                    # 如果是package.json，解析依赖项
                    if filename == 'package.json':
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                package_data = json.load(f)
                                all_deps = {}
                                for dep_type in ['dependencies', 'devDependencies']:
                                    if dep_type in package_data:
                                        all_deps.update(package_data[dep_type])
                                found_configs['node_dependencies'] = all_deps
                        except Exception as e:
                            logger.error(f"解析{filepath}时出错: {e}")
    
    return found_configs

def analyze_directory_structure(repo_dir):
    """分析目录结构"""
    result = {}
    
    def _analyze_dir(directory):
        dir_contents = {}
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    dir_contents[item] = _analyze_dir(item_path)
                else:
                    # 只添加特定类型的文件
                    if any(item.endswith(ext) for ext in ['.py', '.js', '.java', '.go', '.rs', '.cs', '.php', '.rb', 
                                                         '.md', '.txt', '.json', '.yml', '.yaml']):
                        dir_contents[item] = None
        except Exception as e:
            logger.error(f"分析目录结构时出错: {e}")
            return str(e)
        return dir_contents
    
    return _analyze_dir(repo_dir)

def find_technologies(repo_dir):
    """在代码和配置文件中查找技术关键词"""
    technologies = Counter()
    
    # 遍历文件，查找关键词
    for root, _, files in tqdm(list(os.walk(repo_dir)), desc="查找技术关键词"):
        # 排除 .git 目录和 node_modules
        if '.git' in root or 'node_modules' in root:
            continue
        
        for file in files:
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, repo_dir)
            
            # 检查文件路径和名称中的关键词
            for tech, keywords in TECH_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in relpath.lower():
                        technologies[tech] += 1
            
            # 对小文件进行内容分析
            try:
                file_size = os.path.getsize(filepath)
                if file_size < 500000:  # 限制在500KB以下
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        
                        # 检查内容中的技术关键词
                        for tech, keywords in TECH_KEYWORDS.items():
                            for keyword in keywords:
                                count = content.count(keyword.lower())
                                if count > 0:
                                    technologies[tech] += count
            except Exception:
                pass
    
    return technologies

def find_architecture_patterns(repo_dir):
    """查找常见架构模式的迹象"""
    patterns = Counter()
    
    # 检查目录结构是否符合特定架构模式
    dirs = os.listdir(repo_dir)
    
    # MVC 结构检测
    if all(d in str(dirs).lower() for d in ['model', 'view', 'controller']):
        patterns['mvc'] += 10
    elif os.path.exists(os.path.join(repo_dir, 'controllers')) and os.path.exists(os.path.join(repo_dir, 'models')):
        patterns['mvc'] += 5
    
    # 微服务架构检测
    services_dirs = ['services', 'microservices', 'api-gateway']
    if any(d.lower() in str(dirs).lower() for d in services_dirs):
        patterns['microservices'] += 5
    
    # 遍历部分文件查找架构线索
    architecture_clues = defaultdict(int)
    file_count = 0
    
    for root, _, files in os.walk(repo_dir):
        # 排除 .git 目录和 node_modules
        if '.git' in root or 'node_modules' in root:
            continue
        
        for file in files:
            if file_count > 100:  # 限制分析的文件数量
                break
                
            filepath = os.path.join(root, file)
            
            # 只分析文本文件
            if not any(file.endswith(ext) for ext in ['.md', '.txt', '.py', '.js', '.java', '.go', '.rs', '.cs', '.php']):
                continue
                
            try:
                file_size = os.path.getsize(filepath)
                if file_size < 100000:  # 限制在100KB以下
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        
                        # 检查架构模式关键词
                        for pattern, keywords in ARCHITECTURE_PATTERNS.items():
                            for keyword in keywords:
                                count = content.count(keyword.lower())
                                if count > 0:
                                    architecture_clues[pattern] += count
                        
                        file_count += 1
            except Exception:
                pass
    
    # 合并结果
    for pattern, count in architecture_clues.items():
        patterns[pattern] = count
    
    return patterns

def analyze_existing_repo(repo_url):
    """分析已经克隆过的仓库"""
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    
    # 尝试多个可能的路径
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp_repos", repo_name),  # 相对于脚本的路径
        os.path.join("temp_repos", repo_name),  # 相对于当前工作目录的路径
        f"./temp_repos/{repo_name}",  # 另一种相对路径表示
        os.path.abspath(f"temp_repos/{repo_name}")  # 绝对路径
    ]
    
    repo_dir = None
    for path in possible_paths:
        if os.path.exists(path):
            repo_dir = path
            logger.info(f"找到仓库目录: {repo_dir}")
            break
    
    if not repo_dir:
        logger.error(f"仓库目录不存在，尝试过以下路径: {possible_paths}")
        return {"error": "仓库目录不存在"}
    
    try:
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
        
        return result
    except Exception as e:
        logger.error(f"分析仓库时出错: {e}")
        return {"error": str(e)}

def analyze_repo(repo_url):
    """主分析函数，分析给定的GitHub仓库"""
    # 获取仓库名称
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    
    # 定义临时目录和永久目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)  # 项目根目录
    
    # 永久存储目录
    permanent_dir = os.path.join(base_dir, "temp_repos")
    permanent_repo_dir = os.path.join(permanent_dir, repo_name)
    
    # 确保永久目录存在
    os.makedirs(permanent_dir, exist_ok=True)
    logger.info(f"永久存储目录: {permanent_dir}")
    
    # 检查永久目录中是否已有该仓库
    if os.path.exists(permanent_repo_dir):
        logger.info(f"仓库已存在于永久目录中: {permanent_repo_dir}")
        try:
            # 尝试使用已有仓库
            result = {
                "repo_url": repo_url,
                "repo_name": repo_name,
                "file_extensions": dict(get_file_extensions(permanent_repo_dir)),
                "config_files": analyze_config_files(permanent_repo_dir),
                "technologies": dict(find_technologies(permanent_repo_dir)),
                "architecture_patterns": dict(find_architecture_patterns(permanent_repo_dir)),
                "directory_structure": analyze_directory_structure(permanent_repo_dir)
            }
            logger.info(f"使用已有仓库分析成功: {permanent_repo_dir}")
            return result
        except Exception as e:
            logger.warning(f"使用已有仓库分析失败: {e}，将重新克隆")
            # 如果分析失败，删除已有目录并重新克隆
            try:
                shutil.rmtree(permanent_repo_dir)
                logger.info(f"已删除失效的仓库目录: {permanent_repo_dir}")
            except Exception as rm_err:
                logger.warning(f"删除失效目录时出错: {rm_err}")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    logger.info(f"创建临时目录: {temp_dir}")
    
    try:
        # 直接克隆到永久目录
        logger.info(f"尝试直接克隆到永久目录: {permanent_repo_dir}")
        if clone_repo(repo_url, permanent_repo_dir):
            logger.info(f"成功克隆到永久目录: {permanent_repo_dir}")
            # 分析结果
            result = {
                "repo_url": repo_url,
                "repo_name": repo_name,
                "file_extensions": dict(get_file_extensions(permanent_repo_dir)),
                "config_files": analyze_config_files(permanent_repo_dir),
                "technologies": dict(find_technologies(permanent_repo_dir)),
                "architecture_patterns": dict(find_architecture_patterns(permanent_repo_dir)),
                "directory_structure": analyze_directory_structure(permanent_repo_dir)
            }
            return result
        
        # 如果直接克隆失败，尝试克隆到临时目录
        logger.info(f"直接克隆失败，尝试克隆到临时目录")
        temp_repo_dir = os.path.join(temp_dir, "repo")
        if not clone_repo(repo_url, temp_repo_dir):
            logger.error(f"克隆到临时目录也失败了")
            return {"error": "克隆仓库失败"}
        
        # 分析结果
        logger.info(f"使用临时目录进行分析: {temp_repo_dir}")
        result = {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "file_extensions": dict(get_file_extensions(temp_repo_dir)),
            "config_files": analyze_config_files(temp_repo_dir),
            "technologies": dict(find_technologies(temp_repo_dir)),
            "architecture_patterns": dict(find_architecture_patterns(temp_repo_dir)),
            "directory_structure": analyze_directory_structure(temp_repo_dir)
        }
        
        # 复制到永久目录
        try:
            logger.info(f"尝试将临时目录复制到永久目录: {permanent_repo_dir}")
            if os.path.exists(permanent_repo_dir):
                shutil.rmtree(permanent_repo_dir)
            shutil.copytree(temp_repo_dir, permanent_repo_dir)
            logger.info(f"成功复制到永久目录: {permanent_repo_dir}")
        except Exception as e:
            logger.warning(f"复制到永久目录时出错: {e}")
        
        return result
    except Exception as e:
        logger.error(f"分析仓库时出错: {e}")
        return {"error": str(e)}
    finally:
        # 清理临时目录
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录时出错: {e}")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 检查路径是否匹配 /api/analyze
        if not self.path.startswith('/api/analyze'):
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Not Found".encode())
            return
            
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # 允许跨域请求
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
    import argparse
    
    parser = argparse.ArgumentParser(description='分析GitHub仓库的技术栈和架构')
    parser.add_argument('repo_url', help='GitHub仓库URL')
    parser.add_argument('-o', '--output', help='输出JSON文件路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        print(f"分析仓库: {args.repo_url}")
    
    try:
        result = analyze_repo(args.repo_url)
        
        # 格式化JSON输出
        formatted_json = json.dumps(result, ensure_ascii=False, indent=2)
        
        # 输出到文件或标准输出
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(formatted_json)
            print(f"分析结果已保存到: {args.output}")
        else:
            print(formatted_json)
            
        sys.exit(0)
    except Exception as e:
        print(f"分析仓库时出错: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)