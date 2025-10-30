# 1、传入手机照片
# 2、获取照片中的信息，地址和拍摄时间和地点
"""
pip install pillow geopy
1-获取照片中的EXIF数据
2-从EXIF数据中提取GPS信息
3-将GPS信息转换为经纬度坐标
4-根据经纬度坐标获取地址信息
"""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
import os


def get_exif_data(image_path):
    """
    从图像中提取EXIF数据
    """
    try:
        image = Image.open(image_path)
        
        # 方法1：使用_getexif()
        exif_data = image._getexif()
        
        # 方法2：如果方法1失败，尝试使用info属性
        if not exif_data:
            # 对于某些图片格式，尝试从info字典中获取
            if hasattr(image, 'info') and 'exif' in image.info:
                from PIL.ExifTags import TAGS
                import io
                # 尝试解析原始exif数据
                try:
                    exif_data = {}
                    for tag, value in TAGS.items():
                        if value in image.info:
                            exif_data[value] = image.info[value]
                except:
                    pass
        
        # 方法3：检查其他可能包含元数据的属性
        if not exif_data:
            exif_data = {}
            # 检查文件修改时间作为备选
            import datetime
            mtime = os.path.getmtime(image_path)
            exif_data['FileModifyDate'] = datetime.datetime.fromtimestamp(mtime).strftime('%Y:%m:%d %H:%M:%S')
            
            # 如果是PNG格式，可能有其他元数据
            if image.format == 'PNG' and hasattr(image, 'text'):
                for k, v in image.text.items():
                    exif_data[k] = v
        
        # 转换EXIF数据为可读格式
        exif = {}
        if exif_data:
            for tag, value in exif_data.items():
                # 处理不同类型的tag
                if isinstance(tag, int):
                    tag_name = TAGS.get(tag, f"UnknownTag_{tag}")
                else:
                    tag_name = str(tag)
                exif[tag_name] = value
        
        if not exif:
            return {"error": "该图片不包含EXIF信息", "debug": "尝试了多种方法仍无法提取EXIF数据"}
        
        return exif
    except Exception as e:
        return {"error": f"读取图片失败: {str(e)}", "debug": str(type(e))}


def get_gps_info(exif_data):
    """
    从EXIF数据中提取GPS信息
    """
    gps_info = {}
    
    if 'GPSInfo' in exif_data:
        gps_data = exif_data['GPSInfo']
        for tag, value in gps_data.items():
            tag_name = GPSTAGS.get(tag, tag)
            gps_info[tag_name] = value
    
    return gps_info


def convert_to_decimal(degrees, minutes, seconds, direction):
    """
    将度分秒格式的GPS坐标转换为十进制格式
    """
    decimal = degrees + minutes / 60 + seconds / 3600
    # 根据方向调整符号（南纬和西经为负值）
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal


def get_coordinates(gps_info):
    """
    从GPS信息中提取经纬度坐标
    """
    if not gps_info or 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
        return None
    
    # 获取纬度
    lat_deg, lat_min, lat_sec = gps_info['GPSLatitude']
    lat_dir = gps_info.get('GPSLatitudeRef', '')
    latitude = convert_to_decimal(lat_deg, lat_min, lat_sec, lat_dir)
    
    # 获取经度
    lon_deg, lon_min, lon_sec = gps_info['GPSLongitude']
    lon_dir = gps_info.get('GPSLongitudeRef', '')
    longitude = convert_to_decimal(lon_deg, lon_min, lon_sec, lon_dir)
    
    return (latitude, longitude)


def get_address_from_coordinates(latitude, longitude):
    """
    根据经纬度获取地址信息
    """
    try:
        geolocator = Nominatim(user_agent="photo_location_finder")
        location = geolocator.reverse((latitude, longitude), language='zh-CN')
        return location.address
    except Exception as e:
        return f"无法获取地址信息: {str(e)}"


def get_photo_info(image_path):
    """
    获取照片的完整信息，包括拍摄时间和地点
    """
    result = {}
    debug_info = []
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        return {"error": "文件不存在"}
    
    # 记录文件基本信息
    try:
        import os.path
        file_size = os.path.getsize(image_path) / 1024  # KB
        result["文件大小"] = f"{file_size:.2f} KB"
        
        # 尝试获取文件创建时间
        import datetime
        ctime = os.path.getctime(image_path)
        result["文件创建时间"] = datetime.datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        debug_info.append(f"获取文件信息时出错: {str(e)}")
    
    # 获取EXIF数据
    exif_data = get_exif_data(image_path)
    
    if "error" in exif_data:
        result["错误"] = exif_data["error"]
        if "debug" in exif_data:
            debug_info.append(exif_data["debug"])
    else:
        # 获取拍摄时间 - 尝试多种可能的时间戳字段
        time_fields = ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized', 'FileModifyDate']
        found_time = False
        for field in time_fields:
            if field in exif_data:
                result['拍摄时间'] = exif_data[field]
                found_time = True
                break
        
        if not found_time:
            result['拍摄时间'] = "未找到拍摄时间"
        
        # 获取GPS信息和地址
        gps_info = get_gps_info(exif_data)
        
        # 添加调试信息 - 显示是否找到GPSInfo
        if 'GPSInfo' in exif_data:
            debug_info.append("找到GPSInfo字段")
            if gps_info:
                debug_info.append(f"提取到的GPS信息数量: {len(gps_info)}")
                debug_info.append(f"GPS字段: {', '.join(gps_info.keys())}")
            else:
                debug_info.append("GPSInfo存在但无法提取数据")
        else:
            debug_info.append("未找到GPSInfo字段")
        
        coordinates = get_coordinates(gps_info)
        
        if coordinates:
            latitude, longitude = coordinates
            result['GPS坐标'] = f"纬度: {latitude:.6f}, 经度: {longitude:.6f}"
            try:
                result['地址'] = get_address_from_coordinates(latitude, longitude)
            except Exception as e:
                result['地址'] = f"地址解析失败: {str(e)}"
        else:
            result['GPS坐标'] = "未找到GPS信息"
            result['地址'] = "无法确定地址"
    
    # 添加调试信息
    if debug_info:
        result["调试信息"] = debug_info
    
    return result


# 示例使用方法
def main():
    # 请输入照片路径
    photo_path = input("请输入照片路径: ")
    
    # 获取照片信息
    info = get_photo_info(photo_path)
    
    # 输出结果
    print("\n照片信息:")
    for key, value in info.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
