from pathlib import Path


PROJECT_NAME = "Digital Commerce Intelligence Hub"

BASE_DIR = Path(__file__).resolve().parent
MANUAL_INPUT_PATH = BASE_DIR / "manual_sources" / "daily_input.md"
HTML_OUTPUT_PATH = BASE_DIR / "output" / "index.html"
PREVIEW_OUTPUT_PATH = BASE_DIR / "output" / "preview" / "index.html"
PREVIEW_DATA_PATH = BASE_DIR / "output" / "preview" / "data.json"

MAX_ITEMS_FOR_GEMINI = 28
RSS_ITEMS_PER_FEED = 8
GOOGLE_NEWS_ITEMS_PER_QUERY = 5

SECTION_ORDER = ["platform", "ai", "sports", "retail"]
SEARCH_WINDOWS_DAYS = [3, 7, 14]
MIN_SECTION_CANDIDATES = {
    "platform": 4,
    "ai": 4,
    "sports": 3,
    "retail": 3,
}
MAX_SECTION_CANDIDATES = {
    "platform": 12,
    "ai": 12,
    "sports": 10,
    "retail": 10,
}

FEEDS = [
    {"source": "Retail Dive", "url": "https://www.retaildive.com/feeds/news/", "domain": "retail"},
    {"source": "Retail TouchPoints", "url": "https://www.retailtouchpoints.com/feed/", "domain": "retail"},
    {"source": "Modern Retail", "url": "https://www.modernretail.co/feed/", "domain": "retail"},
    {"source": "SportsPro", "url": "https://www.sportspro.com/feed/", "domain": "sports"},
    {"source": "SportBusiness", "url": "https://www.sportbusiness.com/feed/", "domain": "sports"},
    {"source": "Front Office Sports", "url": "https://frontofficesports.com/feed/", "domain": "sports"},
    {"source": "WWD Business", "url": "https://wwd.com/business-news/feed/", "domain": "sports"},
    {"source": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "domain": "ai"},
]

