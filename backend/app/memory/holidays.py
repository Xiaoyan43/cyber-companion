from __future__ import annotations

from datetime import date, timedelta

# Gregorian-fixed holidays — valid every year.
_FIXED: dict[tuple[int, int], str] = {
    (1, 1): "元旦",
    (2, 6): "怀唐伊日（新西兰）",
    (3, 8): "妇女节",
    (4, 25): "澳新军团纪念日（新西兰）",
    (5, 1): "劳动节",
    (5, 4): "青年节",
    (6, 1): "儿童节",
    (7, 1): "建党节",
    (8, 1): "建军节",
    (10, 1): "国庆节",
    (12, 25): "圣诞节",
    (12, 26): "节礼日（新西兰）",
}

# Year-specific holidays: lunar-calendar dates + variable Gregorian (Easter, etc.).
# Add the next year's block before each year rollover.
_LUNAR: dict[int, dict[tuple[int, int], str]] = {
    2026: {
        (1, 2): "新年假期（新西兰）",
        (2, 17): "除夕",
        (2, 18): "春节",
        (3, 5): "元宵节",
        (4, 3): "耶稣受难日（新西兰）",
        (4, 4): "清明节",
        (4, 6): "复活节（新西兰）",
        (5, 1): "劳动节 / 儿童节前夕",
        (6, 1): "儿童节 / 国王诞辰（新西兰）",
        (6, 22): "端午节",
        (7, 10): "马塔里基（新西兰）",
        (8, 29): "七夕",
        (9, 25): "中秋节",
        (10, 22): "重阳节",
        (10, 26): "劳工节（新西兰）",
        (12, 22): "冬至",
    },
}


def get_holiday_window(
    today: date,
    before_days: int = 3,
    after_days: int = 7,
) -> list[tuple[int, str]]:
    """Return holidays within [today - before_days, today + after_days].

    Each entry is (delta_days, holiday_name) where delta_days is negative
    for past holidays, 0 for today, and positive for upcoming ones.
    """
    results: list[tuple[int, str]] = []
    for delta in range(-before_days, after_days + 1):
        d = today + timedelta(days=delta)
        key = (d.month, d.day)
        name = _LUNAR.get(d.year, {}).get(key) or _FIXED.get(key)
        if name:
            results.append((delta, name))
    return results
