# GitHub仓库分析工具

一个简单的工具，可以快速分析GitHub仓库的技术栈和架构。
v0.1 2025-03-16

## 功能

- 分析GitHub仓库使用的编程语言
- 识别常用框架和库
- 检测架构模式
- 显示项目目录结构
- 分析配置文件和依赖项

![](https://raw.githubusercontent.com/jhfnetboy/MarkDownImg/main/img/202503162214564.png)



## 本地开发

1. 克隆仓库
   ```bash
   git clone <仓库URL>
   cd github-repo-analyzer
   ```

2. 安装依赖
   ```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

   pip install -r requirements.txt
   ```

3. 运行API服务器
   ```bash
   python api/analyze.py <GitHub仓库URL>
   ```

4. 在浏览器中打开index.html文件


## 部署到Vercel(option)

### 前提条件

- 一个Vercel账号
- Git已安装

### 部署步骤

1. Fork或克隆此仓库到你的GitHub账号

2. 在Vercel中导入项目
   - 登录Vercel账号
   - 点击"New Project"按钮
   - 从GitHub中选择此仓库
   - 保持默认设置不变，直接点击"Deploy"

3. 等待部署完成

4. 访问生成的URL，开始使用工具

## 注

本工具快速分析GitHub仓库的技术栈和架构，采用以下系统化方法：

1. **查看README文件**
   - 通常包含项目概述、技术栈清单和架构说明
   - 寻找技术标志、框架图或系统描述

2. **检查项目文件结构**
   - 根目录下的配置文件揭示框架和工具
   - 例如：package.json (Node.js)、requirements.txt (Python)、pom.xml (Java)
   - 文件夹结构通常反映架构模式(MVC, MVVM等)

3. **分析依赖项**
   - 检查包管理器文件了解所有依赖项
   - 区分核心框架和辅助工具

4. **查看文档目录**
   - docs/文件夹或wiki页面通常包含架构设计文档
   - 寻找架构图、数据流程图或部署图

5. **浏览源代码**
   - 入口文件(如main.py, index.js, App.java)提供架构线索
   - 查看代码组织方式和目录结构
   - 检查常用设计模式的应用

6. **利用辅助工具**
   - GitHub Insights提供语言分布统计
   - 第三方工具如CodeScene或SourceGraph可视化代码结构

7. **检查CI/CD配置**
   - .github/workflows、.gitlab-ci.yml或Jenkins文件
   - 部署流程常常显示架构组件和部署环境

8. **分析测试用例**
   - 测试目录揭示核心功能和系统边界
   - 集成测试展示系统组件间的交互

系统地收集这些信息后，你应该能够识别主要的技术栈组件、架构模式和系统设计思路。