SEARCH_QUERIES = {
    "platform": [
        "Alibaba digital commerce platform capability", "Taobao merchant tools recommendation", "Tmall membership ecommerce", "1688 digital commerce supply chain", "Cainiao logistics fulfillment",
        "JD retail strategy logistics fulfillment", "JD supply chain commerce", "JD Health new business", "JD merchant tools", "JD retail membership",
        "Douyin ecommerce AI recommendation", "ByteDance ecommerce platform", "Pinduoduo merchant tools strategy", "Meituan instant retail logistics", "WeChat ecommerce mini program",
        "Xiaohongshu commerce search", "Kuaishou ecommerce merchants", "阿里 电商 平台能力", "淘宝 商家工具 推荐", "天猫 会员 电商",
        "1688 供应链 平台", "菜鸟 物流 履约", "京东 零售 战略", "京东 供应链 履约", "京东 物流 开放能力",
        "京东健康 新业务", "抖音 电商 AI 推荐", "字节 电商 平台", "拼多多 商家工具", "美团 即时零售 履约",
        "微信 电商 小程序", "小红书 电商 搜索", "快手 电商 商家",
    ],
    "ai": [
        "AI in retail business adoption", "AI shopping assistant commerce", "AI customer service retail", "AI search ecommerce", "AI recommendation retail",
        "AI agent workflow enterprise", "AI commerce operations", "AI marketing operations retail", "AI productivity enterprise workflow", "model routing enterprise AI",
        "AI product understanding ecommerce", "multimodal AI product search", "AI content generation product descriptions", "AI supply chain optimization retail", "AI inventory forecasting retail",
        "AI price optimization retail", "AI store operations", "business AI adoption retail", "enterprise AI tools operations", "AI workflow automation customer service",
        "OpenAI agent business workflow", "Google Gemini enterprise AI workflow", "Anthropic Claude customer service agent", "DeepSeek enterprise AI adoption", "Microsoft Copilot business workflow",
        "Apple Intelligence productivity workflow", "NVIDIA retail AI operations", "Hugging Face enterprise AI", "AI 零售 业务应用", "AI 购物助手 电商",
        "AI 客服 零售", "AI Search 电商", "AI 推荐 零售", "AI Agent 企业流程", "AI 商业运营", "AI 营销自动化",
        "AI 商品理解 电商", "多模态 商品搜索", "AI 生成 商品内容", "AI 供应链优化", "AI 库存预测", "AI 门店运营", "企业级 AI 工具",
    ],
    "sports": [
        "Decathlon ecommerce digital strategy", "Decathlon store expansion retail", "Nike ecommerce financial results", "Nike membership digital", "Adidas ecommerce strategy",
        "Lululemon membership store expansion", "Anta financial results digital strategy", "Li Ning ecommerce consumer trend", "On Running retail expansion", "Salomon outdoor retail",
        "Columbia sportswear ecommerce", "Arc'teryx retail strategy", "outdoor consumer trends report", "sports retail industry report", "fitness wearable retail",
        "running consumer trend sports retail", "cycling retail consumer trend", "camping outdoor retail trend", "sports technology wearable", "sports equipment ecommerce",
        "sports brand app membership community", "outdoor brand content commerce", "sports brand omnichannel store experience", "sports brand product experience young consumers",
        "迪卡侬 电商 数字化", "迪卡侬 门店 扩张", "耐克 电商 财报", "阿迪达斯 电商 战略", "Lululemon 会员 门店",
        "安踏 财报 数字化", "李宁 电商 消费趋势", "户外 消费趋势 报告", "运动零售 行业报告", "运动科技 可穿戴",
        "运动品牌 会员 社群", "户外品牌 内容电商", "运动品牌 全渠道 门店体验", "运动品牌 商品体验 年轻消费者",
    ],
    "retail": [
        "Walmart retail innovation supply chain", "Walmart AI shopping store operations", "Costco membership digital retail", "Sam's Club digital store checkout", "Amazon retail innovation shopping AI",
        "Target omnichannel inventory", "Zara digital store RFID", "Uniqlo RFID inventory", "IKEA omnichannel fulfillment", "MUJI digital retail",
        "Aldi retail automation checkout", "Lidl digital retail operations", "Sephora store digitalization", "Hema retail innovation supply chain", "Inditex RFID retail",
        "retail technology RFID inventory", "retail supply chain innovation", "store digitalization retail operations", "self checkout retail innovation", "retail omnichannel membership",
        "retail fulfillment inventory sharing", "retail returns app", "grocery fresh management retail", "store automation retail", "consumer behavior retail innovation",
        "retail app loyalty personalization", "retail content commerce conversion", "retail search recommendation customer experience", "retail media closed-loop membership search conversion",
        "零售 App 会员 个性化", "零售 内容电商 转化", "零售 搜索 推荐 用户体验", "零售 闭环数据 会员 转化",
    ],
}

EXPANDED_SEARCH_QUERIES = {
    "platform": [
        "China ecommerce platform strategy", "China digital commerce merchant tools", "China ecommerce logistics fulfillment",
        "China instant retail platform", "China platform AI ecommerce", "国内 电商 平台 战略", "即时零售 平台 能力",
    ],
    "ai": [
        "business AI adoption retail ecommerce", "enterprise AI customer service workflow", "AI agents business operations",
        "AI search shopping customer experience", "AI automation marketing operations", "AI productivity enterprise adoption",
        "企业 AI 应用 零售 电商", "AI 客服 购物 搜索",
    ],
    "sports": [
        "sports outdoor retail industry trends", "sports brand financial results ecommerce", "outdoor retail consumer trend",
        "sports retail store expansion digital", "fitness wearable consumer trend", "运动户外 零售 趋势", "运动品牌 财报 电商",
        "sports brand community app commerce", "outdoor lifestyle content commerce", "运动品牌 社群 App 电商", "户外生活方式 内容转化",
    ],
    "retail": [
        "retail innovation store operations", "retail technology inventory supply chain", "omnichannel retail membership",
        "store digitalization self checkout", "retail consumer behavior innovation", "零售 创新 供应链 门店", "全渠道 会员 门店数字化",
        "retail loyalty app personalization conversion", "retail closed-loop data commerce conversion", "零售 会员 App 个性化 转化", "零售 闭环数据 电商转化",
    ],
}

