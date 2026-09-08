import unittest
from unittest.mock import patch
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from collections import Counter

from sources import google_news, http_feed
from sources.manual import fetch_manual_items
from intelligence.report_quality import finalize_report, validate_report


def entry(title, days=0):
    return {'title':title, 'summary':'retail inventory workflow', 'link':'https://example.com/'+title,
            'published':format_datetime(datetime.now(timezone.utc)-timedelta(days=days))}


class EfficientCollectionTests(unittest.TestCase):
    def setUp(self):
        self.patches = [patch.object(google_news,'FILTER_PROFILES', {'retail':{},'ai':{}}),
                        patch.object(google_news,'MIN_SECTION_CANDIDATES', {'retail':2,'ai':2}),
                        patch.object(google_news,'EXPANDED_SEARCH_QUERIES', {})]
        for p in self.patches:p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def test_one_query_supports_three_local_windows(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            return SimpleNamespace(entries=[entry('one',1),entry('two',6)])
        with patch.object(http_feed,'fetch_feed',side_effect=fetch):
            items=google_news.fetch_google_news_items({'retail':['Inventory']})
        self.assertEqual(len(calls),1)
        self.assertIn('when:14d',parse_qs(urlparse(calls[0]).query)['q'][0])
        self.assertEqual({i['search_window_days'] for i in items},{7})
        self.assertEqual(len(items),2)

    def test_duplicate_queries_across_sections_fetched_once(self):
        with patch.object(http_feed,'fetch_feed',return_value=SimpleNamespace(entries=[])) as fetch:
            google_news.fetch_google_news_items({'retail':['Shared query',' shared   query '], 'ai':['SHARED QUERY']})
        self.assertEqual(fetch.call_count,1)

    def test_stop_launching_when_pool_sufficient(self):
        with patch.object(http_feed,'fetch_feed',return_value=SimpleNamespace(entries=[entry('a'),entry('b')])) as fetch:
            google_news.fetch_google_news_items({'retail':['q1','q2','q3','q4','q5']})
        self.assertEqual(fetch.call_count,2)

    def test_existing_sources_reduce_searches(self):
        existing=[{'domain':'retail','link':'https://example.com/a'}, {'domain':'retail','link':'https://example.com/b'}]
        with patch.object(http_feed,'fetch_feed') as fetch:
            self.assertEqual(google_news.fetch_google_news_items({'retail':['q1','q2']},existing),[])
        fetch.assert_not_called()

    def test_expansion_only_for_deficient_sections(self):
        with patch.object(google_news,'EXPANDED_SEARCH_QUERIES', {'retail':['q3'],'ai':['unused']}):
            with patch.object(http_feed,'fetch_feed',return_value=SimpleNamespace(entries=[])) as fetch:
                google_news.fetch_google_news_items({'retail':['q1','q1']})
        self.assertEqual(fetch.call_count,2)

    def test_no_false_empty_for_slow_success(self):
        import time
        def fetch(url):
            time.sleep(.04)
            return SimpleNamespace(entries=[entry('late')])
        with patch.object(http_feed,'fetch_feed',side_effect=fetch):
            feeds=http_feed.fetch_unique(['a','b'],{})
        self.assertEqual([f.entries[0]['title'] for f in feeds],['late','late'])

    def test_http_failure_retries_once_and_is_logged(self):
        import requests
        with patch.object(http_feed.requests,'get',side_effect=requests.ConnectionError), patch('builtins.print') as log:
            self.assertIsNone(http_feed.fetch_feed('https://example.com/rss'))
        self.assertIn('[fetch failed]',log.call_args.args[0])

    def test_quality_and_email_metadata(self):
        items=fetch_manual_items(Path(__file__).parent/'manual_sources/daily_input.md')
        self.assertEqual(Counter(i['domain'] for i in items),dict(platform=2,ai=2,sports=2,retail=2))
        data=finalize_report(None,items)
        validate_report(data)
        for section in ('platform_intelligence','ai_technology','sports_outdoor','retail_innovation'):
            self.assertEqual(len(data[section]),2)
            for card in data[section]:
                self.assertTrue(card['keywords'])
                self.assertTrue(card['category'])
        with self.assertRaises(ValueError):validate_report(finalize_report(None,items[:1]))

    def test_no_report_or_stage_deadline(self):
        root=Path(__file__).parent
        for name in ['main.py','intelligence/report_quality.py','sources/google_news.py','sources/rss.py']:
            text=(root/name).read_text()
            self.assertNotIn('signal.alarm',text)
            self.assertNotIn('subprocess.run',text)
            self.assertNotIn('bounded_runtime',text)

    def test_same_link_different_titles_uses_one_candidate(self):
        from main import prepare_information_pool
        items=[{'title':title,'summary':'facts','link':'https://example.com/story','domain':'retail'} for title in ['first headline','republished headline']]
        self.assertEqual(len(prepare_information_pool(items)),1)


if __name__=='__main__':unittest.main()
