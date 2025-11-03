#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import sys
import os
import subprocess
import time

# 首先检查并安装PyQt5依赖
def install_dependencies():
    """检查并安装必要的依赖包"""
    required_packages = ['PyQt5']
    installed = False
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"正在安装依赖包 {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            installed = True
    
    return installed

# 安装依赖
if install_dependencies():
    print("依赖安装完成，重新启动程序...")
    time.sleep(2)
    os.execv(sys.executable, [sys.executable] + sys.argv)

# 现在导入PyQt5模块
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QTextEdit, QLabel, QMessageBox, QSplitter,
    QFrame, QSizePolicy, QTabWidget, QProgressBar, QTreeWidget, QTreeWidgetItem,
    QMenu, QAction, QHeaderView, QGroupBox, QGridLayout, QStatusBar
)
from PyQt5.QtGui import QPixmap, QFont, QTextOption, QColor, QIcon
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QCoreApplication

# 添加当前目录到Python路径，以便导入flower_recognition_test和exif_test
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入花卉识别器和EXIF读取器
from flower_recognition_test import FlowerRecognizer
from exif_test import ExifReader


class FlowerRecognitionThread(QThread):
    """
    花卉识别处理线程类，用于在后台处理图片的花卉识别和EXIF信息提取
    """
    # 信号定义
    finished = pyqtSignal(object)  # 处理完成信号，返回处理结果
    error = pyqtSignal(str)  # 错误信号
    progress = pyqtSignal(int)  # 进度信号
    status = pyqtSignal(str)  # 状态更新信号
    file_processed = pyqtSignal(str, object)  # 单个文件处理完成信号
    
    def __init__(self, recognizer, file_paths):
        """初始化处理线程
        
        Args:
            recognizer: FlowerRecognizer实例
            file_paths: 要处理的图片文件路径列表
        """
        super().__init__()
        self.recognizer = recognizer
        self.file_paths = file_paths
        self.is_running = True
    
    def run(self):
        """线程运行方法，在后台处理花卉识别和EXIF信息"""
        try:
            total_files = len(self.file_paths)
            for i, file_path in enumerate(self.file_paths):
                if not self.is_running:
                    break
                    
                # 发送状态更新
                self.status.emit(f"正在处理: {os.path.basename(file_path)}")
                
                # 处理图片 - 即使花卉识别失败也应获取EXIF信息
                try:
                    # 尝试正常处理
                    result = self.recognizer.process_image(file_path)
                    
                    # 如果result为None，创建一个只包含EXIF信息的结果
                    if result is None:
                        result = {'recognition': None}
                        # 直接从ExifReader获取EXIF信息
                        from exif_test import ExifReader
                        exif_reader = ExifReader(file_path)
                        result['exif'] = exif_reader.get_all_info()
                        print(f"无法进行花卉识别，但成功提取了EXIF信息: {os.path.basename(file_path)}")
                    
                    # 发送文件处理完成信号
                    if result:
                        self.file_processed.emit(file_path, result)
                except Exception as e:
                    # 即使处理单个文件失败，也继续处理其他文件
                    print(f"处理文件时出错: {str(e)}")
                    # 创建一个错误结果
                    error_result = {
                        'recognition': None,
                        'exif': None,
                        'error': str(e)
                    }
                    self.file_processed.emit(file_path, error_result)
                
                # 更新进度
                progress = int((i + 1) / total_files * 100)
                self.progress.emit(progress)
            
            if self.is_running:
                # 发送完成信号
                self.finished.emit(self.recognizer.flowers_collection)
        except Exception as e:
            # 发送错误信号
            self.error.emit(str(e))
    
    def stop(self):
        """停止处理线程"""
        self.is_running = False
        self.wait()