# Backward-compatible alias for older imports.
GOOGLE_NEWS_QUERIES = SEARCH_QUERIES

COMMON_EXCLUDED_KEYWORDS = [
    "retail media", "retail media network", "ad network", "ad tech", "ctv", "ctv advertising", "programmatic",
    "shopper marketing", "media monetization", "advertising roi", "media budget", "ad spend", "brand advertising", "marketing campaign",
    "advertising revenue", "media revenue", "ad revenue",
]

COMMON_LOW_VALUE_KEYWORDS = [
    "new sneaker", "new shoe", "shoe release", "capsule collection", "limited edition", "celebrity", "ambassador",
    "endorsement", "collaboration", "sponsorship", "sponsored", "sale event", "discount", "promotion", "promo", "campaign",
    "明星", "代言", "联名", "新鞋", "折扣", "促销", "赞助", "赛事赞助", "销售战报",
]

COMMERCE_RELEVANCE_KEYWORDS = [
    "ecommerce", "commerce", "membership", "loyalty", "app", "mini program", "community", "content commerce",
    "social commerce", "conversion", "search", "recommendation", "personalization", "customer experience",
    "store experience", "store traffic", "omnichannel", "fulfillment", "delivery", "supply chain", "inventory",
    "product experience", "consumer segment", "gen z", "younger consumers", "direct commerce", "owned channel",
    "电商", "会员", "忠诚度", "App", "小程序", "社群", "内容电商", "内容转化", "种草", "转化", "搜索", "推荐",
    "个性化", "用户体验", "门店体验", "门店引流", "线上线下", "全渠道", "履约", "配送", "供应链", "库存",
    "商品体验", "新人群", "年轻消费者", "品牌直营", "自有渠道",
]

