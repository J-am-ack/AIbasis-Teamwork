// 等待DOM加载完毕
document.addEventListener('DOMContentLoaded', function() {
    // 初始化登录页面功能
    initLandingPage();
    
    // 初始化星期切换功能
    initWeekTabs();
    
    // 初始化记录饮食功能
    initRecordMeal();
    
    // 初始化调整计划功能
    initAdjustPlan();
    
    // 初始化趋势分析功能
    initTrendAnalysis();
    
    // 初始化AI健康助手功能
    initAIAssistant();
    
    // 初始化每周计划功能
    initWeeklyPlan();
    
    // 初始化生成推荐功能
    initGenerateRecommendation();
});

// 初始化登录页面功能
function initLandingPage() {
    // 处理导航栏响应式
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }

    // 处理健康贴士
    const dailyTip = document.getElementById('daily-tip');
    const refreshTipBtn = document.getElementById('refresh-tip');
    
    if (dailyTip && refreshTipBtn) {
        // 更新健康贴士
        function updateHealthTip() {
            fetch('/get_health_tip')
                .then(response => response.json())
                .then(data => {
                    dailyTip.innerHTML = `
                        <h3>${data.title}</h3>
                        <p>${data.content}</p>
                    `;
                })
                .catch(error => {
                    console.error('获取健康贴士失败:', error);
                });
        }

        // 点击刷新按钮更新贴士
        refreshTipBtn.addEventListener('click', updateHealthTip);
        
        // 每小时自动更新一次
        setInterval(updateHealthTip, 3600000);
    }

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                window.scrollTo({
                    top: target.offsetTop - 80, // 考虑导航栏高度
                    behavior: 'smooth'
                });
            }
        });
    });

    // 滚动动画
    function revealOnScroll() {
        const elements = document.querySelectorAll('.feature-card, .process-step, .canteen-card');
        const windowHeight = window.innerHeight;
        
        elements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            if (elementTop < windowHeight - 100) {
                element.classList.add('revealed');
            }
        });
    }
    
    // 初始检查
    revealOnScroll();
    
    // 滚动时检查
    window.addEventListener('scroll', revealOnScroll);
    
    // 添加导航栏滚动效果
    const navbar = document.querySelector('.pku-navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // 添加特效
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// 初始化星期切换功能
function initWeekTabs() {
    const dayTabs = document.querySelectorAll('.day-tab');
    const dayPlans = document.querySelectorAll('.day-plan');
    
    if (!dayTabs.length) return;
    
    dayTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const day = this.getAttribute('data-day');
            
            // 移除所有活动状态
            dayTabs.forEach(tab => tab.classList.remove('active'));
            dayPlans.forEach(plan => plan.classList.remove('active'));
            
            // 设置当前标签和计划为活动状态
            this.classList.add('active');
            document.getElementById('plan-' + day).classList.add('active');
        });
    });
}

// 初始化记录饮食功能
function initRecordMeal() {
    const recordButtons = document.querySelectorAll('.record-meal-btn');
    const modal = document.getElementById('record-meal-modal');
    const closeModal = document.querySelector('.close-modal');
    const mealForm = document.getElementById('actual-meal-form');
    
    if (!recordButtons.length || !modal) return;
    
    // 打开弹窗
    recordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const day = this.getAttribute('data-day');
            const meal = this.getAttribute('data-meal');
            const foods = JSON.parse(this.getAttribute('data-foods'));
            
            // 填充推荐食物列表
            const foodsList = document.getElementById('recommended-foods-list');
            foodsList.innerHTML = '';
            foods.forEach(food => {
                const li = document.createElement('li');
                li.textContent = food;
                foodsList.appendChild(li);
            });
            
            // 存储当前记录的信息
            modal.setAttribute('data-day', day);
            modal.setAttribute('data-meal', meal);
            
            // 显示弹窗
            modal.style.display = 'flex';
        });
    });
    
    // 关闭弹窗
    if (closeModal) {
        closeModal.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
    
    // 点击弹窗外部关闭
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // 提交记录表单
    if (mealForm) {
        mealForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const day = modal.getAttribute('data-day');
            const meal = modal.getAttribute('data-meal');
            const actualFoods = document.getElementById('actual-foods').value.split('\n').filter(f => f.trim());
            const actualCalories = document.getElementById('actual-calories').value;
            const satisfaction = document.getElementById('satisfaction').value;
            const notes = document.getElementById('notes').value;
            
            const recordData = {
                day: day,
                meal: meal,
                actual_foods: actualFoods,
                actual_calories: parseInt(actualCalories) || 0,
                satisfaction: satisfaction,
                notes: notes
            };
            
            // 发送记录到服务器
            fetch('/record_meal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(recordData),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('饮食记录已保存！');
                    modal.style.display = 'none';
                    
                    // 清空表单
                    document.getElementById('actual-foods').value = '';
                    document.getElementById('actual-calories').value = '';
                    document.getElementById('notes').value = '';
                } else {
                    alert('保存失败：' + data.message);
                }
            })
            .catch(error => {
                console.error('错误:', error);
                alert('发生错误，请稍后重试');
            });
        });
    }
}

