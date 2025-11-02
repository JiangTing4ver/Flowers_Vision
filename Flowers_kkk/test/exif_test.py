#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import exifread
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time


def convert_to_decimal(coord, ref):
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

def get_address_from_coordinates(lat, lon, max_retries=3):
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
                address = location.raw.get('address', {})
                return address
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

def format_address(address):
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

def main(image):
    # 检查文件是否存在
    if not os.path.exists(image):
        print(f"错误: 文件 '{image}' 不存在")
        return
        
    try:
        with open(image, 'rb') as f:
            exif = exifread.process_file(f)

            # 设备信息（添加错误处理）
            make = exif.get('Image Make', '未知')
            model = exif.get('Image Model', '未知')
            print('相机品牌:', make)
            print('相机型号:', model)

            # 相片信息（添加错误处理）
            datetime = exif.get('Image DateTime', '未知')
            length = exif.get('EXIF ExifImageLength', '未知')
            width = exif.get('EXIF ExifImageWidth', '未知')
            print('拍摄时间:', datetime)
            print('图片大小:', length, '*', width)

            # 位置信息（添加错误处理）
            if all(key in exif for key in ['GPS GPSLongitudeRef', 'GPS GPSLongitude', 
                                         'GPS GPSLatitudeRef', 'GPS GPSLatitude']):
                # 获取原始的经纬度信息
                lon_ref = exif['GPS GPSLongitudeRef'].printable
                lon = exif['GPS GPSLongitude']
                lat_ref = exif['GPS GPSLatitudeRef'].printable
                lat = exif['GPS GPSLatitude']
                
                # 打印原始经纬度
                print(f'原始经纬度: {lat_ref}{lat}, {lon_ref}{lon}')
                
                try:
                    # 转换为十进制格式
                    dec_lat = convert_to_decimal(lat, lat_ref)
                    dec_lon = convert_to_decimal(lon, lon_ref)
                    print(f'十进制经纬度: {dec_lat:.6f}, {dec_lon:.6f}')
                    
                    # 尝试获取地址信息
                    print("正在获取地址信息...")
                    address_info = get_address_from_coordinates(dec_lat, dec_lon)
                    
                    if address_info:
                        # 打印完整地址
                        formatted_address = format_address(address_info)
                        print(f'地址信息: {formatted_address}')
                        
                        # 打印详细地址组件
                        print('详细地址组件:')
                        for key, value in address_info.items():
                            print(f"  {key}: {value}")
                    else:
                        print("无法获取地址信息")
                except Exception as e:
                    print(f"处理位置信息时出错: {e}")
            else:
                print('经纬度: 未找到GPS信息')
    except Exception as e:
        print(f"读取文件时出错: {e}")


if __name__ == '__main__':
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                'example', 'Vivo.jpg')
    print(f"尝试读取文件: {image_path}")
    main(image_path)
