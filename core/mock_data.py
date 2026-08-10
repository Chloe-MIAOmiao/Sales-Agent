"""预置 Demo 场景对话,用于 /analysis 页面一键加载测试。"""

SAMPLE_CASES = [
    {
        "key": "risk_chat",
        "label": "加载违规案例",
        "title": "案例 1:高风险违规(中文)",
        "text": (
            "客户:你好,我没有任何基础,学数据分析能学会吗?\n"
            "销售:放心,我们保证 100% 包学会,学完保底年薪 15 万,"
            "我们跟大厂有合作,毕业直接内推就业!\n"
            "客户:多少钱?\n"
            "销售:原价 5999,今天报名只要 2999,仅剩最后一个名额了,"
            "而且一旦付款概不退款。"
        ),
    },
    {
        "key": "english_lead",
        "label": "加载英文客户案例",
        "title": "案例 2:外企/跨国背景(英文跟进)",
        "text": (
            "Customer: Hi, I work in a multinational company and I'm interested "
            "in your Data Analytics & AI Tools Bootcamp. What tech stack will we "
            "cover, and do you have real case studies from previous students?\n"
            "Sales: Yes, we cover Python, SQL, Power BI and practical AI tools. "
            "All sessions are hands-on with real datasets. Would you like to "
            "attend a free trial class this week?"
        ),
    },
    {
        "key": "invalid_lead",
        "label": "加载垃圾线索案例",
        "title": "案例 3:无效/垃圾线索",
        "text": (
            "客户:在吗在吗在吗在吗\n"
            "客户:给我发一下你们的免费资料和课件\n"
            "客户:还有免费试听链接发我\n"
            "客户:免费的东西先来一份 哈哈哈"
        ),
    },
]

SAMPLE_CASES_BY_KEY = {case["key"]: case for case in SAMPLE_CASES}


def get_sample_case(key: str) -> dict | None:
    return SAMPLE_CASES_BY_KEY.get(key)
