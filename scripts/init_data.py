"""初始化测试舆情数据"""
import asyncio
import sys
sys.path.insert(0, '/app')

from datetime import datetime, timedelta
import random

from backend.memory.storage import db
from backend.models.schemas import SourceType, SentimentType


async def init_sample_data():
    """初始化示例数据"""
    await db.init()

    sample_news = [
        {
            "title": "某科技公司发布新一代AI产品，引发行业关注",
            "content": "近日，某知名科技公司正式发布了其新一代人工智能产品，该产品在自然语言处理、图像识别等领域取得了重大突破。业内人士认为，这将推动整个AI行业的发展。产品发布后，社交媒体上讨论热烈，多数用户表示期待体验新功能。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/1",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 24)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["AI", "人工智能", "科技", "产品发布"]
        },
        {
            "title": "新能源汽车销量持续增长，市场前景看好",
            "content": "根据最新数据显示，新能源汽车销量连续三个月保持增长态势。多家车企纷纷加大研发投入，推出更多智能化、电动化产品。分析师预测，未来五年新能源汽车市场将持续扩大。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/2",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 48)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["新能源汽车", "销量", "市场", "电动车"]
        },
        {
            "title": "某电商平台被曝存在假货问题，引发消费者担忧",
            "content": "近日有消费者投诉某知名电商平台存在售卖假货的问题，相关监管部门已介入调查。平台方回应称将加强商品审核机制，保障消费者权益。此事件在社交媒体上引发广泛讨论。",
            "source": SourceType.SOCIAL,
            "source_url": "https://example.com/social/1",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 12)),
            "sentiment": SentimentType.NEGATIVE,
            "keywords": ["电商", "假货", "消费者", "投诉"]
        },
        {
            "title": "全国多地迎来降温天气，市民需注意保暖",
            "content": "据气象部门预报，未来一周全国多地将迎来大幅降温，部分地区可能出现雨雪天气。专家提醒市民注意防寒保暖，出行注意安全。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/3",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 72)),
            "sentiment": SentimentType.NEUTRAL,
            "keywords": ["天气", "降温", "保暖", "气象"]
        },
        {
            "title": "教育改革新政策出台，减轻学生课业负担",
            "content": "教育部发布新政策，进一步规范校外培训机构，减轻学生课业负担。政策出台后，家长和社会各界反响不一，有人支持认为有利于学生身心健康发展，也有人担忧教育公平问题。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/4",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 96)),
            "sentiment": SentimentType.NEUTRAL,
            "keywords": ["教育", "政策", "学生", "减负"]
        },
        {
            "title": "某知名品牌发布限量款产品，引发抢购热潮",
            "content": "某国际知名品牌今日发布限量款联名产品，开售即被抢购一空。二手市场价格飙升，引发网友热议。品牌方表示将考虑追加生产。",
            "source": SourceType.SOCIAL,
            "source_url": "https://example.com/social/2",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 36)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["品牌", "限量", "抢购", "联名"]
        },
        {
            "title": "某地区发生交通事故，多车追尾致多人受伤",
            "content": "今日上午，某高速公路发生多车追尾事故，造成多人受伤。目前救援工作正在进行中，事故原因正在调查。警方提醒驾驶员保持安全车距。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/5",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 6)),
            "sentiment": SentimentType.NEGATIVE,
            "keywords": ["交通事故", "追尾", "受伤", "高速"]
        },
        {
            "title": "国产游戏海外走红，文化输出获好评",
            "content": "一款国产游戏近日在海外市场大获成功，登顶多国下载榜单。游戏融入大量中国传统文化元素，获得海外玩家好评。业内人士认为这是文化输出的成功案例。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/6",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 48)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["游戏", "国产", "海外", "文化输出"]
        },
        {
            "title": "某明星代言产品被质疑虚假宣传",
            "content": "某知名明星代言的保健品被消费者质疑存在虚假宣传问题，相关部门已介入调查。明星工作室发表声明称将配合调查，并对消费者负责。",
            "source": SourceType.SOCIAL,
            "source_url": "https://example.com/social/3",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 24)),
            "sentiment": SentimentType.NEGATIVE,
            "keywords": ["明星", "代言", "虚假宣传", "保健品"]
        },
        {
            "title": "城市地铁新线路正式开通运营",
            "content": "经过多年建设，某城市地铁新线路今日正式开通运营。新线路连接多个重要区域，将大大方便市民出行。开通首日客流量超过预期。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/7",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 60)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["地铁", "开通", "出行", "交通"]
        },
        {
            "title": "食品安全抽检结果公布，多家企业不合格",
            "content": "市场监管总局公布最新食品安全抽检结果，多家企业的产品被发现不合格。不合格项目涉及添加剂超标、微生物污染等。相关部门已责令企业整改。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/8",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 36)),
            "sentiment": SentimentType.NEGATIVE,
            "keywords": ["食品安全", "抽检", "不合格", "添加剂"]
        },
        {
            "title": "某互联网公司裁员消息引发关注",
            "content": "近日有消息称某大型互联网公司将进行大规模裁员，引发行业关注和员工担忧。公司方面尚未正式回应。分析人士认为这与行业整体环境变化有关。",
            "source": SourceType.SOCIAL,
            "source_url": "https://example.com/social/4",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 18)),
            "sentiment": SentimentType.NEGATIVE,
            "keywords": ["裁员", "互联网", "公司", "就业"]
        },
        {
            "title": "体育赛事精彩纷呈，国家队取得佳绩",
            "content": "在最近结束的国际体育赛事中，国家队表现出色，获得多枚奖牌。运动员们的精彩表现获得观众热烈掌声，为国争光。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/9",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 72)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["体育", "赛事", "国家队", "奖牌"]
        },
        {
            "title": "房价走势分析：多城市房价趋于稳定",
            "content": "根据最新数据显示，多个城市房价趋于稳定，部分城市出现小幅回调。专家分析认为，房地产调控政策效果显现，市场预期趋于理性。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/10",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 96)),
            "sentiment": SentimentType.NEUTRAL,
            "keywords": ["房价", "房地产", "市场", "调控"]
        },
        {
            "title": "环保新政实施，企业加速转型升级",
            "content": "随着新的环保政策正式实施，多家高污染企业开始加速转型升级，引进清洁生产技术。环保部门表示将加大执法力度，确保政策落地见效。",
            "source": SourceType.NEWS,
            "source_url": "https://example.com/news/11",
            "publish_time": datetime.now() - timedelta(hours=random.randint(1, 120)),
            "sentiment": SentimentType.POSITIVE,
            "keywords": ["环保", "政策", "转型", "企业"]
        }
    ]

    print("正在插入示例数据...")
    count = await db.batch_insert_yuqing(sample_news)
    print(f"成功插入 {count} 条示例数据")

    await db.close()
    print("初始化完成！")


if __name__ == "__main__":
    asyncio.run(init_sample_data())
