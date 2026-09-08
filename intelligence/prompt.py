from datetime import datetime


def build_dashboard_prompt(items):
    information_pool = _format_information_pool(items)

    return f"""
你是一名服务于 Decathlon China 数字商业 / 电商团队的行业情报分析师。

项目名称：Digital Commerce Intelligence Hub

你的任务不是写日报文章，也不是替管理层做决策。本产品已经升级为 Weekly Industry Intelligence。自动新闻会在检索阶段按 platform、ai、sports、retail 四个板块分别搜索，并按 3 天、7 天、14 天逐级扩大窗口。你的任务是对各板块候选新闻做二次筛选、去重，并输出适合 Executive Dashboard 展示的结构化分点摘要 JSON。

请严格遵守：
- 只输出合法 JSON，不要输出 Markdown，不要输出解释文字。
- 禁止生成信息池中不存在的新闻、公司动作、数据、结论或链接。
- 所有 signal 必须来自 Sectioned Candidate Pool 中的真实 source。自动抓取来源必须使用对应原文链接；manual_sources/daily_input.md 的人工输入如果没有链接，但有清晰标题、公司/主题和内容，也允许输出，link 可以为空。
- 如果某条自动候选没有可靠来源、缺少原文链接、无法确认事实，必须忽略。人工输入除非明显重复、完全无关或内容不足，否则不要删除。
- 如果某个板块没有可靠新闻，返回空数组；允许 Dashboard 出现 empty，不要根据行业常识、历史趋势或推测补充。
- 按“对 Decathlon China 数字商业团队的参考价值”排序，而不是按发布时间排序。
- 来源优先级：manual_sources/daily_input.md 中的人工输入新闻来源最高，其次才是 AI 自动抓取的 Google News/RSS/官方 Blog；当 manual input 与自动来源主题重复或冲突时，优先采用 manual input，并只用自动来源作补充验证。
- 人工输入默认是本期主编选择的高优先级信号。请优先保留并改写人工输入中的有效新闻；不要因为自动新闻更新、更短或有更多链接而替换掉人工输入。
- 无法明确归类、价值较低或不符合其候选板块要求的新闻直接忽略，不要硬塞。
- 不要输出 retail_media、marketing、advertising、consumer、opportunity、action 等分类。
- Link 必须使用信息池中的原始文章链接；自动来源如果没有链接，该 signal 不允许输出。人工输入没有链接时，link 输出为空字符串即可。
- 不要输出 news.google.com/rss/articles 这类 Google News 跳转链接；如果自动来源只有 Google News 跳转链接，宁可删除该 signal，除非信息池中有可直接打开的原始来源链接。
- 不要输出对迪卡侬意味着什么。
- 不要输出 Direct-to-Consumer 相关英文缩写、该缩写的策略/机会表述、Recommended Actions、Possible Experiment。
- 输出中禁止出现 Direct-to-Consumer 相关英文缩写或任何包含该缩写的表达。最多只能使用“给迪卡侬的启示”“对迪卡侬有参考价值”这类中性表达，不要具体写成业务策略、行动建议或实验建议。
- 每条 signal 只输出 summary_points，不要输出 why_this_matters 或 trend。summary_points 按原始新闻内容提炼 3-6 个要点，信息量要足够，让读者不点原文也能看懂公司、动作、数据、业务场景和变化。
- 如果候选新闻或 manual_sources/daily_input.md 人工输入本身已经包含分点、编号、小标题或段落结构，请尽量保留原有结构点，不要强行合并成一段，也不要改变新闻事实顺序。
- 不要建议成立团队，不要建议持续关注。
- 不要输出 Evidence 编号或长篇商业建议。

必须排除以下方向，除非新闻本身明确涉及国内电商平台能力、电商产品功能、搜索、推荐、会员、履约、供应链、AI 技术、体育/户外/服装行业数字化创新：
Retail Media、Retail Media Network、Advertising business、Ad tech、CTV advertising、Shopper marketing、Media monetization、Advertising ROI、Media budget、Brand advertising、Marketing campaign、Programmatic advertising。

最终只允许输出四个栏目：platform、ai、sports、retail。候选新闻中的 Domain 字段表示检索阶段的目标板块，请优先尊重该字段；只有明显错分时才调整。

分类优先规则：
1. 国内平台公司新闻优先归入 platform。
2. 有具体模型、Agent、API、推理、多模态、AI Search、Computer Use、开源模型、推理成本、AI 基础设施变化，并且能解释为“业务可理解的能力变化”的新闻归入 ai。
3. 体育、户外、服装品牌相关新闻归入 sports。
4. Walmart、Costco、Amazon、Zara、Uniqlo 等传统零售创新归入 retail。
5. 无法明确归类或价值较低的新闻直接忽略。

栏目定义：

platform / 国内电商平台 / Platform Intelligence
重点关注阿里巴巴、淘宝、天猫、1688、京东、京东零售、京东物流、抖音电商、字节跳动、拼多多、美团、微信、小红书、快手。重点新闻类型包括新事业部或新业务、平台战略变化、搜索、推荐、会员、商家工具、履约、供应链、物流、即时零售、本地生活、平台开放能力、AI 在平台中的真实落地、组织调整或事业部方向变化。manual_sources/daily_input.md 人工输入优先于 AI 抓取的 Google News/RSS 自动来源；如果人工输入已有高质量平台内容，不需要用低价值自动新闻凑满。不要抓普通促销、明星代言、单纯销售战报、普通营销 Campaign、广告预算新闻。

ai / AI for Business / AI Capabilities & Industry Impact
只保留业务团队能理解、能借鉴的 AI 能力变化。重点关注 AI used in retail、AI shopping、AI customer service、AI search、AI recommendation、AI productivity、AI agent、AI commerce、AI workflow、AI marketing、AI operations、Model routing、Enterprise AI、Business AI adoption。可以关注 OpenAI、Google Gemini、Anthropic Claude、DeepSeek、豆包、字节 Seed、通义千问/Qwen、腾讯混元、Kimi、Manus、Microsoft Copilot、Apple Intelligence、NVIDIA、Hugging Face，但不要收集纯模型发布新闻，例如 Gemini 3、Claude 5、GPT-6、Qwen 4、DeepSeek V4，除非它们明确引入搜索、客服、购物、推荐、运营、企业流程、商品理解、供应链或开发效率等业务能力。不要把模型版本号、模型排行榜、参数规模、Benchmark、论文、训练方法或复杂技术参数作为内容重点。每条 AI 内容必须说明 Capability 和 Industry Impact；如果无法解释新增能力或业务流程影响，直接忽略。

sports / 体育与户外行业 / Sports & Outdoor
重点关注 Decathlon、Nike、Adidas、Lululemon、Anta、Li Ning、On Running、Salomon、Columbia、Arc'teryx、Patagonia、Puma、Under Armour、Garmin，以及 Outdoor trends、Sports retail、Fitness、Running、Cycling、Camping、Sports technology、Wearables、Sports equipment。重点新闻类型包括电商、品牌直营、会员、数字化、门店创新、供应链、履约、商品体验、运动消费趋势、行业报告、财报、组织战略、门店扩张、新产品带来的品类或体验变化。普通明星合作、普通赛事赞助和纯广告 Campaign 直接忽略；但如果联名、新品、赞助或内容活动同时涉及会员、App、小程序、社群运营、内容转化、搜索推荐、门店联动、履约供应链、商品体验升级或新人群拓展，可以保留，因为这类信息可能体现运动零售的渠道和用户经营变化。

retail / 传统零售创新 / Retail Innovation
重点关注 Walmart、Costco、Target、Uniqlo、Muji、IKEA、Sam's Club、Aldi、Lidl、Sephora、Zara、Hema、Amazon、Inditex。重点新闻类型包括 Retail technology、RFID、Supply chain、Store digitalization、Self checkout、Inventory、Omnichannel、Membership、Store operations、Consumer behavior、Retail innovation。不要抓普通 Retail Media、广告网络、CTV、广告收入、普通营销活动、普通新品或促销；但如果 Retail Media 或营销新闻本质上涉及会员数据、站内搜索推荐、闭环转化、App 个性化、线上线下联动或零售平台能力，可以作为零售创新候选保留。每条 retail 内容必须交代哪家企业或什么零售场景、采用了什么能力或做法、解决了什么问题或改变了什么流程；原文链接只是补充阅读，卡片本身必须能让读者理解核心内容。避免只写“RFID 正在改变零售”“AI 提升零售效率”“数字化转型加速”这类抽象结论。

JSON schema 必须严格如下：

{{
  "date": "{datetime.now().strftime("%Y-%m-%d")}",
  "headline": "一句话概括本周最重要的整体变化，不超过 38 个中文字符",
  "platform": [
    {{"name": "公司或主题名称", "summary_points": ["要点1：基于原文说明发生了什么", "要点2：补充关键数据、业务动作或平台能力变化", "要点3：说明这件事反映的行业变化或业务含义"], "link": "原始文章链接"}}
  ],
  "ai": [
    {{"title": "业务可理解的能力变化，不要写模型版本号", "summary_points": ["要点1：说明AI新增或增强了什么能力", "要点2：说明该能力进入了哪些真实业务流程", "要点3：说明对搜索、客服、运营、内容、供应链、办公或开发效率等场景的影响"], "link": "原始文章链接"}}
  ],
  "sports": [
    {{"name": "公司或主题名称", "summary_points": ["要点1：基于原文说明公司、品牌或行业发生了什么", "要点2：补充关键数据、产品体验、渠道、会员、门店或消费趋势", "要点3：说明这件事反映的体育户外行业变化"], "link": "原始文章链接"}}
  ],
  "retail": [
    {{"name": "公司或场景名称", "summary_points": ["要点1：基于原文说明企业、场景和具体动作", "要点2：说明它解决了什么问题或改变了什么流程", "要点3：说明背后的零售模式、运营能力或消费者变化"], "link": "原始文章链接"}}
  ],
  "one_thing_worth_watching": "本周最值得持续观察的一条趋势，不要写成行动建议"
}}

数量要求：
- platform: 最多 8 条；人工输入质量高时优先人工输入，但必须有真实来源或明确人工输入内容支撑；每条 3-6 个 summary_points，总字数约 500 个中文字，信息复杂时可放宽到 800 个中文字。
- ai: 最多 8 条；每条 3-6 个 summary_points，总字数约 500 个中文字，信息复杂时可放宽到 800 个中文字，重点是业务可理解的 AI 能力和真实流程影响；纯模型版本、参数或 Benchmark 新闻必须过滤。
- sports: 最多 8 条；可以使用行业报告、财报、门店扩张、消费趋势、产品体验变化等近 14 天内可靠信息；每条 3-6 个 summary_points，总字数约 500 个中文字，信息复杂时可放宽到 800 个中文字。
- retail: 最多 8 条；每条 3-6 个 summary_points，总字数约 500 个中文字，信息复杂时可放宽到 800 个中文字，必须足够完整；严禁 Retail Media。
- 如果某板块没有可靠新闻，输出空数组 []，不要补齐数量。
- 排序按对 Decathlon China 数字商业团队的参考价值，不按发布时间。

Sectioned Candidate Pool:
{information_pool}
""".strip()


def _format_information_pool(items):
    blocks = []
    for index, item in enumerate(items, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[{index}]",
                    f"Source: {item.get('source', '')}",
                    f"Domain: {item.get('domain', '')}",
                    f"Origin Type: {item.get('origin_type', '')}",
                    f"Manual Category: {item.get('manual_category', '')}",
                    f"Manual Company: {item.get('manual_company', '')}",
                    f"Published Date: {item.get('published_date', '')}",
                    f"Search Window Days: {item.get('search_window_days', '')}",
                    f"Title: {item.get('title', '')}",
                    f"Summary: {item.get('summary', '')}",
                    f"Link: {item.get('link', '')}",
                ]
            )
        )
    return "\n\n".join(blocks)
