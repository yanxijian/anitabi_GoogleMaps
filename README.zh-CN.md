# anitabi → Google My Maps

**简体中文** · [English](README.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

把 [anitabi](https://www.anitabi.cn/map) 的圣地巡礼地图导出成 **KML**，再导入 [Google My Maps](https://www.google.com/maps/d/) 在谷歌地图上浏览。

只依赖 Python 3.8+ 标准库，**不需要安装 `requests`**。

## 用法

```bash
# 直接给 bangumi_id（可以给多个）
python anitabi_GoogleMaps.py 331884

# 一次导出多个作品
python anitabi_GoogleMaps.py 331884 4912

# 指定输出文件 / 输出目录
python anitabi_GoogleMaps.py 331884 -o 孤独摇滚.kml
python anitabi_GoogleMaps.py 331884 --outdir maps

# 交互模式（不给 id 时进入，输入 q 或直接回车退出）
python anitabi_GoogleMaps.py
```

bangumi_id 就是作品页 URL 里的数字：打开 <https://www.anitabi.cn/map>，搜索作品后地址栏里的 `bangumi/<id>` 即为所需 id。

导入步骤：打开 [Google My Maps](https://www.google.com/maps/d/) → 创建新地图 → 新建图层 → 导入 → 选择生成的 `.kml`。

## 网络不稳定时

anitabi 的接口在部分网络下会超时或返回 403。脚本会重试（`--retries`，默认 2 次；超时 `--timeout`，默认 20 秒），失败后自动回退到**同目录下的 `{id}.json`**：

1. 浏览器打开 `https://api.anitabi.cn/bangumi/<id>/points/detail`
2. 另存为 `{id}.json`，放到脚本同目录
3. 运行 `python anitabi_GoogleMaps.py <id> --offline`

注意：`--offline` 时如果只有 `{id}.json`（点位数组）而没有作品信息，输出文件名会退回用 bangumi_id。

## 相比旧版的变化

| 问题 | 旧版 | 现在 |
| --- | --- | --- |
| 依赖 | 需要 `requests` | 纯标准库 |
| 参数 | 只能交互输入 | 位置参数 + `-o` / `--outdir` / `--offline` / `--timeout` / `--retries` |
| 超时与重试 | 无（可能一直挂着） | 默认 20s 超时 + 指数退避重试 |
| KML 命名空间 | `http://www.opengis.net`（非规范） | `http://www.opengis.net/kml/2.2` |
| 文档标题 | 无 `<Document><name>` | 有 |
| 文件名 | 直接拿作品名，遇 `Re:Zero` 这类标题在 Windows 上写文件失败 | 过滤 `<>:"/\|?*`、保留名、超长、首尾点号 |
| 缺字段 | `item['geo']` / `item['id']` 直接 KeyError | 跳过并统计无效点位 |
| XML 安全 | 图片 URL 未转义，可能截断属性或提前结束 CDATA | 属性转义 + CDATA 拆断 |
| 写入 | 直接覆盖，中断会留半个文件 | 先写 `.tmp` 再 `os.replace` |
| 校验 | 无 | XML 格式、坐标顺序都有测试覆盖 |

## 测试

```bash
python -m unittest discover -s tests -v
```

23 个用例全部离线：HTTP 调用被替换成假实现，覆盖 KML 结构/转义/坐标顺序、文件名清洗、重试与回退、端到端生成与错误码。

## 已知限制

- 只导出点位（Placemark），不含路线、图片下载和作品封面。
- 坐标按 anitabi 返回的 `[纬度, 经度]` 转成 KML 的 `经度,纬度,0`，不做坐标系纠偏。
- 接口没有公开文档，字段缺失时会跳过该点位而不是中断整个转换。
- Windows 控制台默认代码页不是 UTF-8 时会尝试切到 65001；切不动时输出里的中文会变成 `?`，但不会抛 `UnicodeEncodeError` 中断转换。重定向到文件时始终是 UTF-8。

## 我创建的部分作品地图

1. 路人女主 - https://www.google.com/maps/d/viewer?mid=19CAvroXYoTebZ4wZ9tvg9XvoRiL6XvE&usp=sharing
2. LoveLive! 星团 - https://www.google.com/maps/d/viewer?mid=1_shPyo5kTGYvp5Q2BGH9X8e36bfrk94&usp=sharing
3. 刀剑神域SAO - https://www.google.com/maps/d/viewer?mid=1V2zw6YQYttRrdspKxNwpfAsRh4NLeys&usp=sharing
4. MyGo&Mujica - https://www.google.com/maps/d/viewer?mid=1ty5EjnQo1LLCgDqHdhwijhZDN6ZdDlM&usp=sharing
5. 京吹 - https://www.google.com/maps/d/viewer?mid=1XfU4x6KMA1FdQ2180QJ5Ua_wgYQIdTI&usp=sharing
6. 败犬女主 - https://www.google.com/maps/d/viewer?mid=1CNXd5Xkkh2Qf0QZPNG7azKCJC-aCDjE&usp=sharing
7. 孤独摇滚 - https://www.google.com/maps/d/viewer?mid=13FySg0WBFmL4ptTyzw5CDndq0NWQdkc&usp=sharing

## 许可证

MIT，详见 [LICENSE](LICENSE)。
