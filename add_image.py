import os
import sqlite3
from datetime import datetime

# def save_to_filesystem(shirt_id, image_file):
#     """将图片保存到文件系统并更新数据库"""
#     # 1. 生成存储路径
#     year = datetime.now().strftime("%Y")
#     month = datetime.now().strftime("%m")
#     base_dir = os.path.join("uploads", "shirts", year, month)
#     os.makedirs(base_dir, exist_ok=True)
    
#     # 2. 生成唯一文件名（避免重名）
#     ext = os.path.splitext(image_file.filename)[1].lower()
#     filename = f"shirt_{shirt_id}_{os.getpid()}_{datetime.now().microsecond}{ext}"
#     full_path = os.path.join(base_dir, filename)
    
#     # 3. 保存图片到文件系统
#     with open(full_path, "wb") as f:
#         f.write(image_file.read())
    
#     # 4. 计算哈希值和MIME类型
#     image_hash = calculate_hash(full_path)
#     mime_type = get_mime_type(ext)
    
#     # 5. 更新数据库
#     update_database(shirt_id, full_path, image_hash, mime_type)
    
#     return full_path



def save_to_filesystem(shirt_id, image_file, original_filename):
    """将图片保存到文件系统并更新数据库"""
    # 1. 生成存储路径
    year = datetime.now().strftime("%Y")
    month = datetime.now().strftime("%m")
    base_dir = os.path.join("uploads", "shirts", year, month)
    os.makedirs(base_dir, exist_ok=True)

    # 2. 生成唯一文件名（避免重名）
    ext = os.path.splitext(original_filename)[1].lower()
    filename = f"shirt_{shirt_id}_{os.getpid()}_{datetime.now().microsecond}{ext}"
    full_path = os.path.join(base_dir, filename)

    # 3. 保存图片到文件系统
    with open(full_path, "wb") as f:
        f.write(image_file.read())

    # 4. 计算哈希值和MIME类型
    image_hash = calculate_hash(full_path)
    mime_type = get_mime_type(ext)

    # 5. 更新数据库
    update_database(shirt_id, full_path, image_hash, mime_type)

    return full_path

def calculate_hash(file_path):
    """计算文件MD5哈希"""
    import hashlib
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()

def get_mime_type(ext):
    """获取文件MIME类型"""
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif"
    }
    return mime_map.get(ext.lower(), "image/unknown")

def update_database(shirt_id, path, hash_val, mime):
    """更新SQLite数据库"""
    conn = sqlite3.connect("clothing_db.sqlite")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clothing_items SET image_path=?, image_hash=?, image_mime=? WHERE id=?",
        (path, hash_val, mime, shirt_id)
    )
    conn.commit()
    conn.close()
    
    
    
if __name__ == "__main__":
    
    shirt_id = 5
    file_path = "test.jpg"
    with open(file_path, 'rb') as image_file:
        full_path = save_to_filesystem(shirt_id, image_file, file_path)
    print(f"Image saved to {full_path}")
    # save_to_filesystem()