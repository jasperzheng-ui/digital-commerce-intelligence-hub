"""Shared classification, citation numbering and dense text rendering."""
from collections import OrderedDict
from html import escape
import re
from urllib.parse import urlsplit


DOMAINS = {'platform_intelligence': 'platform', 'ai_technology': 'ai',
           'sports_outdoor': 'sports', 'retail_innovation': 'retail'}
SUBCATEGORIES = {
    'platform_intelligence': OrderedDict(alibaba='阿里生态', jd='京东生态', bytedance='字节生态',
                                        tencent='腾讯生态', meituan='美团生态', xiaohongshu='小红书生态'),
    'ai_technology': OrderedDict(business='业务应用', technology='技术进展'),
    'sports_outdoor': OrderedDict(domestic='国内', international='国外'),
    'retail_innovation': OrderedDict(domestic='国内', international='国外'),
}
# Topics are independent of company origin; old drafts may omit them.
TOPICS = {
    'ai_technology': OrderedDict(
        shopping_discovery='购物发现与转化',
        merchandising_operations='商品开发与经营',
        model_updates='主流模型更新',
        retrieval_content_interaction='搜索、内容与交互技术'),
    'sports_outdoor': OrderedDict(
        strategy='品牌布局与组织调整', product='商品创新与本土开发',
        channels_performance='门店与销售渠道', performance='经营表现与库存管理'),
    'retail_innovation': OrderedDict(
        product='商品开发与消费需求', stores='门店模式与扩张',
        operations='库存、履约与经营效率', membership='会员与购物服务'),
}
AI_TOPICS = {
    'business': ('shopping_discovery', 'merchandising_operations'),
    'technology': ('model_updates', 'retrieval_content_interaction'),
}
PLATFORM_WORDS = {
    'alibaba': ('阿里', '淘宝', '天猫', '菜鸟', '1688', 'alibaba', 'taobao', 'tmall', 'cainiao', '通义', '千问'),
    'jd': ('京东', 'jingdong', 'jd', 'jd.com', 'jd logistics'),
    'bytedance': ('字节', '抖音', '豆包', 'bytedance', 'douyin', 'tiktok', '红果'),
    'tencent': ('腾讯', '微信', '视频号', 'tencent', 'wechat', '小程序'),
    'meituan': ('美团', '大众点评', 'meituan'),
    'xiaohongshu': ('小红书', 'xiaohongshu', 'rednote'),
}
DOMESTIC = ('安踏', '李宁', '特步', '361', '匹克', '鸿星尔克', '波司登', '探路者', '凯乐石',
            'anta', 'li ning', 'li-ning', 'xtep', 'lining', 'kailas', 'bosideng', 'keep',
            '盒马', '超盒算', '永辉', '胖东来', '名创优品', '西西弗', '物美', '美宜佳', '小菜园',
            '大润发', '联华', '华润', '苏宁', '京东', '美团', '泡泡玛特', 'miniso', 'hema')
INTERNATIONAL = ('耐克', '阿迪', '迪卡侬', '彪马', '亚瑟士', '斯凯奇', '优衣库', '沃尔玛', '山姆',
                 '宜家', '无印良品', '迪桑特', '可隆', '斐乐', 'nike', 'adidas', 'decathlon', 'puma',
                 'lululemon', 'salomon', 'arcteryx', "arc'teryx", 'aritzia', 'hyrox', 'frasers',
                 'skechers', 'asics', 'under armour', 'columbia', 'hoka', 'patagonia', 'garmin',
                 'walmart', 'sam’s', "sam's", 'costco', 'target', 'uniqlo', 'zara', 'inditex',
                 'muji', 'ikea', 'aldi', 'lidl', 'sephora', 'amazon', 'tesco', 'carrefour', 'sm娱乐',
                 'on running', 'fila', 'descente', 'kolon', 'sm entertainment', 'new balance', 'asics')


def safe_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return False
    try:
        p = urlsplit(value)
        return bool(p.scheme in {'http', 'https'} and p.hostname and not p.username and not p.password
                    and p.hostname.lower() not in {'news.google.com', 'www.bing.com'})
    except ValueError:
        return False


def _matches(text, words):
    text = str(text).casefold()
    for word in words:
        if word.isascii():
            if re.search(r'(?<![a-z0-9])' + re.escape(word) + r'(?![a-z0-9])', text):
                return True
        elif word in text:
            return True
    return False


