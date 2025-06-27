import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QLineEdit, QScrollArea, 
                            QSizePolicy, QMessageBox, QDialog, QFrame, QStackedWidget)
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QCursor, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint

from clothes_edited import InteractiveFashionAssistant, SessionState

from ui_with_image import ImageService

from z_main import process_user_query

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.draggable = False
        self.offset = QPoint()
        self.initUI()

    def initUI(self):
        # 设置窗口无边框并置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setStyleSheet("background-color: #FFFFFF; border-radius: 10px;")
        self.setFixedSize(450, 550)  # 稍微放大整个对话框
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部区域 - 包含Logo和关闭按钮
        top_frame = QFrame(self)
        top_frame.setStyleSheet("background-color: #07C160; border-radius: 10px 10px 0 0;")
        top_frame.setFixedHeight(100)  # 增加顶部区域高度
        
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(15, 15, 15, 15)
        
        # Logo - 放大并居中
        logo_label = QLabel(self)
        logo_pixmap = QPixmap("logo.png").scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap)
        else:
            logo_label.setText("PKU")
            logo_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        
        # 关闭按钮
        close_btn = QPushButton("×", self)
        close_btn.setStyleSheet("""
            background-color: transparent;
            color: white;
            font-size: 28px;
            font-weight: bold;
            border: none;
            padding: 0;
        """)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.clicked.connect(self.close)
        
        top_layout.addWidget(logo_label, 1)  # 占1份空间
        top_layout.addWidget(close_btn, 0, Qt.AlignTop | Qt.AlignRight)  # 靠右对齐
        
        # 底部登录区域
        login_frame = QFrame(self)
        login_frame.setStyleSheet("background-color: #FFFFFF; border-radius: 0 0 10px 10px;")
        
        login_layout = QVBoxLayout(login_frame)
        login_layout.setContentsMargins(30, 30, 30, 30)
        login_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("PKU Survivor", self)
        title_label.setStyleSheet("color: #07C160; font-size: 28px; font-weight: bold; text-align: center;")
        title_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(title_label)
        
        # 选项卡
        tabs_layout = QHBoxLayout()
        
        self.login_tab = QPushButton("登录", self)
        self.login_tab.setStyleSheet("""
            background-color: #07C160; 
            color: white; 
            font-size: 18px; 
            font-weight: bold;
            border-radius: 5px;
            padding: 12px;
            width: 50%;
        """)
        self.login_tab.setCursor(QCursor(Qt.PointingHandCursor))
        self.login_tab.clicked.connect(lambda: self.switch_tab("login"))
        
        self.register_tab = QPushButton("注册", self)
        self.register_tab.setStyleSheet("""
            background-color: #FFFFFF; 
            color: #07C160; 
            font-size: 18px; 
            font-weight: bold;
            border: 1px solid #07C160;
            border-radius: 5px;
            padding: 12px;
            width: 50%;
        """)
        self.register_tab.setCursor(QCursor(Qt.PointingHandCursor))
        self.register_tab.clicked.connect(lambda: self.switch_tab("register"))
        
        tabs_layout.addWidget(self.login_tab)
        tabs_layout.addWidget(self.register_tab)
        
        # 登录表单
        self.login_form = QWidget(self)
        login_form_layout = QVBoxLayout(self.login_form)
        login_form_layout.setSpacing(15)
        
        self.login_username = QLineEdit(self)
        self.login_username.setPlaceholderText("用户名")
        self.login_username.setStyleSheet("""
            border: 1px solid #E5E5E5;
            border-radius: 5px;
            padding: 12px;
            font-size: 16px;
        """)
        
        self.login_password = QLineEdit(self)
        self.login_password.setPlaceholderText("密码")
        self.login_password.setEchoMode(QLineEdit.Password)
        self.login_password.setStyleSheet("""
            border: 1px solid #E5E5E5;
            border-radius: 5px;
            padding: 12px;
            font-size: 16px;
        """)
        
        self.login_button = QPushButton("登录", self)
        self.login_button.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-size: 18px;
            font-weight: bold;
            border-radius: 5px;
            padding: 14px;
        """)
        self.login_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.login_button.clicked.connect(self.handle_login)
        
        login_form_layout.addWidget(self.login_username)
        login_form_layout.addWidget(self.login_password)
        login_form_layout.addWidget(self.login_button)
        
        # 注册表单
        self.register_form = QWidget(self)
        self.register_form.hide()
        register_form_layout = QVBoxLayout(self.register_form)
        register_form_layout.setSpacing(15)
        
        self.register_username = QLineEdit(self)
        self.register_username.setPlaceholderText("用户名")
        self.register_username.setStyleSheet("""
            border: 1px solid #E5E5E5;
            border-radius: 5px;
            padding: 12px;
            font-size: 16px;
        """)
        
        self.register_password = QLineEdit(self)
        self.register_password.setPlaceholderText("密码")
        self.register_password.setEchoMode(QLineEdit.Password)
        self.register_password.setStyleSheet("""
            border: 1px solid #E5E5E5;
            border-radius: 5px;
            padding: 12px;
            font-size: 16px;
        """)
        
        self.register_confirm = QLineEdit(self)
        self.register_confirm.setPlaceholderText("确认密码")
        self.register_confirm.setEchoMode(QLineEdit.Password)
        self.register_confirm.setStyleSheet("""
            border: 1px solid #E5E5E5;
            border-radius: 5px;
            padding: 12px;
            font-size: 16px;
        """)
        
        self.register_button = QPushButton("注册", self)
        self.register_button.setStyleSheet("""
            background-color: #FFFFFF;
            color: #07C160;
            font-size: 18px;
            font-weight: bold;
            border: 2px solid #07C160;
            border-radius: 5px;
            padding: 14px;
        """)
        self.register_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.register_button.clicked.connect(self.handle_register)
        
        register_form_layout.addWidget(self.register_username)
        register_form_layout.addWidget(self.register_password)
        register_form_layout.addWidget(self.register_confirm)
        register_form_layout.addWidget(self.register_button)
        
        # 添加到主布局
        login_layout.addLayout(tabs_layout)
        login_layout.addWidget(self.login_form)
        login_layout.addWidget(self.register_form)
        
        # 整体布局
        main_layout.addWidget(top_frame)
        main_layout.addWidget(login_frame)
        
        # 初始化当前表单
        self.current_form = "login"

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.draggable = True
            self.offset = event.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.draggable and event.buttons() & Qt.LeftButton:
            self.move(self.pos() + event.pos() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.draggable = False
            event.accept()
    
    def switch_tab(self, tab_type):
        if tab_type == "login":
            self.current_form = "login"
            self.login_tab.setStyleSheet("""
                background-color: #07C160; 
                color: white; 
                font-size: 18px; 
                font-weight: bold;
                border-radius: 5px;
                padding: 12px;
                width: 50%;
            """)
            self.register_tab.setStyleSheet("""
                background-color: #FFFFFF; 
                color: #07C160; 
                font-size: 18px; 
                font-weight: bold;
                border: 1px solid #07C160;
                border-radius: 5px;
                padding: 12px;
                width: 50%;
            """)
            self.login_form.show()
            self.register_form.hide()
        else:
            self.current_form = "register"
            self.login_tab.setStyleSheet("""
                background-color: #FFFFFF; 
                color: #07C160; 
                font-size: 18px; 
                font-weight: bold;
                border: 1px solid #07C160;
                border-radius: 5px;
                padding: 12px;
                width: 50%;
            """)
            self.register_tab.setStyleSheet("""
                background-color: #07C160; 
                color: white; 
                font-size: 18px; 
                font-weight: bold;
                border-radius: 5px;
                padding: 12px;
                width: 50%;
            """)
            self.login_form.hide()
            self.register_form.show()
    
    def handle_login(self):
        username = self.login_username.text().strip()
        password = self.login_password.text()
        
        if not username:
            self.show_error("用户名不能为空")
            return
            
        # 这里应该调用clothes_edited中的验证函数
        # 示例: if self.parent.assistant.verify_user(username, password):
        # 为简化演示，假设登录成功
        self.parent.user_id = username
        self.parent.load_user_history(username)  # 加载用户历史
        self.accept()  # 关闭对话框并返回Accepted状态
    
    def handle_register(self):
        username = self.register_username.text().strip()
        password = self.register_password.text()
        confirm = self.register_confirm.text()
        
        if not username or not password:
            self.show_error("用户名和密码不能为空")
            return
            
        if password != confirm:
            self.show_error("两次输入的密码不一致")
            return
            
        # 这里应该调用clothes_edited中的注册函数
        # 示例: self.parent.assistant.register_user(username, password)
        QMessageBox.information(self, "成功", f"用户 {username} 注册成功!")
        self.switch_tab("login")
    
    def show_error(self, message):
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Warning)
        error_dialog.setText(message)
        error_dialog.setWindowTitle("错误")
        error_dialog.setStandardButtons(QMessageBox.Ok)
        error_dialog.setStyleSheet("""
            QMessageBox {
                background-color: white;
                border-radius: 10px;
            }
            QLabel {
                font-size: 16px;
                padding: 15px;
            }
            QPushButton {
                background-color: #07C160;
                color: white;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 16px;
            }
        """)
        error_dialog.exec_()

class WelcomeTips(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用提示")
        self.setGeometry(400, 300, 600, 400)
        self.setStyleSheet("background-color: white; border-radius: 10px;")
        
        layout = QVBoxLayout()
        
        tips_text = """
        <h3 style="color: #07C160; font-size: 22px;">小北穿搭助手使用指南</h3>
        <p style="font-size: 16px; margin-top: 10px;"><b>1. 基本功能</b></p>
        <ul style="font-size: 16px; margin-left: 20px;">
            <li>获取穿搭建议</li>
            <li>调整/优化需求，修改推荐方案(如"优化成更正式的风格")</li>
            <li>命令行输入"help"查看一些使用贴士</li>
            <li>命令行输入"quit"结束对话</li>
        </ul>
        
        <p style="font-size: 16px; margin-top: 10px;"><b>2. 高级功能</b></p>
        <ul style="font-size: 16px; margin-left: 20px;">
            <li>自动保存方案和对话历史</li>
            <li>能调用强大的数据库</li>
            <li>拥有科学严谨完善的匹配逻辑</li>
        </ul>
        
        <p style="font-size: 16px; margin-top: 10px;"><b>3. 交互技巧</b></p>
        <ul style="font-size: 16px; margin-left: 20px;">
            <li>使用"再推荐一些"/"多推荐一点"获取更多选择</li>
            <li>对推荐不满意时，明确指出问题(如"太花哨了/不适合本蜀黍（x")</li>
            <li>指定场景(如"面试穿搭/出席顶会（doge")获取针对性建议</li>
        </ul>
        """
        
        tips_label = QLabel(tips_text)
        tips_label.setWordWrap(True)
        tips_label.setTextFormat(Qt.RichText)
        tips_label.setStyleSheet("padding: 25px;")
        
        ok_btn = QPushButton("我知道了")
        ok_btn.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-size: 18px;
            font-weight: bold;
            border-radius: 5px;
            padding: 12px 25px;
            margin: 20px;
        """)
        ok_btn.setFixedWidth(180)
        ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
        ok_btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        
        layout.addWidget(tips_label)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

