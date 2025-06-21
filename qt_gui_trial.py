import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QTextEdit, QLineEdit
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import QSize

from clothes_edited import InteractiveFashionAssistant
        
from PyQt5.QtWidgets import QScrollArea, QFrame, QHBoxLayout
class AIAgentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.assistant = InteractiveFashionAssistant()
        self.user_id = "trial_user"  # 可替换为登录后动态生成
        self.initUI()

    def initUI(self):
        
        
        # 主布局
        self.main_layout = QVBoxLayout()
        
        self.setWindowTitle('PKU Survivor:an AI Agent for PKUers')
        self.setGeometry(100, 100, 1024, 780)
        font = QFont("Arial", 10)
        self.setFont(font)

        # Welcome Screen
        self.welcome_label = QLabel('Welcome to PKU Survivor', self)
        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.show_options)

        self.welcome_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #4A90E2; margin-bottom: 10px;")


        self.start_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; border-radius: 5px;")
        self.start_button.setFixedSize(QSize(150, 40))
        self.start_button.clicked.connect(self.show_options)
        
        # self.start_button.setAlignment(0x0004)  # Qt.AlignHCenter表示水平居中对齐
        
        # 添加固定空间以使按钮居中
        self.main_layout.addStretch()  # 添加弹性空间以推动按钮居中
        self.main_layout.addWidget(self.start_button)
        self.main_layout.addStretch()  # 再添加弹性空间

        # Options
        self.agent1_button = QPushButton('小北穿搭', self)
        self.agent2_button = QPushButton('小北运动', self)
        self.agent3_button = QPushButton('小北饮食', self)

        # 设置按钮样式
        for button in [self.agent1_button, self.agent2_button, self.agent3_button]:
            button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; border-radius: 5px; margin-top: 5px;")
            button.setFixedSize(QSize(150, 40))

        self.agent1_button.clicked.connect(lambda: self.start_chat(1))
        self.agent2_button.clicked.connect(lambda: self.start_chat(2))
        self.agent3_button.clicked.connect(lambda: self.start_chat(3))

        # Chat Frame


 
        
        

        self.chat_window = QTextEdit(self)
        self.chat_window.setReadOnly(True)
        self.chat_window.setStyleSheet("background-color: #F5F5F5; padding: 10px; border: 1px solid #C0C0C0;")



        
        
        
        self.user_input = QLineEdit(self)
        self.user_input.setStyleSheet("border: 1px solid #BDBDBD; border-radius: 5px; padding: 5px;")
        self.user_input.setPlaceholderText("在这里输入消息...")

        self.send_button = QPushButton('发送', self)
        self.send_button.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold; border-radius: 5px;")
        self.send_button.setFixedSize(QSize(150, 40))
        self.send_button.clicked.connect(self.send_message)

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.welcome_label)
        self.main_layout.addWidget(self.start_button)

        # Options
        self.options_layout = QVBoxLayout()
        self.options_layout.addWidget(self.agent1_button)
        self.options_layout.addWidget(self.agent2_button)
        self.options_layout.addWidget(self.agent3_button)

        # Chat Elements
        self.chat_layout = QVBoxLayout()
        self.chat_layout.addWidget(self.chat_window)
        self.chat_layout.addWidget(self.user_input)
        self.chat_layout.addWidget(self.send_button)
        
        
        # Chat Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setMinimumHeight(500)  # 确保有高度可以展示

        self.chat_container = QWidget()
        self.chat_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.chat_layout_inner = QVBoxLayout(self.chat_container)
        
        self.chat_layout_inner.setContentsMargins(20, 10, 20, 10)
        self.chat_layout_inner.setSpacing(10)
        self.chat_layout_inner.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.chat_container)
        
        
        
        
        self.chat_layout.insertWidget(0, self.scroll_area)
        self.chat_layout.removeWidget(self.chat_window)
        self.chat_window.deleteLater()

        self.main_layout.addLayout(self.options_layout)
        self.main_layout.addLayout(self.chat_layout)

        # Hide options and chat layouts initially
        self.hide_options_and_chat()

    def hide_options_and_chat(self):
        for i in range(self.options_layout.count()):
            widget = self.options_layout.itemAt(i).widget()
            if widget:
                widget.hide()

        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if widget:
                widget.hide()

    def show_options(self):
        self.welcome_label.hide()
        self.start_button.hide()
        for i in range(self.options_layout.count()):
            widget = self.options_layout.itemAt(i).widget()
            if widget:
                widget.show()

    def start_chat(self, agent_id):
        for i in range(self.options_layout.count()):
            widget = self.options_layout.itemAt(i).widget()
            if widget:
                widget.hide()
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if widget:
                widget.show()
        self.display_chat_message("assistant", f"PKUer,你好!欢迎和小北聊天！")
        
        
        #  后续应该加其他的判定条件
        self.display_chat_message("assistant", "🎉 欢迎使用智能穿搭助手小北！我是由传奇debug王（没有AI就不会写代码）的yjm开发的颠覆级穿搭推荐agent。")

    def send_message(self):

        user_input = self.user_input.text().strip()
        if user_input:
            self.display_chat_message("user", user_input)
            self.get_agent_response(user_input)
            self.user_input.clear()

    def get_agent_response(self, user_input):
        # response = f"小北的响应: {user_input}"
        response = self.assistant.process_user_input(self.user_id, user_input)
        self.display_chat_message("assistant", response)
        # self.chat_window.append("小北: " + response)
        
    def display_chat_message(self, sender, message):
        label = QLabel(message)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # 去掉原来固定最大宽度的设置，让布局自动控制
        # label.setMaximumWidth(int(self.scroll_area.width() * 0.6))  

        # 调整样式，可根据需求微调
        label.setStyleSheet("""
            border-radius: 10px;
            padding: 12px;
            font-size: 15px;
            background-color: %s;
        """ % ("#DCF8C6" if sender == "user" else "#FFFFFF"))

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setAlignment(Qt.AlignRight if sender == "user" else Qt.AlignLeft)
        # 添加拉伸因子，让 label 自动占满可用空间（但受限于内容长度）
        if sender == "user":
            layout.addStretch()
            layout.addWidget(label)
        else:
            layout.addWidget(label)
            layout.addStretch()

        container = QWidget()
        container.setLayout(layout)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.chat_layout_inner.addWidget(container)
        self.chat_layout_inner.addStretch()  
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
        
        
 
        
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AIAgentApp()
    window.show()
    sys.exit(app.exec_())