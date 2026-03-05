import json
import requests # pyright: ignore[reportMissingModuleSource]
import html

while True:
    bangumi_id = input("请输入 bangumi_id (输入 q 退出): ").strip()
    if bangumi_id.lower() == 'q':
        break
    
    map_data_url = f"https://api.anitabi.cn/bangumi/{bangumi_id}/points/detail"
    try:
        response = requests.get(map_data_url)
        response.raise_for_status()
        map_data = response.json()
    except requests.RequestException as e:
        print(f"获取地图数据失败: {e}，尝试读取本地文件")
        # 尝试从本地 json 文件读取（自己用浏览器访问后保存到脚本同一目录，文件名格式 bangumi_id.json ）
        try:
            with open(f"{bangumi_id}.json", "r", encoding="utf-8") as jf:
                map_data = json.load(jf)
                print(f"已从本地 {bangumi_id}.json 加载数据")
        except (FileNotFoundError, json.JSONDecodeError) as fe:
            print(f"本地数据加载失败: {fe}")
            continue
    
    bangumi_info_url = f"https://api.anitabi.cn/bangumi/{bangumi_id}/lite"
    try:
      response = requests.get(bangumi_info_url)
      response.raise_for_status()
      bangumi_info = response.json()
    except requests.RequestException as e:
      print(f"获取作品信息失败: {e}")
      continue
    
    # 构建 KML 字符串
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net">
  <Document>
"""
    
    for item in map_data:
        # 做下转义处理，确保符合 XML 要求
        place_name = html.escape(item.get('cn') or item.get('name', '未命名地点'), quote=False)
        # anitabi 的 geo 格式是 [纬度, 经度]，KML 需要 "经度,纬度"
        lat, lng = item['geo']
        img_url = item.get('image', '')
        
        kml_content += f"""
    <Placemark>
      <name>{place_name}</name>
      <description><![CDATA[<img src="{img_url}" width="200" /><br/>ID: {item['id']}]]></description>
      <Point>
        <coordinates>{lng},{lat},0</coordinates>
      </Point>
    </Placemark>"""
    
    kml_content += """
  </Document>
</kml>
"""
    
    # 保存文件
    bangumi_name = bangumi_info.get('cn') or bangumi_info.get('title') or bangumi_id
    filename = f"{bangumi_name}.kml"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(kml_content)
    
    print(f"数据已保存到 {filename}")
