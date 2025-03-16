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
                            logger.error(f"解析package.json失败: {e}")
                    
                    # 如果是requirements.txt，解析Python依赖
                    if filename == 'requirements.txt':
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                python_deps = {}
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#'):
                                        parts = re.split(r'[=<>]', line)
                                        package = parts[0].strip()
                                        python_deps[package] = True
                                found_configs['python_dependencies'] = python_deps
                        except Exception as e:
                            logger.error(f"解析requirements.txt失败: {e}")
    
    return found_configs

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

def analyze_imports(repo_dir):
    """分析代码中的imports/requires来确定主要依赖"""
    imports = defaultdict(int)
    
    # 不同语言的import/require模式
    import_patterns = {