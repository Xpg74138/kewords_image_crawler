
# 🐷 Pig Disease Image Crawler（基于 Bing 图片网页搜索）

本项目是一个用于**按关键词自动爬取图像并记录其来源网页链接**的工具，适用于图像采集、疾病可视化、图像识别训练等任务。

---

## 📁 目录结构

```
.
├── main.py        # 主爬虫脚本
├── config.txt                # 配置文件，填写关键词（每行一个）
├── metadata.csv              # 自动生成：记录图片路径、原图链接、网页链接
└── images/                   # 自动生成：存储每类关键词的图像
    ├── 猪瘟/
    ├── 猪_蓝耳病/
    └── ...
```

---

## 🧱 环境依赖

使用conda虚拟环境， Python 3.10+，依赖库安装如下：

```bash
pip install -r requirements.txt
```


## ✍️ 配置关键词

在 `config.txt` 中填写每个关键词（每行一个），例如：

```
猪瘟
猪 蓝耳病
猪 口蹄疫
```

---

## 🚀 如何运行

```bash
python crawl_bing_html.py
```

运行后会自动完成以下流程：

1. 打开 config.txt 中的所有关键词
2. 对每个关键词使用 Bing 网页搜索抓取图片
3. 下载图片到 `images/关键词/`
4. 自动去重（基于 MD5）
5. 保存图片相关信息到 `metadata.csv` 文件中

---

## 📄 输出文件说明：`metadata.csv`

字段如下：

| 字段名         | 含义说明                         |
|----------------|----------------------------------|
| `keyword`      | 图像对应的搜索关键词             |
| `local_path`   | 图像本地保存路径                 |
| `image_url`    | 图像真实下载地址（可能为 CDN）   |
| `source_page`  | 图像所在网页地址 ✅（你关注的）  |
| `source_domain`| 所在网页的域名                   |

---

## ⚙️ 自定义参数说明

可在脚本头部（`配置区`）中自定义以下参数：

```python
CONFIG_PATH = "config.txt"         # 关键词配置文件路径
OUTPUT_ROOT = "images"             # 图片保存根目录
METADATA_FILE = "metadata.csv"     # 图像元信息 CSV 文件
MAX_PER_KEYWORD = 5                # 每个关键词下载图像最大数量
REQUEST_DELAY_RANGE = (1, 3)       # 每页之间的请求延迟范围（秒）
TIMEOUT = 10                       # 网络请求超时时间（秒）
HEADERS = { ... }                  # 浏览器 User-Agent，避免被封
```

---

## 🔒 注意事项

- Bing 图片搜索有反爬机制，建议每页搜索之间随机等待 1~3 秒
- 本脚本使用网页结构解析而非官方 API，因此 Bing 结构变更可能会影响功能（可适时更新）
- 所下载图像仅用于学习、科研等非商业目的，需遵循版权法规

---


## 📬 联系作者

如你希望本项目添加某项功能或适配特定需求，可联系作者或创建 issue。