FILTER_PROFILES = {
    "platform": {
        "include_any": [
            "alibaba", "taobao", "tmall", "1688", "cainiao", "jd", "jingdong", "jd logistics", "jd health", "douyin", "bytedance",
            "pinduoduo", "pdd", "meituan", "wechat", "xiaohongshu", "kuaishou", "阿里", "淘宝", "天猫", "菜鸟", "京东",
            "京东物流", "京东健康", "抖音", "字节", "拼多多", "美团", "微信", "小红书", "快手",
        ],
        "require_any": [
            "new business", "business unit", "platform strategy", "merchant tools", "search", "recommendation", "membership", "fulfillment",
            "supply chain", "logistics", "instant retail", "local life", "open capability", "marketplace", "ecommerce", "ai",
            "新业务", "新事业部", "平台战略", "商家工具", "搜索", "推荐", "会员", "履约", "供应链", "物流", "即时零售", "本地生活", "开放能力", "电商",
        ],
        "exclude_any": COMMON_LOW_VALUE_KEYWORDS + ["brand campaign", "ordinary promotion", "单纯促销", "普通广告"],
        "override_any": ["platform capability", "advertising tools", "merchant tools", "platform strategy", "supply chain", "fulfillment", "logistics", "ecommerce", "search", "recommendation", "membership", "平台能力", "广告工具", "平台战略", "商家工具", "供应链", "履约", "物流", "搜索", "推荐", "会员"],
    },
    "ai": {
        "include_any": [
            "ai search", "ai shopping", "agent", "customer service", "product understanding", "multimodal", "content generation", "recommendation",
            "membership", "operations automation", "supply chain", "inventory forecasting", "price optimization", "store operations", "enterprise ai",
            "copilot", "openai", "gemini", "claude", "deepseek", "doubao", "seed", "qwen", "hunyuan", "kimi", "manus", "nvidia", "hugging face",
            "智能客服", "商品理解", "多模态", "内容生成", "推荐", "会员运营", "自动化运营", "供应链优化", "库存预测", "价格优化", "门店运营", "企业级 AI", "办公协作",
        ],
        "require_any": [
            "ecommerce", "retail", "shopping", "customer service", "user experience", "operations", "workflow", "product", "recommendation", "supply chain",
            "inventory", "store", "enterprise", "office", "developer", "coding", "电商", "零售", "购物", "客服", "用户体验", "运营", "流程", "商品", "推荐", "供应链", "库存", "门店", "企业", "办公", "开发效率",
        ],
        "exclude_any": COMMON_EXCLUDED_KEYWORDS + [
            "benchmark", "leaderboard", "parameter", "parameters", "trillion parameters", "algorithm", "paper", "research paper", "training method", "quantization",
            "gpu memory", "inference framework", "chip specs", "model release", "new model", "gemini 3", "claude 5", "gpt-6", "qwen 4", "deepseek v4",
            "模型排名", "排行榜", "参数规模", "纯算法", "论文", "训练方法", "量化算法", "显存", "推理框架", "芯片参数", "模型发布", "新模型",
        ],
        "override_any": [
            "shopping", "customer service", "product understanding", "recommendation", "workflow", "operations", "supply chain", "inventory", "store", "enterprise", "retail", "ecommerce", "客服", "商品理解", "推荐", "运营", "供应链", "库存", "门店", "企业", "零售", "电商",
        ],
    },
    "sports": {
        "include_any": [
            "decathlon", "nike", "adidas", "lululemon", "puma", "under armour", "on", "hoka", "salomon", "arc'teryx", "patagonia", "columbia", "the north face", "anta", "li-ning", "kailas", "descente", "fila", "garmin", "fitness", "running", "outdoor", "sports retail",
            "迪卡侬", "耐克", "阿迪达斯", "安踏", "李宁", "户外", "运动品牌", "体育零售",
        ],
        "require_any": [
            "ecommerce", "direct commerce", "membership", "digital", "store innovation", "supply chain", "fulfillment", "product experience", "search", "recommendation", "consumer trend", "organization", "strategy", "omnichannel", "new retail", "store expansion", "product launch", "financial results", "industry report", "wearable", "sports technology",
            "电商", "会员", "数字化", "门店创新", "供应链", "履约", "商品体验", "搜索", "推荐", "消费趋势", "组织战略", "新零售", "门店", "新品", "财报", "行业报告", "可穿戴", "运动科技",
        ],
        "exclude_any": COMMON_EXCLUDED_KEYWORDS + ["celebrity", "ambassador", "endorsement", "collaboration", "sponsorship", "sponsored", "campaign", "明星", "代言", "联名", "赞助", "赛事赞助"],
        "override_any": ["ecommerce", "direct commerce", "membership", "digital", "supply chain", "fulfillment", "strategy", "omnichannel", "store expansion", "financial results", "industry report", "consumer trend", "电商", "会员", "数字化", "供应链", "履约", "战略", "门店", "财报", "行业报告", "消费趋势"] + COMMERCE_RELEVANCE_KEYWORDS,
    },
    "retail": {
        "include_any": [
            "walmart", "sam's club", "costco", "amazon", "target", "zara", "uniqlo", "ikea", "muji", "aldi", "lidl", "carrefour", "7-eleven", "hema", "inditex", "sephora",
        ],
        "require_any": [
            "omnichannel", "digital store", "membership", "supply chain", "fulfillment", "rfid", "self-checkout", "search", "recommendation", "ai shopping", "inventory sharing", "returns", "app", "ecommerce experience", "operations efficiency", "fresh management", "store automation",
            "全渠道", "门店数字化", "会员", "供应链", "履约", "自助结账", "搜索", "推荐", "库存共享", "退换货", "运营效率", "生鲜管理", "门店自动化",
        ],
        "exclude_any": COMMON_LOW_VALUE_KEYWORDS + COMMON_EXCLUDED_KEYWORDS,
        "override_any": ["omnichannel", "digital store", "supply chain", "fulfillment", "rfid", "self-checkout", "self checkout", "inventory", "app", "operations", "全渠道", "供应链", "履约", "库存", "运营效率"] + COMMERCE_RELEVANCE_KEYWORDS,
    },
}
