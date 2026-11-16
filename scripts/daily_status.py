# -*- coding: utf-8 -*-
"""每日生成 data/status.json: 512890 价格/MA200/偏离 + 对 H30269 的近20日跟踪差
由 GitHub Actions 定时运行，不需要本地电脑。
"""
import json
import urllib.request
import datetime
import os
import sys

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ETF = "sh512890"
INDEX = "H30269"
WINDOW = 20


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")


def main():
    out = {"updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "etfDate": None, "price": None, "ma200": None, "dev": None,
           "track20": None, "trackDate": None, "error": None}
    try:
        k = json.loads(get("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=%s,day,,,800,qfq" % ETF))
        node = k["data"][ETF]
        bars = node.get("qfqday") or node.get("day")
        closes = [(b[0], float(b[2])) for b in bars if float(b[2]) > 0]
        if len(closes) < 200:
            raise RuntimeError("K线不足200天")
        px = dict(closes)
        last_date, last_px = closes[-1]
        ma = sum(c for _, c in closes[-200:]) / 200.0
        out.update(etfDate=last_date, price=round(last_px, 3),
                   ma200=round(ma, 4), dev=round(last_px / ma - 1, 5))
    except Exception as e:
        out["error"] = "ETF数据: %s" % e
        write(out)
        return

    try:
        end = datetime.date.today()
        start = end - datetime.timedelta(days=120)
        url = ("https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=%s"
               "&startDate=%s&endDate=%s" % (INDEX, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")))
        data = json.loads(get(url)).get("data") or []
        idx = {}
        for it in data:
            d = str(it.get("tradeDate", ""))
            c = it.get("close")
            if d and c:
                d2 = "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
                idx[d2] = float(c)
        common = [d for d, _ in closes if d in idx]
        if len(common) >= WINDOW + 1:
            d0, d1 = common[-(WINDOW + 1)], common[-1]
            etf_ret = px[d1] / px[d0] - 1
            idx_ret = idx[d1] / idx[d0] - 1
            out["track20"] = round(etf_ret - idx_ret, 5)
            out["trackDate"] = "%s~%s" % (d0, d1)
        else:
            out["error"] = "指数数据不足(%d个共同交易日)" % len(common)
    except Exception as e:
        out["error"] = (out["error"] + "; " if out["error"] else "") + "指数数据: %s" % e

    write(out)


def write(out):
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "status.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
