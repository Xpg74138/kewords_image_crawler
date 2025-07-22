import os
import csv
import time
import json
import hashlib
import random
import urllib.parse
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# --------------------------
# 配置区（可修改）
# --------------------------
CONFIG_PATH = "config.txt"
OUTPUT_ROOT = "images"
METADATA_FILE = "metadata.csv"
MAX_PER_KEYWORD = 5          # 每个关键词最多下载多少张
REQUEST_DELAY_RANGE = (1, 3)   # 每次分页抓取后的随机延迟（秒）以降低被封风险
TIMEOUT = 10                   # 下载超时（秒）
HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
}


# --------------------------
# 工具函数
# --------------------------
def read_keywords(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def safe_filename(s, idx=None, ext="jpg"):
    # 将不可用字符替换为下划线
    base = "".join(c if c.isalnum() or c in "_-" else "_" for c in s)
    if idx is not None:
        base = f"{base}_{idx:04d}"
    return f"{base}.{ext}"


def guess_ext_from_url(url):
    # 依据 URL 后缀粗略猜测；默认 jpg
    path = urlparse(url).path
    _, _, tail = path.rpartition(".")
    tail = tail.lower()
    if tail in ("jpg", "jpeg", "png", "gif", "bmp", "webp"):
        return "jpg" if tail == "jpeg" else tail
    return "jpg"


# --------------------------
# Bing HTML 抓取 & 解析
# --------------------------
def bing_image_search_html(query, first=0):
    """
    返回 Bing 图片搜索页面 HTML 文本。
    first: 分页偏移（0, 35, 70...）
    """
    params = {
        "q": query,
        "first": str(first),  # 起始索引
        "form": "HDRSC2",
        "cw": "1116", "ch": "777"  # 给定窗口尺寸参数（可选）
    }
    url = "https://www.bing.com/images/search?" + urllib.parse.urlencode(params, safe=":+")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_bing_results(html):
    """
    从 Bing 图片 HTML 中提取结果列表。
    返回列表：[{murl:..., purl:..., turl:..., title:...}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # 每个结果在 <a class="iusc"> 标签上
    for a in soup.find_all("a", class_="iusc"):
        m_attr = a.get("m")
        if not m_attr:
            continue
        # 该属性是 JSON 字符串（有时含 HTML 转义 &quot;）
        try:
            m_json = json.loads(m_attr)
        except json.JSONDecodeError:
            # 尝试替换 HTML 实体再解析
            try:
                m_json = json.loads(m_attr.replace("&quot;", '"'))
            except Exception:
                continue

        murl = m_json.get("murl")   # 图片直链
        purl = m_json.get("purl")   # 图片所在网页 ✅
        turl = m_json.get("turl")   # 缩略图
        title = m_json.get("t")     # 标题
        if not murl:
            continue
        results.append({
            "murl": murl,
            "purl": purl,
            "turl": turl,
            "title": title
        })
    return results


# --------------------------
# 下载单张图片
# --------------------------
def download_image(url, save_path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"   ✘ 下载失败: {url} | {e}")
        return False


# --------------------------
# 主抓取流程（单关键词）
# --------------------------
def crawl_one_keyword(keyword, max_num, csv_writer, global_hash_set):
    print(f"\n🚀 开始关键词：{keyword}")
    save_dir = os.path.join(OUTPUT_ROOT, keyword.replace(" ", "_"))
    os.makedirs(save_dir, exist_ok=True)

    downloaded = 0
    page_first = 0
    seen_purl = set()  # 每关键词内避免同网页重复写太多（可选）

    while downloaded < max_num:
        # 抓一页 HTML
        html = bing_image_search_html(keyword, first=page_first)
        items = parse_bing_results(html)
        if not items:
            print("   ⚠️ 没有更多结果，提前结束。")
            break

        for item in items:
            if downloaded >= max_num:
                break

            img_url = item["murl"]
            page_url = item.get("purl") or ""
            title = item.get("title") or keyword

            # 下载文件
            ext = guess_ext_from_url(img_url)
            filename = safe_filename(keyword, idx=downloaded + 1, ext=ext)
            local_path = os.path.join(save_dir, filename)

            ok = download_image(img_url, local_path)
            if not ok:
                continue

            # 去重（跨关键词全局）
            try:
                h = md5_file(local_path)
            except Exception:
                print("   ⚠️ 无法读文件做哈希，跳过。")
                continue
            if h in global_hash_set:
                os.remove(local_path)
                print(f"   ⚠️ 重复（MD5）已移除：{local_path}")
                continue
            global_hash_set.add(h)

            # 写入元数据
            csv_writer.writerow([
                keyword,
                local_path,
                img_url,
                page_url,
                urlparse(page_url).netloc if page_url else ""
            ])

            downloaded += 1
            print(f"   ✔ {downloaded}/{max_num} 保存：{local_path}")

        # 下一页
        page_first += len(items)
        # 随机延迟，避免被封
        time.sleep(random.uniform(*REQUEST_DELAY_RANGE))

    print(f"✅ 关键词【{keyword}】完成，共 {downloaded} 张。")


# --------------------------
# 总控
# --------------------------
def main():
    keywords = read_keywords(CONFIG_PATH)
    if not keywords:
        print("配置文件无关键词，退出。")
        return

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    global_hash_set = set()

    with open(METADATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "local_path", "image_url", "source_page", "source_domain"])

        for kw in keywords:
            crawl_one_keyword(kw, MAX_PER_KEYWORD, writer, global_hash_set)

    print(f"\n📄 所有关键词完成，元数据写入：{METADATA_FILE}")


# --------------------------
# 入口
# --------------------------
if __name__ == "__main__":
    main()
