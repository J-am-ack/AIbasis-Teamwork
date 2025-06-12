import sqlite3

def main():
    # 连接到SQLite数据库（如果不存在则创建）
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    
    try:
        # 创建示例表
        create_table(cursor)
        
        # 插入测试数据
        insert_data(cursor)
        conn.commit()
        print("初始数据：")
        print_all_data(cursor)
        
        # 示例1：修改数据
        update_data_example(cursor)
        conn.commit()
        print("\n修改后的数据：")
        print_all_data(cursor)
        
        # 示例2：删除数据
        delete_data_example(cursor)
        conn.commit()
        print("\n删除后的数据：")
        print_all_data(cursor)
        
        # 示例3：安全删除（逻辑删除）
        logical_delete_example(cursor)
        conn.commit()
        print("\n逻辑删除后的数据：")
        print_all_data_with_logical_deletion(cursor)
        
    except sqlite3.Error as e:
        print(f"SQLite错误: {e}")
        conn.rollback()  # 发生错误时回滚事务
    finally:
        conn.close()

def create_table(cursor):
    # 创建一个用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        email TEXT UNIQUE,
        is_deleted INTEGER DEFAULT 0
    )
    ''')

def insert_data(cursor):
    # 插入测试数据
    users = [
        (1, '张三', 25, 'zhangsan@example.com'),
        (2, '李四', 30, 'lisi@example.com'),
        (3, '王五', 22, 'wangwu@example.com'),
        (4, '赵六', 35, 'zhaoliu@example.com')
    ]
    cursor.executemany('INSERT INTO users (id, name, age, email) VALUES (?, ?, ?, ?)', users)

def update_data_example(cursor):
    # 示例1：修改单个字段
    cursor.execute("UPDATE users SET age = 26 WHERE id = 1")
    
    # 示例2：批量修改
    cursor.execute("UPDATE users SET age = age + 1 WHERE age < 30")
    
    # 示例3：同时修改多个字段
    cursor.execute("UPDATE users SET name = '李四（更新）', email = 'lisi_updated@example.com' WHERE id = 2")

def delete_data_example(cursor):
    # 示例1：删除单条记录
    cursor.execute("DELETE FROM users WHERE id = 3")
    
    # 示例2：删除满足条件的多条记录
    cursor.execute("DELETE FROM users WHERE age > 30")

def logical_delete_example(cursor):
    # 示例3：逻辑删除（标记为已删除，不实际移除数据）
    cursor.execute("UPDATE users SET is_deleted = 1 WHERE id = 2")

def print_all_data(cursor):
    # 查询并打印所有数据（不考虑逻辑删除）
    cursor.execute("SELECT id, name, age, email FROM users")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, 姓名: {row[1]}, 年龄: {row[2]}, 邮箱: {row[3]}")

def print_all_data_with_logical_deletion(cursor):
    # 查询并打印所有数据（排除逻辑删除的记录）
    cursor.execute("SELECT id, name, age, email, is_deleted FROM users WHERE is_deleted = 0")
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, 姓名: {row[1]}, 年龄: {row[2]}, 邮箱: {row[3]}, 是否删除: {row[4]}")

if __name__ == "__main__":
    main()
