#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import exifread
import os


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
                lng = f"{exif['GPS GPSLongitudeRef']}{exif['GPS GPSLongitude']}"
                lat = f"{exif['GPS GPSLatitudeRef']}{exif['GPS GPSLatitude']}"
                print('经纬度:', lng, lat)
            else:
                print('经纬度: 未找到GPS信息')
    except Exception as e:
        print(f"读取文件时出错: {e}")


if __name__ == '__main__':
    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                'example', 'IMG_20251102_143056.jpg')
    print(f"尝试读取文件: {image_path}")
    main(image_path)