// 初始化调整计划功能
function initAdjustPlan() {
    const adjustButton = document.getElementById('adjust-plan-btn');
    
    if (!adjustButton) return;
    
    adjustButton.addEventListener('click', function() {
        const feedback = document.getElementById('feedback').value.trim();
        
        if (!feedback) {
            alert('请输入您的反馈意见');
            return;
        }
        
        // 显示加载状态
        adjustButton.disabled = true;
        adjustButton.textContent = '正在调整...';
        
        // 发送反馈到服务器
        fetch('/adjust_plan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ feedback: feedback }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('饮食计划已根据您的反馈进行调整！页面将刷新以显示新的计划。');
                location.reload();
            } else {
                alert('调整失败：' + data.message);
                adjustButton.disabled = false;
                adjustButton.textContent = '调整计划';
            }
        })
        .catch(error => {
            console.error('错误:', error);
            alert('发生错误，请稍后重试');
            adjustButton.disabled = false;
            adjustButton.textContent = '调整计划';
        });
    });
}

// 初始化趋势分析功能
function initTrendAnalysis() {
    const analyzeButton = document.getElementById('analyze-trends-btn');
    const trendResults = document.getElementById('trend-results');
    const trendsAnalysis = document.getElementById('trends-analysis');
    
    if (!analyzeButton || !trendResults || !trendsAnalysis) return;
    
    analyzeButton.addEventListener('click', function() {
        // 显示加载状态
        analyzeButton.disabled = true;
        analyzeButton.textContent = '分析中...';
        
        // 获取趋势分析数据
        fetch('/analyze_trends')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 显示分析结果
                    trendResults.style.display = 'block';
                    trendsAnalysis.innerHTML = '<h3>饮食趋势分析</h3><div class="analysis-content">' + data.analysis + '</div>';
                    
                    // 绘制图表
                    if (data.daily_calories && Object.keys(data.daily_calories).length > 0) {
                        const ctx = document.getElementById('trends-chart').getContext('2d');
                        
                        // 如果已存在图表，销毁它
                        if (window.caloriesChart) {
                            window.caloriesChart.destroy();
                        }
                        
                        // 创建新图表
                        window.caloriesChart = new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: Object.keys(data.daily_calories),
                                datasets: [{
                                    label: '每日热量摄入 (卡路里)',
                                    data: Object.values(data.daily_calories),
                                    backgroundColor: 'rgba(128, 0, 0, 0.2)',
                                    borderColor: 'rgba(128, 0, 0, 1)',
                                    borderWidth: 2,
                                    tension: 0.1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    y: {
                                        beginAtZero: false,
                                        title: {
                                            display: true,
                                            text: '热量 (卡路里)'
                                        }
                                    },
                                    x: {
                                        title: {
                                            display: true,
                                            text: '日期'
                                        }
                                    }
                                }
                            }
                        });
                    } else {
                        document.getElementById('trends-chart-container').innerHTML = '<p class="no-data">没有足够的数据来生成图表。请记录您的饮食后再试。</p>';
                    }
                } else {
                    alert('获取趋势分析失败：' + data.message);
                }
                
                // 恢复按钮状态
                analyzeButton.disabled = false;
                analyzeButton.textContent = '分析趋势';
            })
            .catch(error => {
                console.error('错误:', error);
                alert('发生错误，请稍后重试');
                analyzeButton.disabled = false;
                analyzeButton.textContent = '分析趋势';
            });
    });
}

// AI健康助手功能
function initAIAssistant() {
    const chatMessages = document.getElementById('chat-messages');
    const userMessage = document.getElementById('user-message');
    const sendButton = document.getElementById('send-message');
    
    if (!chatMessages || !userMessage || !sendButton) return;
    
    // 添加欢迎消息
    addMessage('您好！我是您的AI健康助手。请问有什么饮食健康问题需要咨询吗？', 'assistant');
    
    // 发送消息
    function sendMessage() {
        const message = userMessage.value.trim();
        if (!message) return;
        
        // 显示用户消息
        addMessage(message, 'user');
        userMessage.value = '';
        
        // 发送到服务器
        fetch('/ai_assistant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: message }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                addMessage(data.answer, 'assistant');
            } else {
                addMessage('抱歉，我现在无法回答您的问题。请稍后再试。', 'assistant');
            }
        })
        .catch(error => {
            console.error('错误:', error);
            addMessage('抱歉，发生了错误。请稍后再试。', 'assistant');
        });
    }
    
    // 添加消息到聊天界面
    function addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}-message`;
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // 事件监听
    sendButton.addEventListener('click', sendMessage);
    userMessage.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// 初始化每周计划功能
function initWeeklyPlan() {
    // Implementation of initWeeklyPlan function
}

// 初始化生成推荐功能
function initGenerateRecommendation() {
    const generateForm = document.querySelector('form[action*="generate_recommendation"]');
    
    if (generateForm) {
        generateForm.addEventListener('submit', function() {
            const submitButton = this.querySelector('button[type="submit"]');
            
            if (submitButton) {
                // 禁用按钮并显示加载状态
                submitButton.disabled = true;
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> 正在生成推荐，请稍候...';
                
                // 添加加载提示
                const formContainer = this.closest('.card-body');
                if (formContainer) {
                    const loadingAlert = document.createElement('div');
                    loadingAlert.className = 'alert alert-info mt-3';
                    loadingAlert.innerHTML = `
                        <p><strong>正在生成您的专属饮食计划...</strong></p>
                        <p>系统正在分析您的个人信息和课表安排，这可能需要几十秒的时间。请耐心等待。</p>
                    `;
                    formContainer.appendChild(loadingAlert);
                }
            }
        });
    }
} 