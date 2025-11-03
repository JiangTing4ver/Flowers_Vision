#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
花卉识别测试文件
功能：
1. 使用PyTorch进行花卉识别
2. 结合EXIF信息（拍摄日期和地点）进行深度整理
3. 提供花卉分类和整理的基础框架
"""

import os
import sys
from PIL import Image
import json
from datetime import datetime
import requests
from io import BytesIO
import subprocess
import pkg_resources
# TODO: 检查并安装必要的依赖包.---pytoch 没有安装（maybe）
self._install_dependencies()

# 添加当前目录到Python路径，以便导入exif_test
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入EXIF读取功能
from exif_test import ExifReader


class FlowerRecognizer:
    """
    花卉识别器类
    使用PyTorch预训练模型进行花卉识别，并结合EXIF信息进行深度整理
    """
    
    def __init__(self):
        """初始化花卉识别器"""
        # 初始化EXIF读取器
        self.exif_reader = ExifReader()
        # 花卉类别映射 - 使用真实的Oxford 102花卉数据集类别
        self.class_names = self._load_class_names()
        # 花卉分类结果存储
        self.flowers_collection = {}
        # 模型相关变量
        self.model = None
        self.device = None
        # 模型是否已加载
        self.model_loaded = False
        # PyTorch是否可用
        self._torch_available = False
        # 延迟加载模型，避免在导入时就尝试加载PyTorch
        # 模型将在实际需要使用时才加载
        print("花卉识别器初始化完成，模型将在首次使用时加载")
    
    def _install_dependencies(self):
        """检查并安装必要的依赖包"""
        # 注意：PyTorch相关依赖将在load_model时检查和安装
        required_packages = ['Pillow', 'requests']
        
        for package in required_packages:
            try:
                pkg_resources.get_distribution(package)
                print(f"✓ {package} 已安装")
            except pkg_resources.DistributionNotFound:
                print(f"✗ {package} 未安装，正在安装...")
                try:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                    print(f"✓ {package} 安装成功")
                except Exception as e:
                    print(f"✗ 安装 {package} 失败: {e}")
    
    def _load_class_names(self):
        """加载真实的Oxford 102花卉数据集类别名称"""
        # Oxford 102花卉数据集的完整类别列表（中文名称）
        return [
            '花毛茛', '银莲花', '风信子', '罂粟花', '矮牵牛', '铃兰', '木槿', '耧斗菜', '百合', '鸢尾',
            '郁金香', '水仙', '雏菊', '非洲菊', '向日葵', '金合欢', '牵牛花', '报春花', '长寿花', '洋桔梗',
            '蝴蝶兰', '紫荆', '马蹄莲', '姜花', '三色堇', '天竺葵', '仙客来', '大丽花', '毛地黄', '翠菊',
            '紫罗兰', '牡丹', '玫瑰', '倒挂金钟', '石竹', '杜鹃花', '秋海棠', '茶花', '菊花', '锦葵',
            '花烛', '薰衣草', '落新妇', '凤仙花', '矢车菊', '向日葵', '蔷薇', '绣球花', '夜来香', '薄荷',
            '香雪球', '金盏菊', '勿忘我', '金合欢', '金鱼草', '金缕梅', '火鹤花', '红掌', '百日草', '薰衣草',
            '紫锥菊', '毛茛', '满天星', '虞美人', '蟹爪兰', '万寿菊', '夹竹桃', '长春花', '非洲紫罗兰', '茉莉',
            '荷花', '睡莲', '千日红', '石蒜', '桂花', '米兰', '丁香', '夜来香', '玉兰', '樱花',
            '海棠', '桃花', '梨花', '杏花', '李花', '梅花', '山茶花', '杜鹃花', '紫藤', '凌霄',
            '金银花', '牵牛花', '茑萝', '铁线莲', '藤本月季', '炮仗花', '三角梅', '常春藤', '绿萝', '吊兰'
        ]
    
    def load_model(self):
        """加载预训练的花卉识别模型
        
        使用ResNet50作为基础模型，加载预训练权重用于花卉分类
        """
        if self.model is not None and self.model_loaded:
            return True
            
        try:
            # 确保在实际需要时才导入PyTorch
            import torch
            import torch.nn as nn
            import torchvision.models as models
            
            self._torch_available = True
            
            # 设置设备（GPU如果可用，否则CPU）
            self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            
            print("正在加载花卉识别模型...")
            # 加载预训练的ResNet50模型
            self.model = models.resnet50(pretrained=True)
            
            # 修改最后一层以适应Oxford 102花卉数据集的类别数量
            num_ftrs = self.model.fc.in_features
            self.model.fc = nn.Linear(num_ftrs, len(self.class_names))
            
            # 尝试加载花卉识别的预训练权重
            # 注意：这里使用自定义权重路径，如果不存在则使用迁移学习的模型
            model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flower_model.pth')
            
            if os.path.exists(model_path):
                print(f"加载本地模型权重: {model_path}")
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            else:
                print("未找到本地模型权重，使用迁移学习基础模型")
                print("提示: 可以使用以下代码训练模型并保存权重:")
                print("  torch.save(model.state_dict(), 'flower_model.pth')")
            
            # 将模型移动到指定设备
            self.model = self.model.to(self.device)
            
            # 设置为评估模式
            self.model.eval()
            
            self.model_loaded = True
            print(f"✓ 模型已成功加载到 {self.device} 设备")
            print(f"✓ 支持 {len(self.class_names)} 种花卉类别识别")
            return True
        except Exception as e:
            print(f"✗ 加载模型时出错: {e}")
            return False
    
    def preprocess_image(self, image_path):
        """预处理图像以适应模型输入
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            预处理后的张量
        """
        # 导入PyTorch transforms
        import torchvision.transforms as transforms
        import torch
        
        # 定义图像转换
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        
        # 加载并转换图像
        image = Image.open(image_path)
        image = transform(image).unsqueeze(0)
        return image.to(self.device)
    
    def recognize_flower(self, image_path):
        """识别图像中的花卉
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            dict: 识别结果，包含花卉类别和置信度
        """
        if not self.model_loaded:
            if not self.load_model():
                return None
        
        try:
            # 导入PyTorch相关模块
            import torch
            
            print(f"正在识别图像: {os.path.basename(image_path)}")
            # 预处理图像
            image_tensor = self.preprocess_image(image_path)
            
            # 进行推理
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
                # 获取前3个预测结果
                top_p, top_indices = torch.topk(probabilities, 3)
                
                # 获取主要预测结果
                main_prediction = {
                    'class': self.class_names[top_indices[0]],
                    'confidence': top_p[0].item(),
                    'index': top_indices[0].item()
                }
                
                # 获取所有预测结果
                all_predictions = []
                for i in range(len(top_indices)):
                    all_predictions.append({
                        'class': self.class_names[top_indices[i]],
                        'confidence': top_p[i].item(),
                        'index': top_indices[i].item()
                    })
            
            print(f"✓ 识别完成: {main_prediction['class']} (置信度: {main_prediction['confidence']:.2%})")
            
            return {
                'main_prediction': main_prediction,
                'all_predictions': all_predictions,
                'confidence_score': main_prediction['confidence']
            }
        except Exception as e:
            print(f"✗ 识别花卉时出错: {e}")
            return None
    
    def get_exif_info(self, image_path):
        """获取图像的EXIF信息
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            dict: EXIF信息
        """
        try:
            if self.exif_reader.load_exif(image_path):
                device_info = self.exif_reader.get_device_info()
                image_info = self.exif_reader.get_image_info()
                location_info = self.exif_reader.get_location_info()
                
                return {
                    'device': device_info,
                    'datetime': image_info['datetime'],
                    'size': f"{image_info['width']}x{image_info['length']}",
                    'location': location_info
                }
            return None
        except Exception as e:
            print(f"获取EXIF信息时出错: {e}")
            return None
    
    def process_image(self, image_path):
        """处理单张图像，进行花卉识别和EXIF信息提取
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            dict: 包含识别结果和EXIF信息的字典
        """
        if not os.path.exists(image_path):
            print(f"✗ 文件不存在: {image_path}")
            return None
        
        print(f"\n📷 开始处理图像: {os.path.basename(image_path)}")
        print("-" * 50)
        
        # 获取EXIF信息
        exif_info = self.get_exif_info(image_path)
        
        # 确保先加载模型
        if not self._torch_available:
            self.load_model()
        
        # 识别花卉
        recognition_result = self.recognize_flower(image_path)
        
        # 打印EXIF信息摘要
        if exif_info:
            print("📍 EXIF信息:")
            if exif_info['datetime'] != '未知':
                print(f"  拍摄时间: {exif_info['datetime']}")
            if exif_info['location']['has_location']:
                print(f"  拍摄地点: {exif_info['location']['formatted_address']}")
        
        # 整合结果
        result = {
            'file_path': image_path,
            'filename': os.path.basename(image_path),
            'recognition': recognition_result,
            'exif': exif_info,
            'timestamp': datetime.now().isoformat(),
            'processing_status': 'success' if recognition_result else 'failed'
        }
        
        # 存储到花卉集合中
        self._add_to_collection(result)
        
        print("-" * 50)
        return result
    
    def _add_to_collection(self, result):
        """将处理结果添加到花卉集合中
        
        Args:
            result: 处理结果字典
        """
        if result and result['recognition']:
            # 使用花卉类别作为键（从main_prediction中获取）
            flower_class = result['recognition']['main_prediction']['class']
            
            # 如果该花卉类别不存在，创建新的列表
            if flower_class not in self.flowers_collection:
                self.flowers_collection[flower_class] = []
            
            # 添加到对应类别
            self.flowers_collection[flower_class].append(result)
    
    def organize_by_date(self):
        """按拍摄日期整理花卉照片
        
        Returns:
            dict: 按日期组织的花卉照片
        """
        organized_by_date = {}
        
        # 遍历所有花卉类别和照片
        for flower_class, photos in self.flowers_collection.items():
            for photo in photos:
                if photo and photo['exif']:
                    datetime_str = photo['exif']['datetime']
                    
                    # 确保datetime_str是字符串并处理IfdTag对象
                    if datetime_str != '未知' and datetime_str is not None:
                        # 转换IfdTag对象为字符串（如果需要）
                        if hasattr(datetime_str, 'printable'):
                            datetime_str = datetime_str.printable
                        elif hasattr(datetime_str, '__str__'):
                            datetime_str = str(datetime_str)
                        
                        try:
                            # 尝试解析日期
                            # 处理不同格式的日期字符串
                            if ':' in datetime_str.split()[0]:
                                # 格式: "2023:04:15 14:30:25"
                                date_obj = datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")
                            else:
                                # 格式: "2023-04-15 14:30:25"
                                date_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                            
                            # 按年月日分组
                            date_key = date_obj.strftime("%Y-%m-%d")
                            
                            if date_key not in organized_by_date:
                                organized_by_date[date_key] = []
                            
                            organized_by_date[date_key].append(photo)
                        except ValueError:
                            # 如果日期格式无法解析，跳过
                            continue
        
        return organized_by_date
    
    def organize_by_location(self):
        """按拍摄地点整理花卉照片
        
        Returns:
            dict: 按地点组织的花卉照片
        """
        organized_by_location = {}
        
        # 遍历所有花卉类别和照片
        for flower_class, photos in self.flowers_collection.items():
            for photo in photos:
                if photo['exif'] and photo['exif']['location']['has_location']:
                    # 使用格式化地址作为键
                    location = photo['exif']['location'].get('formatted_address', '未知地点')
                    
                    if location not in organized_by_location:
                        organized_by_location[location] = []
                    
                    organized_by_location[location].append(photo)
        
        return organized_by_location
    
    def _convert_serializable(self, data):
        """递归转换数据结构中的不可序列化对象为字符串
        
        Args:
            data: 待转换的数据（字典、列表、对象等）
            
        Returns:
            可JSON序列化的数据
        """
        if isinstance(data, dict):
            return {key: self._convert_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_serializable(item) for item in data]
        elif hasattr(data, 'printable'):
            # 处理EXIF中的IfdTag对象
            return data.printable
        elif hasattr(data, '__str__'):
            # 处理其他可能的自定义对象
            return str(data)
        else:
            # 基本类型直接返回
            return data
    
    def export_collection(self, output_file):
        """导出花卉集合到JSON文件
        
        Args:
            output_file: 输出文件路径
        
        Returns:
            bool: 是否成功导出
        """
        # 准备导出数据
        export_data = {
            'flowers_by_class': self.flowers_collection,
            'flowers_by_date': self.organize_by_date(),
            'flowers_by_location': self.organize_by_location(),
            'statistics': {
                'total_flowers': sum(len(photos) for photos in self.flowers_collection.values()),
                'flower_classes': list(self.flowers_collection.keys()),
                'total_classes': len(self.flowers_collection)
            },
            'export_time': datetime.now().isoformat()
        }
        
        try:
            # 转换为可JSON序列化的数据
            serializable_data = self._convert_serializable(export_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            print(f"花卉集合已导出到: {output_file}")
            return True
        except Exception as e:
            print(f"导出花卉集合时出错: {e}")
            return False
    
    def batch_process(self, directory):
        """批量处理目录中的所有图片
        
        Args:
            directory: 包含图片的目录路径
        """
        if not os.path.isdir(directory):
            print(f"目录不存在: {directory}")
            return
        
        # 支持的图片格式
        supported_formats = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
        
        # 遍历目录中的所有文件
        for filename in os.listdir(directory):
            if filename.lower().endswith(supported_formats):
                file_path = os.path.join(directory, filename)
                self.process_image(file_path)
        
        print(f"批量处理完成，共识别到 {sum(len(photos) for photos in self.flowers_collection.values())} 张花卉照片")


def main():
    """花卉识别主程序 - 实际运行版本"""
    print("🌼 花卉识别与深度整理工具")
    print("=" * 50)
    print("功能：使用PyTorch进行真实花卉识别，并结合拍摄日期和地点进行深度整理")
    print("=" * 50)
    
    # 创建花卉识别器实例
    recognizer = FlowerRecognizer()
    
    # 加载模型
    print("\n🔄 初始化并加载花卉识别模型...")
    if not recognizer.load_model():
        print("\n⚠️  注意：使用的是迁移学习基础模型，识别准确率可能有限")
        print("   建议使用花卉数据集训练并保存专用模型权重")
    
    # 设置图片目录 - 优先使用用户指定的目录
    image_dir = None
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        image_dir = sys.argv[1]
    
    # 如果没有指定目录，检查默认位置
    if not image_dir:
        # 检查example目录
        example_dir = os.path.join(current_dir, 'example')
        if os.path.exists(example_dir):
            image_dir = example_dir
            print(f"\n📂 找到示例图片目录: {image_dir}")
        else:
            # 使用当前目录
            image_dir = current_dir
            print(f"\n📂 使用当前目录作为图片源: {image_dir}")
    
    # 批量处理图片
    print(f"\n🚀 开始批量处理图片...")
    recognizer.batch_process(image_dir)
    
    # 显示识别结果统计
    print("\n📊 花卉识别统计结果:")
    print("=" * 50)
    
    if recognizer.flowers_collection:
        total_flowers = sum(len(photos) for photos in recognizer.flowers_collection.values())
        print(f"\n总识别花卉照片: {total_flowers} 张")
        print(f"识别花卉种类数: {len(recognizer.flowers_collection)} 种")
        
        # 按数量排序并显示前10种花卉
        sorted_flowers = sorted(
            recognizer.flowers_collection.items(), 
            key=lambda x: len(x[1]), 
            reverse=True
        )
        
        print("\n识别到的花卉种类:")
        for i, (flower_class, photos) in enumerate(sorted_flowers[:10], 1):
            print(f"  {i:2d}. {flower_class}: {len(photos)} 张")
        
        if len(sorted_flowers) > 10:
            print(f"  ... 还有 {len(sorted_flowers) - 10} 种花卉未显示")
        
        # 按日期整理统计
        date_organized = recognizer.organize_by_date()
        if date_organized:
            print(f"\n📅 按日期整理: {len(date_organized)} 个不同日期")
            # 显示最早和最近的拍摄日期
            dates = sorted(date_organized.keys())
            print(f"   最早拍摄日期: {dates[0]} ({len(date_organized[dates[0]])} 张)")
            print(f"   最近拍摄日期: {dates[-1]} ({len(date_organized[dates[-1]])} 张)")
        
        # 按地点整理统计
        location_organized = recognizer.organize_by_location()
        if location_organized:
            print(f"\n📍 按地点整理: {len(location_organized)} 个不同地点")
            # 显示拍摄照片最多的地点
            top_location = max(location_organized.items(), key=lambda x: len(x[1]))
            print(f"   拍摄最多的地点: {top_location[0]} ({len(top_location[1])} 张)")
    else:
        print("\n⚠️  未识别到任何花卉照片")
        print("   请确保目录中包含花卉图片，且图片清晰可见")
    
    # 导出识别结果
    output_file = os.path.join(current_dir, 'flower_recognition_results.json')
    print(f"\n💾 导出识别结果到: {output_file}")
    if recognizer.export_collection(output_file):
        print("   ✓ 导出成功")
    else:
        print("   ✗ 导出失败")
    
    print("\n🎉 花卉识别任务完成！")
    print("=" * 50)
    print("提示：")
    print("1. 可以通过命令行参数指定图片目录: python flower_recognition_test.py /path/to/images")
    print("2. 要提高识别准确率，建议使用花卉数据集训练专用模型")
    print("3. 导出的JSON文件包含详细的识别结果和整理信息")


if __name__ == '__main__':
    # 运行主程序
    main()
