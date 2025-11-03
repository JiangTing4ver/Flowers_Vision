#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QTextEdit, QLabel, QMessageBox, QSplitter,
    QFrame, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont, QTextOption
from PyQt5.QtCore import Qt, QSize

# 添加当前目录的父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exif_test import ExifReader


class ExifViewer(QMainWindow):
    """
    EXIF查看器主窗口类
    """
    
    def __init__(self):
        """初始化EXIF查看器"""
        super().__init__()
        self.init_ui()
        self.exif_reader = ExifReader()
        self.setup_console_redirect()   # 重定向标准输出到文本框
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle('EXIF信息查看器')
        self.setGeometry(100, 100, 900, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部按钮区域
        top_layout = QHBoxLayout()
        
        # 创建选择文件按钮
        self.select_button = QPushButton('选择图片文件')
        self.select_button.setMinimumHeight(40)
        self.select_button.clicked.connect(self.select_image)
        
        # 创建清空按钮
        self.clear_button = QPushButton('清空')
        self.clear_button.setMinimumHeight(40)
        self.clear_button.clicked.connect(self.clear_all)
        
        # 添加按钮到顶部布局
        top_layout.addWidget(self.select_button)
        top_layout.addWidget(self.clear_button)
        top_layout.addStretch()
        
        # 添加顶部布局到主布局
        main_layout.addLayout(top_layout)
        
        # 创建分割器，用于分割图片预览和EXIF信息
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建左侧图片预览区域
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        
        self.image_label = QLabel('图片预览')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFrameStyle(QLabel.Panel | QLabel.Sunken)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        left_layout.addWidget(self.image_label)
        
        # 创建右侧EXIF信息显示区域
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        
        # 创建EXIF信息标题
        exif_label = QLabel('EXIF信息')
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        exif_label.setFont(font)
        
        # 创建文本编辑框用于显示EXIF信息
        self.exif_text = QTextEdit()
        self.exif_text.setReadOnly(True)
        self.exif_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.exif_text.setWordWrapMode(QTextOption.WordWrap)
        
        # 添加到右侧布局
        right_layout.addWidget(exif_label)
        right_layout.addWidget(self.exif_text)
        
        # 添加左右框架到分割器
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        
        # 设置分割器的初始大小比例
        splitter.setSizes([400, 500])
        
        # 添加分割器到主布局
        main_layout.addWidget(splitter, 1)
    
    def setup_console_redirect(self):
        """重定向控制台输出到文本编辑框"""
        # 保存原始的stdout
        self.original_stdout = sys.stdout
        # 创建一个自定义的输出流类
        class ConsoleRedirect:
            def __init__(self, text_edit):
                self.text_edit = text_edit
            
            def write(self, text):
                # 将输出写入文本编辑框
                self.text_edit.insertPlainText(text)
                # 滚动到底部
                self.text_edit.moveCursor(self.text_edit.textCursor().End)
            
            # 实现flush方法以支持print函数的flush参数
            def flush(self):
                pass
        
        # 重定向stdout
        sys.stdout = ConsoleRedirect(self.exif_text)
    
    def select_image(self):
        """选择图片文件并显示EXIF信息"""
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择图片文件', 
            '', 
            '图片文件 (*.jpg *.jpeg *.png *.tiff *.bmp)'
        )
        
        if file_path:
            try:
                # 清空之前的内容
                self.exif_text.clear()
                
                # 显示图片预览
                self.display_image_preview(file_path)
                
                # 使用ExifReader类处理图片
                print(f"正在处理文件: {file_path}")
                self.exif_reader.process_image(file_path)
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'处理图片时出错: {str(e)}')
    
    def display_image_preview(self, file_path):
        """显示图片预览"""
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            # 缩放图片以适应标签大小
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText('无法加载图片')
            QMessageBox.warning(self, '警告', '无法显示图片预览')
    
    def clear_all(self):
        """清空所有内容"""
        self.exif_text.clear()
        self.image_label.clear()
        self.image_label.setText('图片预览')
    
    def resizeEvent(self, event):
        """窗口大小改变时重新调整图片预览大小"""
        if self.image_label.pixmap() is not None:
            scaled_pixmap = self.image_label.pixmap().scaled(
                self.image_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        super().resizeEvent(event)
    
    def closeEvent(self, event):
        """关闭窗口时恢复原始的stdout"""
        sys.stdout = self.original_stdout
        event.accept()


def main():
    """主函数"""
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = ExifViewer()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()