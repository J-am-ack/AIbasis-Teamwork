# 北京大学饮食规划系统

这是一个为北京大学学生设计的个性化饮食规划系统，基于Flask框架和大模型技术。该系统能够根据学生的个人信息、课表安排和健康目标，生成个性化的饮食建议，并提供日程安排。

## 功能特点

- **个人信息收集**：收集用户的基本信息和健康目标
- **课表解析**：使用大模型解析用户提供的课表信息
- **营养需求计算**：基于用户信息计算个性化的营养需求
- **饮食推荐**：结合课表时间和地点，推荐最适合的食堂和菜品
- **实际饮食记录**：用户可以记录实际的饮食情况
- **趋势分析**：分析用户的饮食趋势，提供改进建议
- **反馈调整**：根据用户反馈调整饮食计划

## 技术栈

- **后端**：Python Flask
- **前端**：HTML + CSS + JavaScript
- **大模型集成**：使用DeepSeek API进行课表解析、饮食推荐等任务
- **数据可视化**：使用Chart.js展示饮食趋势

## 系统流程

1. 用户输入个人信息和健康目标
2. 系统解析用户课表获取时间和位置信息
3. 计算用户个性化营养需求
4. 结合食堂信息生成饮食推荐
5. 用户查看推荐结果并记录实际饮食
6. 系统跟踪分析用户饮食趋势
7. 定期调整推荐策略以适应用户变化

## 数据集

系统使用以下数据集：
- 北京大学食堂菜谱数据集
- 饮食健康关联知识图谱基础数据库
- 饮食健康问答数据集

## 安装和运行

1. 克隆项目
```bash
git clone https://github.com/yourusername/pku-meal-planner.git
cd pku-meal-planner
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行应用
```bash
python app.py
```

4. 访问应用
打开浏览器，访问 http://localhost:5000

## 目录结构

```
pku-meal-planner/
├── app.py                      # 主应用文件
├── 北京大学食堂菜谱数据集-66eb503d54.json   # 食堂菜谱数据
├── 饮食健康关联知识图谱基础数据库-473840c6d1.json  # 知识图谱数据
├── 饮食健康问答数据集-*.json     # 问答数据集
├── static/                     # 静态资源
│   ├── css/                    # CSS样式
│   │   └── style.css           # 主样式文件
│   └── js/                     # JavaScript脚本
│       └── script.js           # 主脚本文件
└── templates/                  # HTML模板
    ├── index.html              # 首页
    ├── profile.html            # 个人信息页
    ├── schedule.html           # 课表输入页
    └── result.html             # 结果展示页
```

## 未来改进

- 增加数据库支持，存储用户信息和饮食记录
- 添加用户登录系统，支持多用户
- 优化移动端界面
- 添加更多食堂和菜品数据
- 集成图像识别功能，支持拍照记录饮食

## 开发者

本项目由 [Your Name] 开发

## 许可证

本项目使用 MIT 许可证