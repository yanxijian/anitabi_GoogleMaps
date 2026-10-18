"""anitabi_GoogleMaps 的单元测试。

全部离线：HTTP 调用被替换成假实现，输出文件写到临时目录。

    python -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anitabi_GoogleMaps as aim  # noqa: E402

KML_NS = "{http://www.opengis.net/kml/2.2}"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def fake_open_factory(handler):
    def _open(request, timeout=None, **kwargs):
        return handler(request, timeout)
    return _open


class BuildKmlTests(unittest.TestCase):
    def test_coordinates_are_longitude_latitude(self):
        points = [{"id": 1, "geo": [35.0, 139.0], "name": "Tokyo", "image": ""}]
        kml, used, skipped = aim.build_kml(points, "作品")
        self.assertEqual((used, skipped), (1, 0))
        self.assertIn("<coordinates>139.000000,35.000000,0</coordinates>", kml)

    def test_namespace_and_document_name(self):
        kml, _, _ = aim.build_kml([{"id": 2, "geo": [1.0, 2.0], "name": "X"}], "标题")
        self.assertIn('<kml xmlns="http://www.opengis.net/kml/2.2">', kml)
        self.assertIn("<name>标题</name>", kml)

    def test_output_is_well_formed_xml(self):
        points = [
            {"id": 1, "geo": [35.0, 139.0], "cn": "東京 & <塔>", "image": "https://e.com/a.png"},
            {"id": 2, "geo": [-33.9, 151.2], "name": "Sydney"},
        ]
        kml, used, _ = aim.build_kml(points, "A & B")
        self.assertEqual(used, 2)
        root = ET.fromstring(kml)
        placemarks = root.findall(f"{KML_NS}Document/{KML_NS}Placemark")
        self.assertEqual(len(placemarks), 2)
        self.assertEqual(placemarks[0].find(f"{KML_NS}name").text, "東京 & <塔>")

    def test_attribute_escaping_in_image_url(self):
        points = [{"id": 1, "geo": [1.0, 2.0], "name": "N", "image": 'https://e.com/a.png?x="1"&y=2'}]
        kml, _, _ = aim.build_kml(points, "t")
        self.assertIn("&quot;", kml)
        self.assertIn("&amp;", kml)
        self.assertNotIn('src="https://e.com/a.png?x="1"', kml)

    def test_cdata_terminator_never_ends_the_section(self):
        # URL 先做属性转义，"]]>" 变成 "]]&gt;"，不会提前闭合 CDATA。
        points = [{"id": 1, "geo": [1.0, 2.0], "name": "N", "image": "https://e.com/]]>.png"}]
        kml, _, _ = aim.build_kml(points, "t")
        self.assertIn("]]&gt;", kml)
        self.assertNotIn("]]>.png", kml)
        ET.fromstring(kml)  # 仍然是合法 XML

    def test_cdata_escape_splits_terminator(self):
        self.assertEqual(aim.cdata_escape("a]]>b"), "a]]]]><![CDATA[>b")

    def test_invalid_points_are_skipped(self):
        points = [
            {"id": 1, "geo": [1.0, 2.0], "name": "ok"},
            {"id": 2, "name": "no geo"},
            {"id": 3, "geo": [1.0], "name": "short"},
            {"id": 4, "geo": ["x", "y"], "name": "nan"},
            {"id": 5, "geo": [999.0, 2.0], "name": "out of range"},
            "not a dict",
            {"id": 6, "geo": [1.0, 2.0], "name": "also ok"},
        ]
        _, used, skipped = aim.build_kml(points, "t")
        self.assertEqual(used, 2)
        self.assertEqual(skipped, 5)

    def test_fallback_name_is_used(self):
        kml, _, _ = aim.build_kml([{"id": 1, "geo": [1.0, 2.0]}], "t")
        self.assertIn(f"<name>{aim.FALLBACK_NAME}</name>", kml)

    def test_empty_points_still_valid(self):
        kml, used, _ = aim.build_kml([], "空")
        self.assertEqual(used, 0)
        ET.fromstring(kml)


class ConsoleTests(unittest.TestCase):
    """Windows 控制台不是 UTF-8 时，中文提示不能把程序打崩。"""

    def test_survives_streams_without_reconfigure(self):
        class NoReconfigure:
            def write(self, text):
                return len(text)

        original_out, original_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = NoReconfigure()
        try:
            aim._configure_console()  # 不应抛异常
        finally:
            sys.stdout, sys.stderr = original_out, original_err

    def test_requests_replacement_errors(self):
        calls = []

        class Recorder:
            def reconfigure(self, **kwargs):
                calls.append(kwargs)

        original_out, original_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = Recorder()
        try:
            aim._configure_console()
        finally:
            sys.stdout, sys.stderr = original_out, original_err

        self.assertEqual(len(calls), 2)
        for kwargs in calls:
            self.assertEqual(kwargs.get("errors"), "replace")


class FilenameTests(unittest.TestCase):
    def test_windows_invalid_characters_removed(self):
        name = aim.safe_filename('Re:Zero / 第2季? <特别篇>')
        for bad in '<>:"/\\|?*':
            self.assertNotIn(bad, name)
        self.assertTrue(name)

    def test_reserved_device_names_are_prefixed(self):
        self.assertEqual(aim.safe_filename("CON"), "_CON")
        self.assertEqual(aim.safe_filename("com1"), "_com1")

    def test_trailing_dots_and_spaces_stripped(self):
        self.assertEqual(aim.safe_filename("  name.  "), "name")

    def test_empty_becomes_placeholder(self):
        self.assertEqual(aim.safe_filename("   "), "bangumi")

    def test_length_is_bounded(self):
        self.assertLessEqual(len(aim.safe_filename("x" * 500)), 120)


class FetchTests(unittest.TestCase):
    def setUp(self):
        self._orig_open = aim._open
        self._orig_sleep = aim._sleep
        aim._sleep = lambda seconds: None

    def tearDown(self):
        aim._open = self._orig_open
        aim._sleep = self._orig_sleep

    def test_retries_then_succeeds(self):
        calls = {"n": 0}

        def handler(request, timeout):
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError("connection reset")
            return FakeResponse(b'[{"id": 1, "geo": [1.0, 2.0]}]')

        aim._open = fake_open_factory(handler)
        data = aim.fetch_json("https://example.invalid", retries=2)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(data[0]["id"], 1)

    def test_raises_after_exhausting_retries(self):
        aim._open = fake_open_factory(lambda request, timeout: (_ for _ in ()).throw(OSError("boom")))
        with self.assertRaises(aim.AnitabiError):
            aim.fetch_json("https://example.invalid", retries=1)

    def test_invalid_json_raises(self):
        aim._open = fake_open_factory(lambda request, timeout: FakeResponse(b"not json"))
        with self.assertRaises(aim.AnitabiError):
            aim.fetch_json("https://example.invalid", retries=0)


class EndToEndOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self._cwd)
        self.tmp.cleanup()

    def _write_points(self, bangumi_id, points):
        with open(f"{bangumi_id}.json", "w", encoding="utf-8") as handle:
            json.dump(points, handle, ensure_ascii=False)

    def test_offline_conversion_creates_kml(self):
        self._write_points("123", [{"id": 7, "geo": [34.7, 135.5], "cn": "大阪"}])
        code = aim.main(["123", "--offline"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile("123.kml"), os.listdir("."))
        with open("123.kml", encoding="utf-8") as handle:
            content = handle.read()
        ET.fromstring(content)
        self.assertIn("<coordinates>135.500000,34.700000,0</coordinates>", content)
        self.assertIn("<name>大阪</name>", content)

    def test_offline_falls_back_to_local_cache_when_network_fails(self):
        self._write_points("456", [{"id": 8, "geo": [1.0, 2.0], "name": "N"}])
        original = aim._open
        aim._open = fake_open_factory(lambda request, timeout: (_ for _ in ()).throw(OSError("down")))
        try:
            points = aim.load_points("456", offline=False, timeout=1, retries=0)
        finally:
            aim._open = original
        self.assertEqual(points[0]["id"], 8)

    def test_output_path_is_honoured(self):
        self._write_points("789", [{"id": 9, "geo": [1.0, 2.0], "name": "N"}])
        code = aim.main(["789", "--offline", "-o", "custom.kml"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile("custom.kml"))

    def test_output_with_multiple_ids_is_rejected(self):
        self.assertEqual(aim.main(["1", "2", "-o", "x.kml", "--offline"]), 2)

    def test_missing_local_data_returns_failure(self):
        self.assertEqual(aim.main(["does-not-exist", "--offline"]), 1)

    def test_points_without_coordinates_fail(self):
        self._write_points("empty", [{"id": 1, "name": "no geo"}])
        self.assertEqual(aim.main(["empty", "--offline"]), 1)


class SourceEncodingTests(unittest.TestCase):
    """守护文件编码：被外部工具二次编码成乱码时立刻失败。

    正常的中文源文件无法用 latin-1 表示；一旦被 UTF-8 -> Latin-1 -> UTF-8
    转坏，全文就只剩 Latin-1 能表示的字符，这里的断言就会失败。
    """

    def assert_clean_utf8(self, path: str) -> None:
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8")
        self.assertTrue(any(ord(ch) > 127 for ch in text), f"{path} 里没有中文，可能已损坏")
        try:
            text.encode("latin-1")
        except UnicodeEncodeError:
            return
        self.fail(f"{path} 疑似被二次编码（全文可用 latin-1 表示）")

    def test_module_literals_are_readable_chinese(self):
        self.assertEqual(aim.FALLBACK_NAME, "未命名地点")
        self.assertEqual(aim.safe_filename("海阔天空"), "海阔天空")

    def test_module_source_is_clean_utf8(self):
        self.assert_clean_utf8(aim.__file__)

    def test_test_file_itself_is_clean_utf8(self):
        self.assert_clean_utf8(__file__)


if __name__ == "__main__":
    unittest.main()
