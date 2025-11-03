#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import exifread
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time


class ExifReader:
    """
    EXIF信息读取器类，用于从图片中提取EXIF信息，包括设备信息、拍摄时间和GPS位置等。
    """
    
    def __init__(self):
        """初始化EXIF读取器"""
        self.exif_data = None
        self.image_path = None
    
    def convert_to_decimal(self, coord, ref):
        """将EXIF格式的经纬度转换为十进制格式"""
        # coord通常是一个包含三个元素的列表：度、分、秒
        d, m, s = 0, 0, 0
        
        # 处理exifread返回的格式
        if hasattr(coord, 'values'):
            coord_values = coord.values
        else:
            coord_values = coord
        
        if len(coord_values) >= 3:
            # 处理度
            if hasattr(coord_values[0], 'num') and hasattr(coord_values[0], 'den'):
                d = coord_values[0].num / coord_values[0].den
            else:
                d = float(coord_values[0])
            
            # 处理分
            if hasattr(coord_values[1], 'num') and hasattr(coord_values[1], 'den'):
                m = coord_values[1].num / coord_values[1].den
            else:
                m = float(coord_values[1])
            
            # 处理秒
            if hasattr(coord_values[2], 'num') and hasattr(coord_values[2], 'den'):
                s = coord_values[2].num / coord_values[2].den
            else:
                s = float(coord_values[2])
        
        # 计算十进制坐标
        decimal = d + (m / 60.0) + (s / 3600.0)
        
        # 根据参考方向调整符号
        if ref in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    
    def get_address_from_coordinates(self, lat, lon, max_retries=3):
        """
        通过经纬度获取地址信息
        使用geopy和Nominatim服务进行逆地理编码
        """
        geolocator = Nominatim(user_agent="photo_exif_location", timeout=10)
        
        # 重试机制
        for attempt in range(max_retries):
            try:
                location = geolocator.reverse((lat, lon), language='zh-CN')
                if location:
                    return location.raw.get('address', {})
                return None
            except GeocoderTimedOut:
                print(f"地理编码请求超时，第 {attempt + 1} 次尝试...")
                time.sleep(1)
            except GeocoderServiceError as e:
                print(f"地理编码服务错误: {e}，第 {attempt + 1} 次尝试...")
                time.sleep(1)
            except Exception as e:
                print(f"获取地址信息时出错: {e}")
                break
        
        print("多次尝试后仍无法获取地址信息")
        return None
    
    def format_address(self, address):
        """格式化地址信息，提取关键部分"""
        if not address:
            return "地址信息不可用"
        
        # 尝试提取关键地址组件
        country = address.get('country', '未知国家')
        province = address.get('state', '') or address.get('province', '') or '未知省份'
        city = address.get('city', '') or address.get('district', '') or '未知城市'
        town = address.get('town', '') or address.get('county', '') or ''
        street = address.get('road', '') or address.get('street', '') or ''
        number = address.get('house_number', '')
        
        # 构建完整地址
        address_parts = [country, province, city]
        if town:
            address_parts.append(town)
        if street:
            address_parts.append(street)
            if number:
                address_parts.append(number)
        
        # 移除空字符串并连接
        return '，'.join(filter(None, address_parts))
    
    def load_exif(self, image_path):
        """
        加载图片的EXIF数据
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            bool: 是否成功加载
        """
        # 检查文件是否存在
        if not os.path.exists(image_path):
            print(f"错误: 文件 '{image_path}' 不存在")
            return False
        
        try:
            with open(image_path, 'rb') as f:
                self.exif_data = exifread.process_file(f)
                self.image_path = image_path
                return True
        except Exception as e:
            print(f"读取文件时出错: {e}")
            return False
    
    def get_device_info(self):
        """
        获取设备信息
        
        Returns:
            dict: 包含相机品牌和型号的字典
        """
        if not self.exif_data:
            return {'make': '未知', 'model': '未知'}
        
        return {
            'make': self.exif_data.get('Image Make', '未知'),
            'model': self.exif_data.get('Image Model', '未知')
        }
    
    def get_image_info(self):
        """
        获取图片基本信息
        
        Returns:
            dict: 包含拍摄时间和图片尺寸的字典
        """
        if not self.exif_data:
            return {'datetime': '未知', 'length': '未知', 'width': '未知'}
        
        return {
            'datetime': self.exif_data.get('Image DateTime', '未知'),
            'length': self.exif_data.get('EXIF ExifImageLength', '未知'),
            'width': self.exif_data.get('EXIF ExifImageWidth', '未知')
        }
    
    def get_location_info(self):
        """
        获取位置信息
        
        Returns:
            dict: 包含经纬度和地址信息的字典
        """
        if not self.exif_data:
            return {'has_location': False, 'error': '未加载EXIF数据'}
        
        # 检查是否有GPS信息
        if all(key in self.exif_data for key in ['GPS GPSLongitudeRef', 'GPS GPSLongitude', 
                                               'GPS GPSLatitudeRef', 'GPS GPSLatitude']):
            try:
                # 获取原始的经纬度信息
                lon_ref = self.exif_data['GPS GPSLongitudeRef'].printable
                lon = self.exif_data['GPS GPSLongitude']
                lat_ref = self.exif_data['GPS GPSLatitudeRef'].printable
                lat = self.exif_data['GPS GPSLatitude']
                
                # 转换为十进制格式
                dec_lat = self.convert_to_decimal(lat, lat_ref)
                dec_lon = self.convert_to_decimal(lon, lon_ref)
                
                # 获取地址信息
                address_info = self.get_address_from_coordinates(dec_lat, dec_lon)
                
                return {
                    'has_location': True,
                    'raw_lat': f"{lat_ref}{lat}",
                    'raw_lon': f"{lon_ref}{lon}",
                    'decimal_lat': dec_lat,
                    'decimal_lon': dec_lon,
                    'address_info': address_info,
                    'formatted_address': self.format_address(address_info) if address_info else "无法获取地址信息"
                }
            except Exception as e:
                return {'has_location': False, 'error': f"处理位置信息时出错: {e}"}
        else:
            return {'has_location': False, 'error': '未找到GPS信息'}
    
    def print_device_info(self):
        """打印设备信息"""
        info = self.get_device_info()
        print('相机品牌:', info['make'])
        print('相机型号:', info['model'])
    
    def print_image_info(self):
        """打印图片基本信息"""
        info = self.get_image_info()
        print('拍摄时间:', info['datetime'])
        print('图片大小:', info['length'], '*', info['width'])
    
    def print_location_info(self):
        """打印位置信息"""
        info = self.get_location_info()
        
        if info['has_location']:
            print(f'原始经纬度: {info["raw_lat"]}, {info["raw_lon"]}')
            print(f'十进制经纬度: {info["decimal_lat"]:.6f}, {info["decimal_lon"]:.6f}')
            print(f'地址信息: {info["formatted_address"]}')
            
            if info['address_info']:
                print('详细地址组件:')
                for key, value in info['address_info'].items():
                    print(f"  {key}: {value}")
        else:
            print(f'经纬度: {info["error"]}')
    
    def print_all_info(self):
        """打印所有EXIF信息"""
        if not self.exif_data:
            print("未加载EXIF数据")
            return
        
        print("\n--- 设备信息 ---")
        self.print_device_info()
        
        print("\n--- 图片信息 ---")
        self.print_image_info()
        
        print("\n--- 位置信息 ---")
        self.print_location_info()
    
    def process_image(self, image_path):
        """
        处理图片并打印所有EXIF信息
        
        Args:
            image_path: 图片文件路径
        """
        print(f"尝试读取文件: {image_path}")
        if self.load_exif(image_path):
            self.print_all_info()


def main():
    # 创建ExifReader实例
    reader = ExifReader()
    
    # 构建图片路径
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                              'example', 'Vivo.jpg')
    
    # 处理图片
    reader.process_image(image_path)


if __name__ == '__main__':
    main()
