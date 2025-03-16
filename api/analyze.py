import os
import re
import json
import subprocess
import logging
from collections import Counter, defaultdict
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
from tqdm import tqdm
import tempfile
import shutil
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

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

def clone_repo(repo_url, target_dir=None):
    """克隆GitHub仓库到本地"""
    if target_dir is None:
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        target_dir = f"./temp_repos/{repo_name}"
    
    if os.path.exists(target_dir):
        logger.info(f"仓库目录已存在: {target_dir}")
        return target_dir
    
    logger.info(f"克隆仓库 {repo_url} 到 {target_dir}")
    try:
        subprocess.run(['git', 'clone', '--depth=1', repo_url, target_dir], check=True)
        return target_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"克隆仓库失败: {e}")
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
    try:
        def _analyze_dir(directory):
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    result[item] = _analyze_dir(item_path)
                else:
                    # 只添加特定类型的文件
                    if any(item.endswith(ext) for ext in ['.py', '.js', '.java', '.go', '.rs', '.cs', '.php', '.rb', 
                                                         '.md', '.txt', '.json', '.yml', '.yaml']):
                        result[item] = None
    except Exception as e:
        logger.error(f"分析目录结构时出错: {e}")
        return str(e)
    
    structure = _analyze_dir(repo_dir)
    return structure

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
def analyze_repo(repo_url):
    """主分析函数，分析给定的GitHub仓库"""
    # 定义历史文件路径
    history_file = "clone_history.txt"

    # 检查历史记录
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            cloned_repos = f.read().splitlines()
        if repo_url in cloned_repos:
            logger.info(f"仓库已存在于历史记录中: {repo_url}")
            return analyze_existing_repo(repo_url)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo")

    try:
        # 克隆仓库
        if not clone_repo(repo_url, repo_dir):
            return {"error": "克隆仓库失败"}

        # 记录克隆的仓库到历史文件
        with open(history_file, 'a') as f:
            f.write(repo_url + "\n")

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