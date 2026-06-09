import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from datetime import datetime, timezone, timedelta
from grouper import group_articles

_BASE = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _art(uid, topics, hours=0):
    crawled = _BASE + timedelta(hours=hours)
    ts = crawled.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")
    return {
        "uuid": uid,
        "topics": topics,
        "crawled": ts,
        "published": ts,
        "summary": f"Summary {uid}",
        "url": f"https://example.com/{uid}",
        "thread": {"domain_rank": 5000},
        "performance_score": 1,
        "entities": {"locations": [], "organizations": []},
    }


class TestGroupArticlesBasic(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(group_articles([]), [])

    def test_single_article_forms_one_group(self):
        groups = group_articles([_art("a1", ["Finance->risk"])])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0]["uuid"], "a1")

    def test_two_articles_shared_topic_within_window(self):
        groups = group_articles([_art("a1", ["Finance->risk"], 0), _art("a2", ["Finance->risk"], 3)])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_two_articles_shared_topic_outside_window(self):
        groups = group_articles([_art("a1", ["Finance->risk"], 0), _art("a2", ["Finance->risk"], 7)])
        self.assertEqual(len(groups), 2)

    def test_no_shared_topic_within_window(self):
        groups = group_articles([_art("a1", ["Finance->risk"], 0), _art("a2", ["Politics->gov"], 1)])
        self.assertEqual(len(groups), 2)


class TestGroupArticlesBoundary(unittest.TestCase):
    def test_at_exact_window_boundary_grouped(self):
        # Exactly 6 hours apart — within window (<=)
        groups = group_articles([_art("a1", ["TopicA"], 0), _art("a2", ["TopicA"], 6)])
        self.assertEqual(len(groups), 1)

    def test_just_past_window_boundary_not_grouped(self):
        # 6 hours and 6 minutes — beyond window
        groups = group_articles([_art("a1", ["TopicA"], 0), _art("a2", ["TopicA"], 6.1)])
        self.assertEqual(len(groups), 2)

    def test_window_anchors_to_first_article_in_group(self):
        # a1 at t=0, a2 at t=6.5 → outside window from a1 → new group
        groups = group_articles([_art("a1", ["TopicA"], 0), _art("a2", ["TopicA"], 6.5)])
        self.assertEqual(len(groups), 2)


class TestGroupArticlesTopics(unittest.TestCase):
    def test_empty_topics_form_singleton_groups(self):
        groups = group_articles([_art("a1", [], 0), _art("a2", [], 1)])
        self.assertEqual(len(groups), 2)

    def test_none_topics_treated_as_empty(self):
        groups = group_articles([_art("a1", None, 0), _art("a2", ["Finance->risk"], 1)])
        self.assertEqual(len(groups), 2)

    def test_empty_topics_does_not_match_article_with_topics(self):
        groups = group_articles([_art("a1", ["Finance->risk"], 0), _art("a2", [], 1)])
        self.assertEqual(len(groups), 2)

    def test_chain_grouping_via_intermediate_article(self):
        # a1 has X, a2 has X+Y, a3 has Y only
        # a1+a2 merge on X; group now has X+Y; a3 matches on Y
        a1, a2, a3 = _art("a1", ["TopicX"], 0), _art("a2", ["TopicX", "TopicY"], 1), _art("a3", ["TopicY"], 2)
        groups = group_articles([a1, a2, a3])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 3)

    def test_chain_stops_outside_window(self):
        # a1 at t=0, a2 at t=1 (TopicX+Y), a3 at t=7 (TopicY) — a3 outside window from a1
        a1, a2, a3 = _art("a1", ["TopicX"], 0), _art("a2", ["TopicX", "TopicY"], 1), _art("a3", ["TopicY"], 7)
        groups = group_articles([a1, a2, a3])
        self.assertEqual(len(groups), 2)
        sizes = sorted(len(g) for g in groups)
        self.assertEqual(sizes, [1, 2])


class TestGroupArticlesMultipleGroups(unittest.TestCase):
    def test_two_independent_topic_groups(self):
        articles = [
            _art("a1", ["TopicA"], 0), _art("a2", ["TopicA"], 2),
            _art("b1", ["TopicB"], 0.5), _art("b2", ["TopicB"], 3),
        ]
        groups = group_articles(articles)
        self.assertEqual(len(groups), 2)
        self.assertEqual(sorted(len(g) for g in groups), [2, 2])

    def test_three_time_separated_batches(self):
        batch1 = [_art(f"a{i}", ["TopicA"], i * 0.5) for i in range(3)]  # t=0,0.5,1
        batch2 = [_art(f"b{i}", ["TopicA"], 8 + i * 0.5) for i in range(3)]  # t=8,8.5,9
        batch3 = [_art(f"c{i}", ["TopicA"], 16 + i * 0.5) for i in range(3)]  # t=16,16.5,17
        groups = group_articles(batch1 + batch2 + batch3)
        self.assertEqual(len(groups), 3)
        for g in groups:
            self.assertEqual(len(g), 3)

    def test_all_same_topic_within_window(self):
        articles = [_art(f"a{i}", ["SharedTopic"], i * 0.5) for i in range(10)]
        groups = group_articles(articles)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 10)


class TestGroupArticlesSorting(unittest.TestCase):
    def test_unsorted_input_handled_correctly(self):
        # Provide articles out of crawled order — grouper must sort internally
        a1, a2, a3 = _art("a1", ["TopicA"], 5), _art("a2", ["TopicA"], 1), _art("a3", ["TopicA"], 3)
        groups = group_articles([a1, a2, a3])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 3)

    def test_reverse_order_input(self):
        articles = [_art(f"a{i}", ["TopicA"], 5 - i) for i in range(5)]
        groups = group_articles(articles)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 5)


class TestGroupArticlesMissingFields(unittest.TestCase):
    def test_missing_crawled_falls_back_to_published(self):
        a = _art("a1", ["TopicA"], 0)
        del a["crawled"]
        groups = group_articles([a])
        self.assertEqual(len(groups), 1)

    def test_missing_both_timestamps_still_forms_group(self):
        a = {"uuid": "a1", "topics": ["TopicA"], "summary": "s", "url": "u",
             "thread": {}, "performance_score": 0, "entities": {}}
        groups = group_articles([a])
        self.assertEqual(len(groups), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
