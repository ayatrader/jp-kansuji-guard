"""Convert Japanese kanji numerals in running text to digits, but only where the text is clearly a number.

Proper nouns (一宮, 三菱, 五十嵐), words (統一, 一般) and idioms (一石二鳥) are kept.
Spans that a rule cannot decide (十分 = "enough" or "10 minutes", 二三人 = "2 or 3 people") are kept and flagged.
Python standard library only.
"""
import re

DIGIT = {"〇": 0, "零": 0, "一": 1, "壱": 1, "二": 2, "弐": 2, "三": 3, "参": 3, "四": 4,
         "五": 5, "伍": 5, "六": 6, "七": 7, "八": 8, "九": 9}
SMALL = {"十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "阡": 1000}
BIG = {"万": 10 ** 4, "萬": 10 ** 4, "億": 10 ** 8, "兆": 10 ** 12}
KANJI_NUM = "".join(DIGIT) + "".join(SMALL) + "".join(BIG)
_FW = str.maketrans("０１２３４５６７８９，", "0123456789,")

RUN_RE = re.compile(r"[0-9０-９" + KANJI_NUM + r"](?:[0-9０-９,，" + KANJI_NUM + r"]*[0-9０-９" + KANJI_NUM + r"])?")

# Units and counters that make a preceding numeral a number. Longest match wins.
COUNTERS = sorted("""円 年 年度 年間 年生 ヶ月 か月 カ月 ケ月 箇月 ヵ月 月 日 日間 時 時間 分 分間 秒 週 週間 世紀 人 名 歳 才 個 件 回 回目
枚 本 台 冊 社 店 軒 階 号 番目 番 位 点 条 項 章 節 巻 頁 ページ 行目 通 杯 匹 頭 羽 着 足 品 種 種類 代 割 倍 度 期 泊 校 戸 坪 畳 株 票 席 問 丁目 番地 区画
ドル ユーロ メートル キロ グラム リットル パーセント % ％ km kg cm mm m g 円札 万円 億円""".split(), key=len, reverse=True)

# Characters before a single-digit numeral that still mean "a number follows".
ALLOWED_PREV = set("第約計全各毎満同金総")  # 同 is guarded by the lexicon (同一)
APPROX_PREV = set("数何幾")  # 数万円, 何百人: not a single value

# Words that contain numeral characters but are not numbers. Kept as they are.
PROTECTED = """
一般 一部 一緒 一応 一方 一生 一体 一切 一層 一斉 一致 一律 一流 一覧 一環 一貫 一見 一向 一瞬 一旦 一端 一途 一筋 一面 一新 一掃 一変 一転
一段と 一目 一同 一人前 一人っ子 一員 一因 一例 一味 一家 一般的 一昨日 一昨年 一人称 一次 一極 一角 一帯 一服 一報 一件落着 一長一短
唯一 統一 同一 均一 単一 随一 画一 択一 万一 万が一 不一致 第一人者 第一印象 第一線 第三者 第三国
万全 万能 万歳 万博 万引 万年筆 万葉 万国 万人 万物 万華鏡 千差万別 千載一遇 千羽鶴
一石二鳥 一期一会 十人十色 三日坊主 七転八起 七転び八起き 四苦八苦 八方美人 二束三文 三寒四温 一朝一夕 一喜一憂 一進一退 五分五分 九死に一生
一心不乱 一網打尽 一目瞭然 一刀両断 十中八九 二人三脚 三位一体 一騎当千 百発百中 百人一首 八百長 八百屋 八百万 四十肩 五十肩 二十四節気 十二支 七福神
三角 四角 三味線 十字 十字架 八重 七夕 二日酔い 五月雨 五月晴れ 十八番 三面記事 二枚目 三枚目 二の舞 一張羅 七五三 四天王 三種の神器 十二単
一宮 一関 一戸 二戸 三戸 五戸 六戸 八戸 九戸 二子玉川 三重 三鷹 三島 三河 三田 三原 三沢 三郷 四日市 四国 四街道 五所川原 五島 五反田 六本木
七尾 八王子 八尾 八代 八幡 八女 九州 九十九里 十和田 十日町 十勝 千葉 千代田 千歳 千住 千里 万代 四万十 八丈島 九段 十条 三軒茶屋 一橋 一条 二条 三条
四条 五条 六条 七条 八条 九条 一乗寺 八坂 百合ヶ丘 二重橋 三陸 四谷 八重洲 五稜郭 九十九
一郎 二郎 三郎 四郎 五郎 六郎 七郎 八郎 九郎 十郎 太一 健一 誠一 一二三 五十嵐 二宮 三浦 三好 三上 三木 三宅 一ノ瀬 八木 八田 九鬼 千尋 千夏 千秋
百合 七海 一輝 一樹 一平 千代 美千代 百恵 三四郎 十兵衛
三菱 三井 一休 七十七銀行 八十二銀行 百五銀行 十六銀行 十八親和 三越 三和 一蘭 五洋建設 九電 四電 一ツ橋
""".split()

# Readings decide these; text alone does not.
def _ambiguous(text, s, e):
    run = text[s:e]
    nxt = text[e:e + 2]
    prev = text[max(0, s - 2):s]
    if run == "十" and text.startswith("分", e):
        if nxt[1:2] in ("間",) or text.startswith(("後", "前", "おき", "ごと", "以内", "以上", "程度", "遅れ"), e + 1):
            return None
        if prev[-1:] == "時" or prev[-1:].isdigit():
            return None
        return "十分 can mean 'enough' (じゅうぶん) or '10 minutes' (じゅっぷん)"
    if run == "一" and text.startswith("時", e):
        if prev in ("午前", "午後") or text.startswith(("半", "頃", "過ぎ", "ちょうど"), e + 1):
            return None
        if text.startswith(("的", "期", "金", "停止", "中断", "保", "帰", "預"), e + 1):
            return "keep"
        return "一時 can mean 'temporarily' (いちじ) or '1 o'clock'"
    if run == "一" and text.startswith("番", e) and not text.startswith("番目", e) and not text.startswith("番地", e):
        if prev[-1:] == "第":
            return None
        return "一番 can mean 'most / best' or 'number 1'"
    if run == "一" and text.startswith("度", e):
        return None
    flat = all(c in DIGIT for c in run)
    if flat and len(run) == 2 and "〇" not in run and "零" not in run:
        a, b = DIGIT[run[0]], DIGIT[run[1]]
        if b == a + 1:
            return f"{run} usually means an approximate range ({a} or {b}), not {a}{b}"
    return None


def parse_number(s):
    """Parse a numeral string (kanji, daiji, digits, or mixed like 1億2,300万) to int. Returns None if malformed."""
    s = s.translate(_FW).replace(",", "")
    if not s:
        return None
    if all(c.isdigit() for c in s):
        return int(s)
    if all(c in DIGIT or c.isdigit() for c in s):  # flat: 二〇二四, 一九九五
        return int("".join(str(DIGIT[c]) if c in DIGIT else c for c in s))
    total, section, cur = 0, 0, None
    last_big, last_small = None, None
    i = 0
    while i < len(s):
        c = s[i]
        if c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            if cur is not None:
                return None
            cur = int(s[i:j])
            i = j
            continue
        if c in DIGIT:
            if cur is not None:
                return None
            cur = DIGIT[c]
        elif c in SMALL:
            u = SMALL[c]
            if last_small is not None and u >= last_small:
                return None
            if cur is not None and cur >= 10:
                return None
            section += (1 if cur is None else cur) * u
            cur, last_small = None, u
        elif c in BIG:
            u = BIG[c]
            if last_big is not None and u >= last_big:
                return None
            section += cur or 0
            if section == 0:
                return None
            total += section * u
            section, cur, last_small, last_big = 0, None, None, u
        else:
            return None
        i += 1
    section += cur or 0
    if last_small is not None and cur is not None and cur >= 10:
        return None
    return total + section


def _protected_spans(text):
    spans = []
    for w in PROTECTED:
        start = text.find(w)
        while start != -1:
            spans.append((start, start + len(w), w))
            start = text.find(w, start + 1)
    return spans


def _is_kanji(ch):
    return bool(ch) and ("一" <= ch <= "鿿" or ch in "々〆")


ERA_PREV = ("令和", "平成", "昭和", "大正", "明治", "午前", "午後", "西暦", "毎月", "毎年", "毎週", "毎日")


def _is_num(ch):
    return bool(ch) and (ch in KANJI_NUM or ch.translate(_FW).isdigit())


def _after_number_unit(text, s):
    """True for 年一月 / 三時十分 / 二泊三日: the text before is a counter that itself follows a number."""
    head = text[:s]
    for c in COUNTERS:
        if head.endswith(c) and len(head) > len(c) and _is_num(head[-len(c) - 1]):
            return True
    return False


def _counter_after(text, e):
    for c in COUNTERS:
        if text.startswith(c, e):
            return c
    return None


def convert(text):
    """Return {text, changes, kept, flags}. Only clear numbers are converted."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    protected = _protected_spans(text)
    out, changes, kept, flags = [], [], [], []
    pos = 0
    for m in RUN_RE.finditer(text):
        s, e = m.span()
        run = m.group()
        if not any(c in KANJI_NUM for c in run):
            continue  # already digits
        item = {"start": s, "end": e, "text": run}
        prev = text[s - 1] if s > 0 else ""
        hit = next((w for (ps, pe, w) in protected if ps < e and s < pe
                    and not (s < ps and _is_num(text[ps - 1]))  # 三十八万人: 万人 starts inside the number
                    and not (ps == s and prev == "第")), None)  # 第三条 is article 3, not 三条
        if hit:
            kept.append({**item, "reason": f"part of the word {hit}"})
            continue
        if prev in APPROX_PREV:
            flags.append({**item, "reason": f"{prev}{run} is approximate, not a single value"})
            continue
        amb = _ambiguous(text, s, e)
        if amb == "keep":
            kept.append({**item, "reason": "word, not a number"})
            continue
        if amb:
            flags.append({**item, "reason": amb})
            continue
        value = parse_number(run)
        if value is None:
            flags.append({**item, "reason": "malformed numeral"})
            continue
        counter = _counter_after(text, e)
        positional = any(c in SMALL or c in BIG for c in run) and len(run) >= 2
        flat_long = len(run) >= 3 or any(c.isdigit() for c in run.translate(_FW))
        nxt = text[e:e + 1]
        if counter and (not _is_kanji(prev) or prev in ALLOWED_PREV or positional or flat_long
                        or _after_number_unit(text, s) or text[max(0, s - 2):s] in ERA_PREV):
            reason = f"followed by {counter}"
        elif any(c in BIG for c in run) and len(run) >= 2 and not _is_kanji(nxt):
            reason = "contains 万/億/兆"
        else:
            why = "inside a word" if (_is_kanji(prev) or _is_kanji(nxt)) else "no unit or counter after it"
            kept.append({**item, "reason": why})
            continue
        out.append(text[pos:s])
        out.append(str(value))
        pos = e
        changes.append({"start": s, "end": e, "before": run, "after": str(value), "value": value, "reason": reason})
    out.append(text[pos:])
    return {"text": "".join(out), "changes": changes, "kept": kept, "flags": flags}


def naive_convert(text):
    """Baseline for the bench: convert every parsable numeral run, with no context rules."""
    def rep(m):
        run = m.group()
        if not any(c in KANJI_NUM for c in run):
            return run
        v = parse_number(run)
        return run if v is None else str(v)
    return RUN_RE.sub(rep, text)