def infer_subcategory(section, item):
    explicit = item.get('subcategory') or item.get('sub_category') or item.get('company_origin')
    if explicit:
        raw = str(explicit).strip().casefold()
        aliases = {label.casefold(): key for key, label in SUBCATEGORIES[section].items()}
        aliases.update({'国内品牌': 'domestic', '国外品牌': 'international', '海外': 'international',
                        '业务': 'business', '技术': 'technology'})
        return aliases.get(raw, raw)
    company = str(item.get('company') or '')
    text = ' '.join(str(item.get(k) or '') for k in ('title', 'name', 'text', 'summary', 'news'))
    if section == 'platform_intelligence':
        for candidate in (company, text):
            hits = [key for key, words in PLATFORM_WORDS.items() if _matches(candidate, words)]
            if len(hits) == 1:
                return hits[0]
        return 'unclassified'
    if section == 'ai_technology':
        if _matches(text, ('模型发布', '模型升级', '多模态模型', '推理性能', '训练方法', '开源模型',
                           'benchmark', '芯片', '基础设施', 'model release', 'open source model')):
            return 'technology'
        if _matches(text, ('客服', '工作流', '购物', '库存', '办公', '门店', '业务', '选购', '商品',
                           '企业', 'shopping', 'workflow', 'customer service', 'retail', 'business')):
            return 'business'
        return 'unclassified'
    for candidate in (company, text):
        domestic, overseas = _matches(candidate, DOMESTIC), _matches(candidate, INTERNATIONAL)
        if domestic != overseas:
            return 'domestic' if domestic else 'international'
    return 'unclassified'


def entry_title(item):
    return str(item.get('title') or item.get('name') or '行业动态').strip()


def entry_text(item):
    if item.get('text'):
        return str(item['text']).strip()
    points = item.get('summary_points')
    if isinstance(points, list):
        return '\n'.join(str(p).strip() for p in points if str(p).strip())
    return str(points or item.get('summary') or item.get('news') or item.get('capability') or '').strip()


def references(item):
    if 'references' in item:
        return item['references']
    if item.get('link'):
        return [{'link': item['link'], 'title': entry_title(item), 'source': item.get('source', ''),
                 'date': item.get('date', '')}]
    return []


def validate_digest(data):
    total = 0
    for section in DOMAINS:
        items = data.get(section)
        if not isinstance(items, list):
            raise ValueError(f'{section} 必须是信息点数组。')
        for index, item in enumerate(items):
            path = f'{section}[{index}]'
            if not isinstance(item, dict):
                raise ValueError(f'{path} 必须是对象。')
            if not isinstance(item.get('title') or item.get('name'), str) or not entry_title(item):
                raise ValueError(f'{path} 缺少标题。')
            if 'text' in item and (not isinstance(item['text'], str) or not item['text'].strip()):
                raise ValueError(f'{path}.text 必须是非空文本。')
            if 'summary_points' in item and (not isinstance(item['summary_points'], list)
                    or not all(isinstance(p, str) and p.strip() for p in item['summary_points'])):
                raise ValueError(f'{path}.summary_points 必须是文本数组。')
            if not entry_text(item):
                raise ValueError(f'{path} 缺少正文 text 或 summary_points。')
            if infer_subcategory(section, item) not in (*SUBCATEGORIES[section], 'unclassified'):
                raise ValueError(f'{path}.subcategory 不是该板块的有效细分类。')
            topic = item.get('topic')
            if topic is not None:
                if not isinstance(topic, str) or topic not in TOPICS.get(section, {}):
                    raise ValueError(f'{path}.topic 不是该板块的有效主题。')
                if section == 'ai_technology':
                    kind = infer_subcategory(section, item)
                    if kind in AI_TOPICS and topic not in AI_TOPICS[kind]:
                        raise ValueError(f'{path}.topic 与业务应用／技术进展不匹配。')
            refs = references(item)
            if not isinstance(refs, list) or not refs:
                raise ValueError(f'{path} 必须有原文 link 或 references。')
            for n, ref in enumerate(refs):
                if not isinstance(ref, dict) or not safe_url(ref.get('link')):
                    raise ValueError(f'{path}.references[{n}].link 必须是有效原文链接。')
                for field in ('title', 'source', 'date'):
                    if field in ref and not isinstance(ref[field], str):
                        raise ValueError(f'{path}.references[{n}].{field} 必须是文本。')
            total += 1
    return total


def citation_catalog(data):
    """One numbering scheme across the observation and all four modules."""
    catalog = OrderedDict()
    def add(url, title, source='', date=''):
        if safe_url(url) and url not in catalog:
            catalog[url] = {'number': len(catalog) + 1, 'title': title, 'source': source, 'date': date}
    overview = data.get('weekly_overview') or {}
    by_id = {s['id']: s for s in overview.get('sources', [])}
    for field in ('macro_analysis', 'industry_trends', 'consumer_insights'):
        for point in overview.get(field, []):
            for ref_id in point.get('source_ids', []):
                source = by_id.get(ref_id)
                if source:
                    add(source.get('url'), source.get('title', '原文'), source.get('source', ''), source.get('date', ''))
    for section in DOMAINS:
        for item in data.get(section, []):
            for ref in references(item):
                add(ref.get('link'), ref.get('title') or entry_title(item), ref.get('source', ''), ref.get('date', ''))
    return catalog


