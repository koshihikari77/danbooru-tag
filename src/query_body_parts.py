#!/usr/bin/env python3
"""
body partsに属するアイテム数を調べる
"""

import sqlite3

def query_body_parts():
    conn = sqlite3.connect("data/danbooru_tags.db")
    cursor = conn.cursor()
    
    # body partsを含むパスを持つアイテム数
    cursor.execute("""
        SELECT COUNT(DISTINCT tag_id) 
        FROM tag_paths 
        WHERE path_value LIKE '%body parts%'
    """)
    count = cursor.fetchone()[0]
    print(f"body partsに属するアイテム数: {count}")
    
    # 詳細情報
    cursor.execute("""
        SELECT t.name, tc.classification_name, t.depth
        FROM tags t
        JOIN tag_classifications tc ON t.classification_id = tc.classification_id
        WHERE t.tag_id IN (
            SELECT DISTINCT tag_id 
            FROM tag_paths 
            WHERE path_value LIKE '%body parts%'
        )
        ORDER BY t.depth, t.name
        LIMIT 20
    """)
    
    print("\n最初の20件:")
    for row in cursor.fetchall():
        print(f"  {row[0]} (深度{row[2]}, {row[1]})")
    
    conn.close()

if __name__ == "__main__":
    query_body_parts()