class FlowerRecognitionApp(QMainWindow):
    """
    花卉识别与整理GUI应用主窗口类
    """
    
    def __init__(self):
        """初始化花卉识别应用"""
        super().__init__()
        self.init_ui()
        
        # 初始化花卉识别器
        self.recognizer = FlowerRecognizer()
        self.setup_console_redirect()  # 重定向标准输出到文本框
        self.process_thread = None  # 初始化处理线程为None
        
        # 存储处理结果
        self.current_results = {}
        self.current_file_path = None
        
        # 初始化模型
        self.initialize_model()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle('花卉识别与整理工具')
        self.setGeometry(100, 100, 1200, 700)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部按钮区域
        top_layout = QHBoxLayout()
        
        # 创建选择单个文件按钮
        self.select_file_button = QPushButton('选择单个图片')
        self.select_file_button.setMinimumHeight(40)
        self.select_file_button.clicked.connect(self.select_single_image)
        
        # 创建选择目录按钮
        self.select_dir_button = QPushButton('选择图片目录')
        self.select_dir_button.setMinimumHeight(40)
        self.select_dir_button.clicked.connect(self.select_image_directory)
        
        # 创建停止处理按钮
        self.stop_button = QPushButton('停止处理')
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_processing)
        
        # 创建导出结果按钮
        self.export_button = QPushButton('导出结果')
        self.export_button.setMinimumHeight(40)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_results)
        
        # 添加按钮到顶部布局
        top_layout.addWidget(self.select_file_button)
        top_layout.addWidget(self.select_dir_button)
        top_layout.addWidget(self.stop_button)
        top_layout.addWidget(self.export_button)
        top_layout.addStretch()
        
        # 添加顶部布局到主布局
        main_layout.addLayout(top_layout)
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 创建状态标签
        self.status_label = QLabel('就绪')
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet('color: #0066cc;')
        main_layout.addWidget(self.status_label)
        
        # 创建分割器，用于分割左侧图片预览和右侧标签页
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
        
        # 创建右侧标签页
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        
        # 创建识别结果标签页
        self.recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(self.recognition_tab)
        
        # 创建识别结果文本框
        self.recognition_text = QTextEdit()
        self.recognition_text.setReadOnly(True)
        self.recognition_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.recognition_text.setWordWrapMode(QTextOption.WordWrap)
        recognition_layout.addWidget(self.recognition_text)
        
        # 添加识别结果标签页
        self.tab_widget.addTab(self.recognition_tab, '识别结果')
        
        # 创建EXIF信息标签页
        self.exif_tab = QWidget()
        exif_layout = QVBoxLayout(self.exif_tab)
        
        # 创建EXIF信息文本框
        self.exif_text = QTextEdit()
        self.exif_text.setReadOnly(True)
        self.exif_text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.exif_text.setWordWrapMode(QTextOption.WordWrap)
        exif_layout.addWidget(self.exif_text)
        
        # 添加EXIF信息标签页
        self.tab_widget.addTab(self.exif_tab, 'EXIF信息')
        
        # 创建整理结果标签页
        self.organization_tab = QWidget()
        organization_layout = QVBoxLayout(self.organization_tab)
        
        # 创建整理结果树
        self.organization_tree = QTreeWidget()
        self.organization_tree.setHeaderLabels(['项目', '数量', '详情'])
        self.organization_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        organization_layout.addWidget(self.organization_tree)
        
        # 添加整理结果标签页
        self.tab_widget.addTab(self.organization_tab, '整理结果')
        
        # 添加标签页到右侧布局
        right_layout.addWidget(self.tab_widget)
        
        # 添加左右框架到分割器
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        
        # 设置分割器的初始大小比例
        splitter.setSizes([500, 700])
        
        # 添加分割器到主布局
        main_layout.addWidget(splitter, 1)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('就绪')
    
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
                QCoreApplication.processEvents()  # 确保UI响应
                self.text_edit.insertPlainText(text)
                # 滚动到底部
                self.text_edit.moveCursor(self.text_edit.textCursor().End)
            
            # 实现flush方法以支持print函数的flush参数
            def flush(self):
                pass
        
        # 创建文本编辑框用于显示日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        # 重定向stdout
        sys.stdout = ConsoleRedirect(self.log_text)
    
    def initialize_model(self):
        """初始化花卉识别模型"""
        # 不再在线程中预先加载模型，而是在首次使用时加载
        self.status_label.setText('花卉识别器已初始化')
        self.statusBar.showMessage('就绪')
        
        # 直接添加日志标签页
        # 创建日志标签页
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        log_layout.addWidget(self.log_text)
        self.tab_widget.addTab(self.log_tab, '处理日志')
        
        print("花卉识别GUI已初始化，模型将在首次处理图片时加载")
    
    def select_single_image(self):
        """选择单个图片文件并进行识别"""
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择图片文件', 
            '', 
            '图片文件 (*.jpg *.jpeg *.png *.tiff *.bmp)'
        )
        
        if file_path:
            self.process_file(file_path)
    
    def select_image_directory(self):
        """选择图片目录并批量处理"""
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(
            self, 
            '选择图片目录', 
            ''
        )
        
        if directory:
            # 获取目录中的所有图片文件
            supported_formats = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
            image_files = []
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        image_files.append(os.path.join(root, file))
            
            if image_files:
                self.process_files(image_files)
            else:
                QMessageBox.information(self, '提示', '所选目录中没有找到支持的图片文件')
    
    def process_file(self, file_path):
        """处理单个文件"""
        self.process_files([file_path])
    
    def process_files(self, file_paths):
        """处理多个文件"""
        # 检查是否有正在运行的线程，如果有则停止
        if self.process_thread and self.process_thread.isRunning():
            self.process_thread.stop()
        
        # 清空之前的内容
        self.recognition_text.clear()
        self.exif_text.clear()
        self.organization_tree.clear()
        
        # 更新UI状态
        self.select_file_button.setEnabled(False)
        self.select_dir_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 显示第一个文件的预览（如果有）
        if file_paths:
            self.current_file_path = file_paths[0]
            self.display_image_preview(file_paths[0])
        
        # 创建并启动处理线程
        self.process_thread = FlowerRecognitionThread(self.recognizer, file_paths)
        self.process_thread.finished.connect(self.on_process_finished)
        self.process_thread.error.connect(self.on_process_error)
        self.process_thread.progress.connect(self.on_progress_update)
        self.process_thread.status.connect(self.on_status_update)
        self.process_thread.file_processed.connect(self.on_file_processed)
        self.process_thread.start()
    
    def stop_processing(self):
        """停止处理"""
        if self.process_thread and self.process_thread.isRunning():
            self.status_label.setText('正在停止处理...')
            self.process_thread.stop()
            self.status_label.setText('处理已停止')
            self.statusBar.showMessage('处理已停止')
            
            # 更新UI状态
            self.select_file_button.setEnabled(True)
            self.select_dir_button.setEnabled(True)
            self.stop_button.setEnabled(False)
    
    def on_file_processed(self, file_path, result):
        """单个文件处理完成回调"""
        # 存储结果
        self.current_results[file_path] = result
        
        # 如果是当前显示的文件，更新显示
        if file_path == self.current_file_path:
            self.update_display(result)
    
    def on_progress_update(self, progress):
        """进度更新回调"""
        self.progress_bar.setValue(progress)
    
    def on_status_update(self, status):
        """状态更新回调"""
        self.status_label.setText(status)
        self.statusBar.showMessage(status)
    
    def on_process_finished(self, results):
        """所有文件处理完成回调"""
        # 更新UI状态
        self.select_file_button.setEnabled(True)
        self.select_dir_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        # 即使没有识别结果，也启用导出按钮（可以导出EXIF信息）
        self.export_button.setEnabled(True)
        self.status_label.setText('处理完成')
        self.statusBar.showMessage('处理完成')
        
        # 更新整理结果树（如果有结果）
        if results:
            self.update_organization_tree()
        else:
            # 创建一个简单的整理结果，显示处理的文件数量
            self.organization_tree.clear()
            root = QTreeWidgetItem(['处理结果', str(len(self.current_results)), ''])
            self.organization_tree.addTopLevelItem(root)
        
        # 显示统计信息
        total_files = len(self.current_results)
        
        # 尝试计算花卉识别的统计信息
        try:
            total_flowers = sum(len(photos) for photos in results.values())
            total_classes = len(results)
            message = f'共处理完成 {total_files} 张图片\n'
            
            if total_flowers > 0:
                message += f'识别到 {total_flowers} 张花卉照片\n'
                message += f'识别出 {total_classes} 种花卉\n'
            else:
                message += '花卉识别功能暂时不可用\n'
                message += 'EXIF信息已成功提取'
        except:
            message = f'共处理完成 {total_files} 张图片\n'
            message += '花卉识别功能暂时不可用\n'
            message += 'EXIF信息已成功提取'
        
        QMessageBox.information(self, '处理完成', message)
    
    def on_process_error(self, error_message):
        """处理错误回调"""
        # 更新UI状态
        self.select_file_button.setEnabled(True)
        self.select_dir_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText('处理出错')
        self.statusBar.showMessage('处理出错')
        
        # 显示错误信息
        QMessageBox.critical(self, '错误', f'处理图片时出错: {error_message}')
    
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
    
    def update_display(self, result):
        """更新识别结果和EXIF信息显示"""
        # 更新识别结果
        recognition_text = "=== 花卉识别结果 ===\n\n"
        
        # 检查是否有错误信息
        if result.get('error'):
            recognition_text += f"处理过程中出现错误:\n{result['error']}\n\n"
            recognition_text += "花卉识别功能暂时不可用，但EXIF信息查看仍可正常使用。"
        elif result and result.get('recognition'):
            if 'main_prediction' in result['recognition']:
                main_pred = result['recognition']['main_prediction']
                recognition_text += f"主要识别结果: {main_pred['class']}\n"
                recognition_text += f"置信度: {main_pred['confidence']:.2%}\n\n"
                
                if 'all_predictions' in result['recognition']:
                    recognition_text += "前3个预测结果:\n"
                    for i, pred in enumerate(result['recognition']['all_predictions'], 1):
                        recognition_text += f"{i}. {pred['class']}: {pred['confidence']:.2%}\n"
            else:
                recognition_text += "花卉识别功能暂时不可用\n"
        else:
            recognition_text += "未能识别出花卉\n"
            recognition_text += "注意：PyTorch可能未正确安装或存在兼容性问题\n"
            recognition_text += "EXIF信息查看功能仍可正常使用"
        
        self.recognition_text.setText(recognition_text)
        
        # 更新EXIF信息
        exif_text = "=== EXIF信息 ===\n\n"
        if result and result.get('exif'):
            exif = result['exif']
            
            # 设备信息
            if exif.get('device'):
                device = exif['device']
                exif_text += "设备信息:\n"
                if device.get('camera_model'):
                    exif_text += f"  相机型号: {device['camera_model']}\n"
                if device.get('manufacturer'):
                    exif_text += f"  制造商: {device['manufacturer']}\n"
            
            # 拍摄时间
            if exif.get('datetime') and exif['datetime'] != '未知':
                datetime_str = exif['datetime']
                # 处理IfdTag对象
                if hasattr(datetime_str, 'printable'):
                    datetime_str = datetime_str.printable
                elif hasattr(datetime_str, '__str__'):
                    datetime_str = str(datetime_str)
                exif_text += f"\n拍摄时间: {datetime_str}\n"
            
            # 图片尺寸
            if exif.get('size'):
                exif_text += f"\n图片尺寸: {exif['size']}\n"
            
            # 位置信息
            if exif.get('location') and exif['location'].get('has_location'):
                location = exif['location']
                exif_text += "\n位置信息:\n"
                if location.get('formatted_address'):
                    exif_text += f"  地址: {location['formatted_address']}\n"
                if location.get('latitude') and location.get('longitude'):
                    exif_text += f"  坐标: {location['latitude']}, {location['longitude']}\n"
        else:
            exif_text += "未能获取EXIF信息\n"
        
        self.exif_text.setText(exif_text)
    
    def update_organization_tree(self):
        """更新整理结果树"""
        # 清空树
        self.organization_tree.clear()
        
        # 添加按类别整理
        by_class_root = QTreeWidgetItem(['按花卉种类整理', 
                                       str(len(self.recognizer.flowers_collection)), 
                                       ''])
        
        # 按数量排序
        sorted_flowers = sorted(
            self.recognizer.flowers_collection.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )
        
        for flower_class, photos in sorted_flowers:
            class_item = QTreeWidgetItem([flower_class, str(len(photos)), ''])
            by_class_root.addChild(class_item)
        
        self.organization_tree.addTopLevelItem(by_class_root)
        
        # 添加按日期整理
        date_organized = self.recognizer.organize_by_date()
        if date_organized:
            by_date_root = QTreeWidgetItem(['按拍摄日期整理', 
                                         str(len(date_organized)), 
                                         ''])
            
            # 按日期排序
            sorted_dates = sorted(date_organized.keys())
            
            for date in sorted_dates:
                date_item = QTreeWidgetItem([date, str(len(date_organized[date])), ''])
                by_date_root.addChild(date_item)
            
            self.organization_tree.addTopLevelItem(by_date_root)
        
        # 添加按地点整理
        location_organized = self.recognizer.organize_by_location()
        if location_organized:
            by_location_root = QTreeWidgetItem(['按拍摄地点整理', 
                                             str(len(location_organized)), 
                                             ''])
            
            # 按数量排序
            sorted_locations = sorted(
                location_organized.items(), 
                key=lambda x: len(x[1]), 
                reverse=True
            )
            
            for location, photos in sorted_locations:
                location_item = QTreeWidgetItem([location, str(len(photos)), ''])
                by_location_root.addChild(location_item)
            
            self.organization_tree.addTopLevelItem(by_location_root)
        
        # 展开所有节点
        self.organization_tree.expandAll()
    
    def export_results(self):
        """导出识别结果"""
        # 打开文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            '导出结果', 
            os.path.join(current_dir, 'flower_recognition_results.json'),
            'JSON文件 (*.json)'
        )
        
        if file_path:
            self.statusBar.showMessage('正在导出结果...')
            if self.recognizer.export_collection(file_path):
                QMessageBox.information(self, '成功', f'结果已成功导出到:\n{file_path}')
                self.statusBar.showMessage('导出完成')
            else:
                QMessageBox.critical(self, '错误', '导出结果失败')
                self.statusBar.showMessage('导出失败')
    
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
        """关闭窗口时恢复原始的stdout并停止线程"""
        # 检查是否有正在运行的线程，如果有则停止
        if hasattr(self, 'process_thread') and self.process_thread and self.process_thread.isRunning():
            self.process_thread.stop()
        
        # 检查是否有正在运行的模型线程，如果有则停止
        if hasattr(self, 'model_thread') and self.model_thread and self.model_thread.isRunning():
            self.model_thread.quit()
            self.model_thread.wait()
        
        # 恢复原始的stdout
        sys.stdout = self.original_stdout
        event.accept()


def main():
    """主函数"""
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = FlowerRecognitionApp()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
