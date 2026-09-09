from datetime import date, timedelta

PLATFORMS = ["douyin", "kuaishou", "xhs", "bili", "shipinhao"]
KEYS = ["浏览", "点赞", "转发", "收藏", "涨粉"]


def review(start: date, end: date, platform: str):
    if start > end or (end - start).days > 366:
        raise ValueError("请选择不超过 366 天的有效日期范围")
    selected = PLATFORMS if platform == "all" else [platform]
    if any(p not in PLATFORMS for p in selected):
        raise ValueError("不支持的平台")
    totals = [0] * len(KEYS)
    daily = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        values = [0] * len(KEYS)
        for p in selected:
            seed = day.toordinal() * (PLATFORMS.index(p) + 3)
            metrics = [180 + seed % 550, 15 + seed % 65, 2 + seed % 15, 4 + seed % 20, 1 + seed % 6]
            values = [a + b for a, b in zip(values, metrics)]
        totals = [a + b for a, b in zip(totals, values)]
        daily.append({
            "date": day.isoformat(),
            "views": values[0],
            "likes": values[1],
            "shares": values[2],
            "saves": values[3],
            "followers": values[4],
        })
    return {
        "mode": "demo", "start": start.isoformat(), "end": end.isoformat(), "platform": platform,
        "stats": [{"k": key, "v": f"{value:,}", "d": "演示数据"} for key, value in zip(KEYS, totals)],
        "daily": daily,
        "conclusion": "示例建议：测试「职场吐槽」与「轻知识」两类选题，分别记录完播率和关注转化，再决定下一轮内容配比。",
        "suggestion": "测试职场吐槽与轻知识两类选题，以完播率和关注转化比较效果。",
    }
