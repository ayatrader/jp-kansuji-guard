import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kansujiguard import convert, naive_convert, parse_number  # noqa: E402
from kansujiguard.bench import FILE, score  # noqa: E402
from kansujiguard.cases import all_cases  # noqa: E402
from kansujiguard.server import handle  # noqa: E402


class TestParse(unittest.TestCase):
    def test_values(self):
        cases = {"三億五千万": 350000000, "二〇二四": 2024, "一九九五": 1995, "壱萬": 10000, "参拾萬": 300000,
                 "1億2,300万": 123000000, "１２万３千": 123000, "十": 10, "百二十": 120, "一兆二千億": 1200000000000,
                 "千": 1000, "二十五": 25}
        for s, v in cases.items():
            self.assertEqual(parse_number(s), v, s)

    def test_malformed(self):
        for s in ("十十", "万億", "千百千", "万", "三億五億", ""):
            self.assertIsNone(parse_number(s), s)


class TestConvert(unittest.TestCase):
    def t(self, s):
        return convert(s)["text"]

    def test_numbers(self):
        self.assertEqual(self.t("売上は三億五千万円でした"), "売上は350000000円でした")
        self.assertEqual(self.t("第三条に従う"), "第3条に従う")
        self.assertEqual(self.t("令和六年三月十五日"), "令和6年3月15日")
        self.assertEqual(self.t("金壱萬円也"), "金10000円也")

    def test_keeps_names_places_idioms(self):
        for s in ("一宮市", "五十嵐さん", "三菱商事", "統一した", "一石二鳥", "加藤一二三九段", "京都の三条"):
            self.assertEqual(self.t(s), s)

    def test_flags_are_reported_not_converted(self):
        r = convert("十分な時間と二三人と数万円")
        self.assertEqual(r["text"], "十分な時間と二三人と数万円")
        self.assertEqual([f["text"] for f in r["flags"]], ["十", "二三", "万"])

    def test_number_inside_protected_word_suffix(self):
        # 万人 (ばんにん) is a word, but in 三十八万人 it is 380000 people
        self.assertEqual(self.t("約三十八万人"), "約380000人")

    def test_held_out_sentences(self):
        # not in the bench
        self.assertEqual(self.t("会議は二十分で終わった"), "会議は20分で終わった")
        self.assertEqual(self.t("三井の株を五百株"), "三井の株を500株")
        self.assertEqual(self.t("一般の参加者は四十人"), "一般の参加者は40人")
        self.assertEqual(self.t("四日市から八王子まで"), "四日市から八王子まで")

    def test_digits_untouched_and_offsets(self):
        r = convert("合計123円と三千円")
        self.assertEqual(r["text"], "合計123円と3000円")
        c = r["changes"][0]
        self.assertEqual(("合計123円と三千円"[c["start"]:c["end"]], c["value"]), ("三千", 3000))

    def test_type_error(self):
        with self.assertRaises(ValueError):
            convert(None)


class TestBench(unittest.TestCase):
    def test_bench_file_matches_cases(self):
        path = os.path.join(ROOT, "data", FILE)
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f]
        self.assertEqual(rows, all_cases())
        self.assertEqual(len({r["id"] for r in rows}), len(rows))

    def test_scores(self):
        self.assertEqual(score(lambda t: convert(t)["text"])["overall"]["accuracy"], 1.0)
        self.assertLess(score(naive_convert)["overall"]["accuracy"], 0.5)


class TestMCP(unittest.TestCase):
    def test_list_and_call(self):
        r = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "jp-kansuji-guard")
        tools = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, {"jp_kansuji_convert", "jp_kansuji_parse"})
        for t in tools:
            self.assertTrue(t["annotations"]["readOnlyHint"])
        out = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "jp_kansuji_convert", "arguments": {"text": "三菱の売上は三億円"}}})
        self.assertEqual(out["result"]["structuredContent"]["text"], "三菱の売上は300000000円")
        bad = handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                      "params": {"name": "jp_kansuji_parse", "arguments": {"numeral": 5}}})
        self.assertTrue(bad["result"]["isError"])
        self.assertIn("error", handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "x"}}))
        self.assertIsNone(handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_stdio(self):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "jp_kansuji_parse", "arguments": {"numeral": "壱萬"}}}) + "\n"
        p = subprocess.run([sys.executable, "-m", "kansujiguard.server"], input=msg.encode("utf-8"),
                           capture_output=True, cwd=ROOT, timeout=30)
        resp = json.loads(p.stdout.decode("utf-8").strip())
        self.assertEqual(resp["result"]["structuredContent"]["value"], 10000)


if __name__ == "__main__":
    unittest.main()
