import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QLineEdit, QScrollArea, 
                            QSizePolicy, QMessageBox, QDialog, QFrame, QStackedWidget)
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QCursor, QFontMetrics
from PyQt5.QtCore import Qt, QTimer, QSize, QPoint

import sqlite3



class ImageService:
    def get_image_path(shirt_id):
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
            image_filename = result[0]
            # 加载院衫图片
            pixmap = QPixmap(image_filename)
            if not pixmap.isNull():
                # 调整图片大小
                pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # 创建图片标签
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                # 添加到聊天布局
                self.chat_layout_inner.addWidget(image_label)
                # 滚动到最新消息
                self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
    