def grouped_entries(data, section):
    groups = OrderedDict((key, []) for key in SUBCATEGORIES[section])
    for item in data.get(section, []):
        groups.setdefault(infer_subcategory(section, item), []).append(item)
    return [(key, SUBCATEGORIES[section].get(key, '其他／待归类'), items)
            for key, items in groups.items() if items]


def _topic_groups(section, items, allowed=None):
    topics = TOPICS[section]
    groups = OrderedDict((key, []) for key in (allowed or topics))
    for item in items:
        key = item.get('topic')
        # Missing topics in mixed old/new drafts remain visible without guessing.
        groups.setdefault(key if key in groups else 'other', []).append(item)
    return [(key, topics.get(key, '其他动态'), entries)
            for key, entries in groups.items() if entries]


def display_groups(data, section):
    """Return headings and optional subheadings shared by web and email."""
    items = data.get(section, [])
    topical = section in TOPICS and any(item.get('topic') for item in items)
    if topical and section in {'sports_outdoor', 'retail_innovation'}:
        return [(key, label, [(None, '', entries)])
                for key, label, entries in _topic_groups(section, items)]
    result = []
    for key, label, entries in grouped_entries(data, section):
        nested = (_topic_groups(section, entries, AI_TOPICS.get(key))
                  if topical else [(None, '', entries)])
        result.append((key, label, nested))
    return result


def _origin_label(section, item):
    if section not in {'sports_outdoor', 'retail_innovation'} or not item.get('topic'):
        return ''
    return {'domestic': '国内', 'international': '国外'}.get(infer_subcategory(section, item), '')


def render_digest_html(data, section):
    catalog = citation_catalog(data)
    e = lambda value: escape(str(value), quote=True)
    blocks = []
    def render_items(items):
        lines = []
        for item in items:
            links, seen = [], set()
            for ref in references(item):
                url = ref['link']
                if url in seen:
                    continue
                seen.add(url)
                source = catalog[url]
                detail = ' · '.join(str(source[k]) for k in ('title', 'source', 'date') if source.get(k))
                links.append(f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer" '
                             f'title="{e(detail)}" aria-label="来源 {source["number"]}：{e(detail)}" '
                             f'style="color:#3643BA;text-decoration:underline;font-size:13px;white-space:nowrap;">[{source["number"]}]</a>')
            text = e(entry_text(item)).replace('\n', '<br>')
            origin = _origin_label(section, item)
            badge = (f'<span class="digest-origin" style="display:inline-block;margin-right:7px;'
                     f'padding:0 6px;border:1px solid #dfe4f1;border-radius:4px;font-size:11px;'
                     f'line-height:1.7;color:#596780;background:#f4f6fb;vertical-align:middle;">'
                     f'{e(origin)}</span>' if origin else '')
            lines.append('<li class="digest-item" style="margin:0 0 14px;padding-left:2px;line-height:1.85;'
                         'font-size:15px;color:#263244;overflow-wrap:anywhere;">'
                         + badge + f'<strong style="color:#172033;">{e(entry_title(item))}：</strong>'
                         + text + ' ' + ' '.join(links) + '</li>')
        return '<ul style="margin:0;padding-left:20px;">' + ''.join(lines) + '</ul>'

    for key, label, nested in display_groups(data, section):
        content = []
        for topic, topic_label, items in nested:
            if topic is not None:
                content.append(f'<h4 style="margin:18px 0 10px;color:#253253;'
                               f'font-size:16px;line-height:1.5;">{e(topic_label)}</h4>')
            content.append(render_items(items))
        blocks.append(f'<div class="digest-group" data-subcategory="{e(key)}" style="margin-top:22px;">'
                      f'<h3 style="margin:0 0 14px;padding:0 0 9px;border-bottom:1px solid #e6e9ef;'
                      f'color:#3643BA;font-size:19px;line-height:1.5;">{e(label)}</h3>'
                      + ''.join(content) + '</div>')
    return ''.join(blocks) or '<p style="color:#687386;font-size:14px;">本期未筛出高价值行业情报。</p>'


def render_digest_text(data, section):
    catalog = citation_catalog(data)
    lines = []
    for _, label, nested in display_groups(data, section):
        lines.extend(['', label])
        for topic, topic_label, items in nested:
            if topic is not None:
                lines.extend(['', topic_label])
            for item in items:
                origin = _origin_label(section, item)
                prefix = f'【{origin}】' if origin else ''
                lines.append('- ' + prefix + entry_title(item) + '：' + entry_text(item))
                for ref in {r['link']: r for r in references(item)}.values():
                    number = catalog[ref['link']]['number']
                    lines.append(f"  [{number}] {ref.get('title') or entry_title(item)}：{ref['link']}")
    return '\n'.join(lines) or '本期未筛出高价值行业情报。'