class ChatBubble(QWidget):
    def __init__(self, sender, message, parent=None):
        super().__init__(parent)
        self.initUI(sender, message)
    
    def initUI(self, sender, message):
        layout = QHBoxLayout(self)
        
        # label = QLabel(message)
        # label.setWordWrap(True)
        # self.message_label = label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        # self.message_label = QLabel(message)
        
        self.message_label = QLabel(message)  # 定义 self.message_label
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        
        # 计算每行显示的最佳字数
        font = self.message_label.font()
        font_metrics = QFontMetrics(font)
        avg_char_width = font_metrics.averageCharWidth()
        
        # 设置气泡最大宽度为10-15个汉字宽度
        max_chars_per_line = 45  # 最多15个汉字
        min_chars_per_line = 20 # 最少10个汉字
        
        # 计算最大宽度范围
        min_width = min_chars_per_line * avg_char_width
        max_width = max_chars_per_line * avg_char_width
        
        # 设置气泡样式
        if sender == "user":
            bg_color = "#DCF8C6"
            alignment = Qt.AlignRight
        else:
            bg_color = "#FFFFFF"
            alignment = Qt.AlignLeft
            
        self.message_label.setStyleSheet(f"""
            border-radius: 12px;
            padding: 14px;
            font-size: 16px;
            background-color: {bg_color};
            max-width: {max_width}px;

        """)
        
        layout.setAlignment(alignment)
        layout.addWidget(self.message_label)
        self.setLayout(layout)
    # def __init__(self, sender, message, parent=None):
    #     super().__init__(parent)
    #     self.initUI(sender, message)
    
    # def initUI(self, sender, message):
    #     main_layout = QHBoxLayout(self)
        
    #     # 创建头像
    #     avatar_label = QLabel(self)
    #     avatar_size = 40  # 头像大小
        
    #     if sender == "user":
    #         avatar_pixmap = QPixmap("user_avatar.png").scaled(avatar_size, avatar_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    #         if avatar_pixmap.isNull():
    #             avatar_label.setText("👤")  # 如果找不到图片，使用emoji
    #             avatar_label.setStyleSheet("font-size: 24px; padding: 5px;")
    #         else:
    #             avatar_label.setPixmap(avatar_pixmap)
    #         main_layout.setAlignment(Qt.AlignRight)
    #     else:
    #         avatar_pixmap = QPixmap("agent_avatar.png").scaled(avatar_size, avatar_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    #         if avatar_pixmap.isNull():
    #             avatar_label.setText("🤖")  # 如果找不到图片，使用emoji
    #             avatar_label.setStyleSheet("font-size: 24px; padding: 5px;")
    #         else:
    #             avatar_label.setPixmap(avatar_pixmap)
    #         main_layout.setAlignment(Qt.AlignLeft)
        
    #     # 创建消息气泡
    #     bubble_layout = QHBoxLayout()
        
    #     self.message_label = QLabel(message)
    #     self.message_label.setWordWrap(True)
    #     self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
    #     # 设置气泡样式
    #     if sender == "user":
    #         bg_color = "#DCF8C6"
    #         alignment = Qt.AlignRight
    #         bubble_layout.addStretch()
    #     else:
    #         bg_color = "#FFFFFF"
    #         alignment = Qt.AlignLeft
    #         bubble_layout.addWidget(avatar_label)
        
    #     # 增加气泡最大宽度，从85%增加到90%
    #     self.message_label.setStyleSheet(f"""
    #         border-radius: 12px;
    #         padding: 14px;
    #         font-size: 16px;
    #         background-color: {bg_color};
    #         max-width: 90%;
    #     """)
        
    #     bubble_layout.addWidget(self.message_label)
        
    #     if sender == "user":
    #         bubble_layout.addWidget(avatar_label)
    #     else:
    #         bubble_layout.addStretch()
        
    #     main_layout.addLayout(bubble_layout)
    #     self.setLayout(main_layout)
    
    # def get_message_label(self):
    #     return self.message_label
    
    
    
class AgentSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        
        
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(40)
        
        title_label = QLabel("选择你的智能助手")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #07C160; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # 三个Agent按钮
        agents_layout = QVBoxLayout()
        agents_layout.setAlignment(Qt.AlignCenter)
        agents_layout.setSpacing(25)
        
        # 小北穿搭
        fashion_agent_btn = QPushButton("小北穿搭")
        fashion_agent_btn.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-size: 20px;
            font-weight: bold;
            border-radius: 12px;
            padding: 18px 35px;
            width: 350px;
        """)
        fashion_agent_btn.setCursor(QCursor(Qt.PointingHandCursor))
        fashion_agent_btn.clicked.connect(lambda: self.parent.select_agent(1))
        
        # 小北运动
        sports_agent_btn = QPushButton("小北运动")
        sports_agent_btn.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-size: 20px;
            font-weight: bold;
            border-radius: 12px;
            padding: 18px 35px;
            width: 350px;
        """)
        sports_agent_btn.setCursor(QCursor(Qt.PointingHandCursor))
        sports_agent_btn.clicked.connect(lambda: self.parent.select_agent(2))
        
        # 小北饮食
        diet_agent_btn = QPushButton("小北饮食")
        diet_agent_btn.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-size: 20px;
            font-weight: bold;
            border-radius: 12px;
            padding: 18px 35px;
            width: 350px;
        """)
        diet_agent_btn.setCursor(QCursor(Qt.PointingHandCursor))
        diet_agent_btn.clicked.connect(lambda: self.parent.select_agent(3))
        
        agents_layout.addWidget(fashion_agent_btn)
        agents_layout.addWidget(sports_agent_btn)
        agents_layout.addWidget(diet_agent_btn)
        
        back_btn = QPushButton("返回")
        back_btn.setStyleSheet("""
            background-color: white;
            color: #07C160;
            font-size: 18px;
            font-weight: bold;
            border: 2px solid #07C160;
            border-radius: 10px;
            padding: 12px 25px;
            width: 180px;
        """)
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.clicked.connect(self.parent.show_welcome)
        
        layout.addWidget(title_label)
        layout.addLayout(agents_layout)
        layout.addWidget(back_btn, alignment=Qt.AlignCenter)
        layout.addStretch()
        
        self.setLayout(layout)

import sqlite3

class AIAgentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.assistant = InteractiveFashionAssistant()
        self.user_id = None
        self.current_response = ""
        self.current_index = 0
        self.timer = None
        self.current_agent = None
        self.initUI()
        
        # 连接到SQLite数据库
        self.conn = sqlite3.connect('clothing_db.sqlite')
        self.cursor = self.conn.cursor()
    
    def initUI(self):
        
        # 主窗口设置
        self.setWindowTitle('Welcome to PKU Survivor')  # 保持原应用名称
        self.setGeometry(100, 100, 1024, 780)
        font = QFont("Arial", 10)
        self.setFont(font)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建欢迎界面容器
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignTop)  # 内容靠上排列
        
        # 欢迎界面标题
        title_frame = QFrame(self)
        title_frame.setStyleSheet("background-color: #07C160;")
        title_frame.setFixedHeight(200)
        
        title_layout = QVBoxLayout(title_frame)
        title_layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("PKU Survivor")
        title_label.setStyleSheet("color: white; font-size: 48px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("智能助手平台")
        subtitle_label.setStyleSheet("color: white; font-size: 24px; margin-top: 10px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        # 欢迎界面内容
        content_frame = QFrame(self)
        content_frame.setStyleSheet("background-color: white;")
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(40)
        
        
        # # 主窗口设置
        # self.setWindowTitle('PKU Survivor')
        # self.setGeometry(100, 100, 1024, 780)
        # font = QFont("Arial", 12)
        # self.setFont(font)
        
        # # 主布局
        # main_layout = QVBoxLayout(self)
        # main_layout.setContentsMargins(0, 0, 0, 0)
        
        # # 创建欢迎界面容器
        # self.welcome_widget = QWidget()
        # welcome_layout = QVBoxLayout(self.welcome_widget)
        # welcome_layout.setAlignment(Qt.AlignCenter)  # 整体内容居中
        
        # # 欢迎界面Logo - 放大并居中
        logo_frame = QFrame(self)
        logo_frame.setStyleSheet("background-color: white;")
        
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setAlignment(Qt.AlignCenter)
        
        logo_label = QLabel(self)
        logo_pixmap = QPixmap("logo.png").scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap)
        # else:
        #     logo_label.setText("PKU Survivor")
        #     logo_label.setStyleSheet("color: #07C160; font-size: 48px; font-weight: bold;")
        # logo_label.setAlignment(Qt.AlignCenter)
        
        logo_layout.addWidget(logo_label)
        
        # # 欢迎界面标题
        # title_frame = QFrame(self)
        # title_frame.setStyleSheet("background-color: #07C160;")
        
        # title_layout = QVBoxLayout(title_frame)
        # title_layout.setAlignment(Qt.AlignCenter)
        
        # title_label = QLabel("Welcome to PKU survivor!")
        # title_label.setStyleSheet("color: white; font-size: 42px; font-weight: bold;")
        # title_label.setAlignment(Qt.AlignCenter)
        
        # subtitle_label = QLabel("专属PKUers的生活助手，从此打造个性化生活方式")
        # subtitle_label.setStyleSheet("color: #333333; font-size: 24px; margin-top: 15px;")
        # subtitle_label.setAlignment(Qt.AlignCenter)
        
        # title_layout.addWidget(title_label)
        # title_layout.addWidget(subtitle_label)
        
        # # 欢迎界面内容
        # content_frame = QFrame(self)
        # content_frame.setStyleSheet("background-color: transparent;")
        
        # content_layout = QVBoxLayout(content_frame)
        # content_layout.setAlignment(Qt.AlignCenter)
        # content_layout.setSpacing(50)
        
        # 功能介绍
        features_frame = QFrame(self)
        features_frame.setStyleSheet("background-color: transparent; padding: 20px;")
        
        features_layout = QVBoxLayout(features_frame)
        
        feature1 = QLabel("✨ 智能穿搭推荐")
        feature1.setStyleSheet("font-size: 22px; margin-bottom: 15px;")
        
        feature2 = QLabel("✨ 运动健身指导")
        feature2.setStyleSheet("font-size: 22px; margin-bottom: 15px;")
        
        feature3 = QLabel("✨ 健康饮食建议")
        feature3.setStyleSheet("font-size: 22px;")
        
        features_layout.addWidget(feature1)
        features_layout.addWidget(feature2)
        features_layout.addWidget(feature3)
        
        # 开始按钮
        start_btn = QPushButton("开始使用")
        start_btn.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-size: 22px;
            font-weight: bold;
            border-radius: 35px;
            padding: 18px 40px;
        """)
        start_btn.setFixedWidth(240)
        start_btn.setCursor(QCursor(Qt.PointingHandCursor))
        start_btn.clicked.connect(self.show_agent_selection)
        
        content_layout.addStretch()
        content_layout.addWidget(features_frame)
        content_layout.addWidget(start_btn, alignment=Qt.AlignCenter)
        content_layout.addStretch()
        
        welcome_layout.addStretch()
        # welcome_layout.addWidget(logo_frame)
        welcome_layout.addWidget(title_frame)
        welcome_layout.addWidget(content_frame)
        welcome_layout.addStretch()
        welcome_layout.addWidget(logo_frame)
        
        # 创建Agent选择界面
        self.agent_selection_widget = AgentSelectionWidget(self)
        
        # 创建聊天界面容器
        self.chat_widget = QWidget()
        chat_layout = QVBoxLayout(self.chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # 聊天顶部栏
        top_bar = QFrame(self)
        top_bar.setStyleSheet("background-color: #07C160; color: white; padding: 10px;")
        top_bar.setFixedHeight(105)
        
        top_bar_layout = QHBoxLayout(top_bar)
        
        back_btn = QPushButton("")
        back_btn.setIcon(QIcon.fromTheme("go-previous"))
        back_btn.setStyleSheet("background-color: transparent; color: white;")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.clicked.connect(self.show_agent_selection)
        
        self.agent_title_label = QLabel("小北穿搭助手")
        self.agent_title_label.setStyleSheet("font-size: 25px; font-weight: bold; ")
        self.agent_title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        
        top_bar_layout.addWidget(back_btn)
        top_bar_layout.addWidget(self.agent_title_label)
        top_bar_layout.addStretch()
        
        # 聊天内容区域
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet("background-color: #F5F5F5;")
        
        self.chat_container = QWidget()
        self.chat_layout_inner = QVBoxLayout(self.chat_container)
        self.chat_layout_inner.setAlignment(Qt.AlignTop)
        self.chat_layout_inner.setSpacing(20)
        self.chat_layout_inner.setContentsMargins(25, 25, 25, 25)
        
        self.chat_scroll.setWidget(self.chat_container)
        
        # 输入区域
        input_frame = QFrame(self)
        input_frame.setStyleSheet("background-color: white; border-top: 1px solid #E5E5E5; padding: 15px;")
        
        input_layout = QHBoxLayout(input_frame)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setStyleSheet("""
            border: 1px solid #E5E5E5;
            border-radius: 25px;
            padding: 12px 20px;
            font-size: 16px;
            height: 45px;
        """)
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setStyleSheet("""
            background-color: #07C160;
            color: white;
            font-weight: bold;
            border-radius: 25px;
            padding: 12px 25px;
            margin-left: 15px;
            height: 45px;
            font-size: 16px;
        """)
        self.send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(top_bar)
        chat_layout.addWidget(self.chat_scroll)
        chat_layout.addWidget(input_frame)
        
        # 添加布局到主窗口
        main_layout.addWidget(self.welcome_widget)
        main_layout.addWidget(self.agent_selection_widget)
        main_layout.addWidget(self.chat_widget)
        
        # 初始显示欢迎界面
        self.welcome_widget.show()
        self.agent_selection_widget.hide()
        self.chat_widget.hide()
        
        self.setLayout(main_layout)
    
    def show_welcome(self):
        self.chat_widget.hide()
        self.agent_selection_widget.hide()
        self.welcome_widget.show()
    
    def show_agent_selection(self):
        self.welcome_widget.hide()
        self.chat_widget.hide()
        self.agent_selection_widget.show()
    
    def select_agent(self, agent_id):
        self.current_agent = agent_id
        
        # 只有选择"小北穿搭"时才需要登录
        if agent_id == 1:
            login_dialog = LoginDialog(self)
            if login_dialog.exec_():  # 等待对话框关闭
                self.show_welcome_tips()
                self.start_chat()
        else:
            # 其他Agent不需要登录，直接进入聊天
            self.start_chat()
    
    def show_welcome_tips(self):
        tips = WelcomeTips(self)
        tips.exec_()
    
    def start_chat(self):
        # 设置顶部栏标题
        # agent_names = ["", "小北穿搭助手", "小北运动助手", "小北饮食助手"]
        # self.agent_title_label.setText(agent_names[self.current_agent])
        
        # self.agent_selection_widget.hide()
        # self.chat_widget.show()



        # # 根据选择的Agent显示不同的欢迎语
        # if self.current_agent == 1:
        #     welcome_messages = [
        #         "🎉 这里是最懂你的智能穿搭助手小北！我是由传奇debug王yjm开发的颠覆级穿搭推荐agent。","和小北打个招呼吧~"
        #     ]
        # elif self.current_agent == 2:
        #     welcome_messages = [
        #         "🎉 欢迎使用小北运动助手！今天想进行什么类型的运动？"

        #     ]
        # elif self.current_agent == 3:
        #     welcome_messages = [
        #         "🎉 欢迎使用小北饮食助手！今天想吃点什么？"

        #     ]

        # for message in welcome_messages:
        #     self.stream_output(message)
        
        
        
        
        
        
        
        
        
        
        # 真的拼尽全力无法战胜这个流式输出的显示，只能打残版欢迎语了/(ㄒoㄒ)/~~
        # 第一行被删掉（
        
        
        agent_welcome_messages = {
        1: [
            "和小北打个招呼吧~"
        ],
        2: [
            "🎉 欢迎使用小北运动助手！今天想进行什么类型的运动？",
            "输入你的运动目标(如: 减肥、增肌)获取运动建议"
        ],
        3: [
            "🎉 欢迎使用小北饮食助手！今天想吃点什么？",
            "输入你的饮食需求(如: 减脂餐、健康早餐)获取饮食建议"
        ]
        }
        self.welcome_messages = agent_welcome_messages.get(self.current_agent, [])
        self.current_welcome_index = 0
        # 启动第一条欢迎语的流式输出
        self.start_next_welcome()

    def start_next_welcome(self):
        if self.current_welcome_index < len(self.welcome_messages):
            current_msg = self.welcome_messages[self.current_welcome_index]
            self.ww_stream_output(current_msg)
        else:
            # 所有欢迎语输出完毕，可做其他初始化逻辑
            pass
        
        
        
        
    def ww_stream_output(self, response):
        self.current_response = response
        self.current_index = 0
        # 停止之前的定时器（防止冲突）
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()
        # 新建定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.ww_update_output)
        self.timer.start(50)  # 每50ms输出一个字符

    # def ww_update_output(self):
    #     if self.current_index < len(self.current_response):
    #         # 每一个新消息的第一个字符，创建新气泡
    #         if self.current_index == 0:
    #             self.current_bubble = ChatBubble("assistant", self.current_response[0])
    #             self.chat_layout_inner.addWidget(self.current_bubble)
    #         else:
    #             # 拼接字符到当前气泡
    #             label = self.current_bubble.layout().itemAt(0).widget()
    #             label.setText(label.text() + self.current_response[self.current_index])
            
    #         self.current_index += 1
            
            
    #         QApplication.processEvents()
    #         # 关键：强制气泡布局更新并计算高度
    #         self.current_bubble.layout().update()
    #         self.current_bubble.adjustSize()
            
    #         # 滚动到底部
    #         self.chat_scroll.verticalScrollBar().setValue(
    #             self.chat_scroll.verticalScrollBar().maximum()
    #         )
    #     else:
    #         # 当前消息流式输出完毕，停止定时器
    #         self.timer.stop()
    #         # 准备输出下一条欢迎语
    #         self.current_welcome_index += 1
    #         self.start_next_welcome()  # 递归调用，输出下一条
    
    # def ww_update_output(self):
    #     if self.current_index < len(self.current_response):
    #         # 每一个新消息的第一个字符，创建新气泡
    #         if self.current_index == 0:
    #             self.current_bubble = ChatBubble("assistant", self.current_response[0])
    #             self.chat_layout_inner.addWidget(self.current_bubble)
    #         else:
    #             # 拼接字符到当前气泡
    #             current_text = self.current_bubble.message_label.text()
    #             self.current_bubble.message_label.setText(current_text + self.current_response[self.current_index])
    #         self.current_index += 1
    #     else:
    #         # 当前欢迎语输出完毕，停止定时器
    #         self.timer.stop()
    #         # 滚动到聊天区域底部
    #         self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
    #         # 处理下一条欢迎语
    #         self.current_welcome_index += 1
    #         self.start_next_welcome()
       
       
    def ww_update_output(self):
        if self.current_index < len(self.current_response):
            # 每一个新消息的第一个字符，创建新气泡
            if self.current_index == 0:
                self.current_bubble = ChatBubble("assistant", self.current_response[0])
                self.chat_layout_inner.addWidget(self.current_bubble)
            else:
                # 拼接字符到当前气泡
                current_text = self.current_bubble.message_label.text()
                self.current_bubble.message_label.setText(current_text + self.current_response[self.current_index])
            self.current_index += 1
            # 更新布局
            self.chat_widget.layout().update()
            # 滚动到最新消息
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
        else:
            # 当前欢迎语输出完毕，停止定时器
            self.timer.stop()
            
                    
            
            
            # 滚动到聊天区域底部
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
            # QTimer.singleShot(100)
            
            # 处理下一条欢迎语
            self.current_welcome_index += 1
            self.start_next_welcome() 
            
            

        # 设置顶部栏标题
        agent_names = ["", "小北穿搭助手", "小北运动助手", "小北饮食助手"]
        self.agent_title_label.setText(agent_names[self.current_agent])

        self.agent_selection_widget.hide()
        self.chat_widget.show()


    #     agent_welcome_messages = {
    #         1: [
    #             "🎉 这里是最懂你的智能穿搭助手小北！",
    #             "我是由传奇debug王yjm开发的颠覆级穿搭推荐agent。",
    #             "和小北打个招呼吧~"
    #         ],
    #         2: [
    #             "🎉 欢迎使用小北运动助手！今天想进行什么类型的运动？",
    #             "输入你的运动目标(如: 减肥、增肌)获取运动建议"
    #         ],
    #         3: [
    #             "🎉 欢迎使用小北饮食助手！今天想吃点什么？",
    #             "输入你的饮食需求(如: 减脂餐、健康早餐)获取饮食建议"
    #         ]
    #     }
        
    #     # 获取当前Agent的欢迎消息
    #     self.welcome_messages = agent_welcome_messages.get(self.current_agent, [])
    #     self.current_welcome_index = 0
        
    #     # 开始显示欢迎消息
    #     if self.welcome_messages:
    #         self.w_stream_output(self.welcome_messages[self.current_welcome_index])

    # def w_stream_output(self, response):
    #     """流式输出回复"""
    #     self.current_response = response
    #     self.current_index = 0

    #     # 停止之前的计时器
    #     if hasattr(self, 'timer') and self.timer:
    #         self.timer.stop()

    #     # 创建新计时器
    #     self.timer = QTimer(self)
    #     self.timer.timeout.connect(self.w_update_output)
    #     self.timer.start(50)  # 每50ms输出一个字符

    # # def w_update_output(self):
    # #     """更新流式输出"""
    # #     if self.current_index < len(self.current_response):
    # #         # 如果是第一条字符，创建新气泡
    # #         if self.current_index == 0:
    # #             self.current_bubble = ChatBubble("assistant", self.current_response[0])
    # #             self.chat_layout_inner.addWidget(self.current_bubble)
    # #         # 否则追加到现有气泡
    # #         else:
    # #             label = self.current_bubble.layout().itemAt(0).widget()
    # #             label.setText(label.text() + self.current_response[self.current_index])

    # #         self.current_index += 1
    # #         # 滚动到底部
    # #         self.chat_scroll.verticalScrollBar().setValue(
    # #             self.chat_scroll.verticalScrollBar().maximum()
    # #         )
    # #     else:
    # #         # 当前消息显示完毕，停止计时器
    # #         self.timer.stop()
            
    # #         # 显示下一条欢迎消息
    # #         self.current_welcome_index += 1
    # #         if self.current_welcome_index < len(self.welcome_messages):
    # #             # 使用单次定时器延迟显示下一条消息，避免界面卡顿
    # #             QTimer.singleShot(300, lambda: self.w_stream_output(
    # #                 self.welcome_messages[self.current_welcome_index]))
    
    
    
    # def w_update_output(self):
    #     """更新流式输出"""
    #     if self.current_index < len(self.current_response):
    #         # 如果是第一条字符，创建新气泡
    #         if self.current_index == 0:
    #             self.current_bubble = ChatBubble("assistant", self.current_response[0])
    #             self.chat_layout_inner.addWidget(self.current_bubble)
    #         # 否则追加到现有气泡
    #         else:
    #             label = self.current_bubble.layout().itemAt(0).widget()
    #             label.setText(label.text() + self.current_response[self.current_index])

    #         self.current_index += 1
    #         # 滚动到底部
    #         self.chat_scroll.verticalScrollBar().setValue(
    #             self.chat_scroll.verticalScrollBar().maximum()
    #         )
    #     else:
    #         # 当前消息显示完毕，停止计时器
    #         self.timer.stop()
            
    #         # 显示下一条欢迎消息
    #         self.current_welcome_index += 1
    #         if self.current_welcome_index < len(self.welcome_messages):
    #             # 计算当前消息的总显示时间，根据消息长度设置合理延迟
    #             # 假设每个字符需要50ms显示，再增加200ms缓冲
    #             message_length = len(self.current_response)
    #             delay_time = message_length * 50 + 200
                
    #             # 使用单次定时器延迟显示下一条消息，确保界面渲染完成
    #             QTimer.singleShot(delay_time, lambda: self.w_stream_output(
    #                 self.welcome_messages[self.current_welcome_index]))
    #         else:
    #             # 所有欢迎消息显示完毕，重置索引
    #             self.current_welcome_index = 0
    
    def load_user_history(self, username):
        """加载用户历史记录"""
        # 实际实现应调用clothes_edited中的相关函数
        pass
    
    def send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return
            
        self.display_message("user", message)
        self.message_input.clear()


        
        # 处理用户输入
        self.process_user_input(message)
    
    def process_user_input(self, message):
        """处理用户输入并获取回复"""
        if self.current_agent == 1 and not self.user_id:
            self.display_message("assistant", "请先登录再进行对话")
            return
            
        # 调用clothes_edited中的处理逻辑
        # 这里根据不同的Agent调用不同的处理函数
        if self.current_agent == 1:
            response = self.assistant.process_user_input(self.user_id, message)
            if("🎯 **院衫推荐**" in response):
                now_session = self.assistant.get_or_create_session(self.user_id)
                now_id  = self.assistant.prepare_image(now_session)
                print(now_id)
                self.show_college_shirt_image(now_id)
        else:
            # # 其他Agent的处理逻辑可以在这里添加
            # if self.current_agent == 2:
            # # need add
            #     process_user_query(message)
            
            
            # else:
                
            response = f"[{self.current_agent}] 功能开发中，暂不支持复杂交互"
            
        self.stream_output(response)
    
    
    def get_image_path(self, shirt_id):
        """从数据库获取图片路径"""
        conn = sqlite3.connect("clothing_db.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM clothing_items WHERE id=?", (shirt_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    
    def show_college_shirt_image(self, shirt_id):
        
        result = self.get_image_path(shirt_id)
        

        if result:
            print("有结果")
            image_filename = result[0]
            # 加载院衫图片
            pixmap = QPixmap(image_filename)
            if not pixmap.isNull():
                # 调整图片大小
                print("下面应输出图片")
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # 创建图片标签
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                # 添加到聊天布局
                self.chat_layout_inner.addWidget(image_label)
                # 滚动到最新消息
                self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
    
    def stream_output(self, response):
        """流式输出回复"""
        self.current_response = response
        self.current_index = 0
        
        if self.timer:
            self.timer.stop()
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_output)
        self.timer.start(50)  # 每50ms输出一个字符
    
    def update_output(self):
        """更新流式输出"""
        if self.current_index < len(self.current_response):
            # 如果是第一条字符，创建新气泡
            if self.current_index == 0:
                self.current_bubble = ChatBubble("assistant", self.current_response[0])
                self.chat_layout_inner.addWidget(self.current_bubble)
            # 否则追加到现有气泡
            else:
                label = self.current_bubble.layout().itemAt(0).widget()
                label.setText(label.text() + self.current_response[self.current_index])
            
            self.current_index += 1
            self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            )
        else:
            self.timer.stop()
    
    def display_message(self, sender, message):
        """显示消息气泡"""
        bubble = ChatBubble(sender, message)
        self.chat_layout_inner.addWidget(bubble)
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置全局样式
    app.setStyleSheet("""
        QWidget {
            font-family: "Arial", "Microsoft YaHei";
        }
        QScrollBar:vertical {
            width: 8px;
            background: rgba(0,0,0,5%);
            margin: 0;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: rgba(0,0,0,25%);
            min-height: 25px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
            margin: 0;
            border: none;
        }
    """)
    window = AIAgentApp()
    window.show()
    sys.exit(app.exec_())