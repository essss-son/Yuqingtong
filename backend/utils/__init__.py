"""工具函数"""
import re
from datetime import datetime
from typing import List, Any, Dict


def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ""

    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """提取关键词（简单实现）"""
    stop_words = {'的', '是', '在', '了', '和', '与', '或', '等', '这', '那', '有', '被', '把', '对', '为', '以'}

    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
    word_count = {}

    for word in words:
        if word not in stop_words:
            word_count[word] = word_count.get(word, 0) + 1

    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:top_n]]


def format_datetime(dt: datetime) -> str:
    """格式化日期时间"""
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def calculate_time_ago(dt: datetime) -> str:
    """计算时间差"""
    if not dt:
        return ""

    now = datetime.now()
    diff = now - dt

    seconds = int(diff.total_seconds())

    if seconds < 60:
        return f"{seconds}秒前"
    elif seconds < 3600:
        return f"{seconds // 60}分钟前"
    elif seconds < 86400:
        return f"{seconds // 3600}小时前"
    else:
        return f"{seconds // 86400}天前"
