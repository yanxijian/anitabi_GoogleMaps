# anitabi → Google My Maps

**한국어** · [English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[anitabi](https://www.anitabi.cn/map)의 성지순례 지도를 **KML**로 내보내고, [Google My Maps](https://www.google.com/maps/d/)에 가져와 구글 지도에서 보기 위한 도구입니다.

Python 3.8 이상 표준 라이브러리만 씁니다. **`requests`를 설치할 필요가 없습니다**.

## 사용법

```bash
# bangumi_id 하나 지정(여러 개도 가능)
python anitabi_GoogleMaps.py 331884

# 여러 작품을 한 번에 내보내기
python anitabi_GoogleMaps.py 331884 4912

# 출력 파일 / 출력 디렉터리 지정
python anitabi_GoogleMaps.py 331884 -o bocchi-the-rock.kml
python anitabi_GoogleMaps.py 331884 --outdir maps

# 대화형 모드(id를 주지 않으면 진입. Enter 또는 q로 종료)
python anitabi_GoogleMaps.py
```

`bangumi_id`는 작품 페이지 URL에 있는 숫자입니다. <https://www.anitabi.cn/map>을 열고 작품을 검색한 뒤 주소창의 `bangumi/<id>`를 보면 됩니다.

가져오는 순서: [Google My Maps](https://www.google.com/maps/d/)를 연다 → 새 지도를 만든다 → 레이어를 추가한다 → 가져오기 → 생성된 `.kml`을 고른다.

## 네트워크가 불안정할 때

anitabi API는 환경에 따라 시간 초과가 나거나 403을 돌려줍니다. 스크립트는 재시도하고(`--retries`, 기본 2회. `--timeout`, 기본 20초) 그래도 안 되면 **스크립트와 같은 디렉터리의 `{id}.json`**으로 넘어갑니다:

1. 브라우저에서 `https://api.anitabi.cn/bangumi/<id>/points/detail`을 연다
2. 스크립트와 같은 디렉터리에 `{id}.json`으로 저장한다
3. `python anitabi_GoogleMaps.py <id> --offline`을 실행한다

주의: `--offline`에서 `{id}.json`(지점 배열)만 있고 작품 정보가 없으면 출력 파일 이름은 bangumi_id로 대체됩니다.

## 이전 버전에서 바뀐 점

| 문제 | 이전 | 지금 |
| --- | --- | --- |
| 의존성 | `requests` 필요 | 표준 라이브러리만 |
| 인자 | 대화형 입력뿐 | 위치 인자에 더해 `-o` / `--outdir` / `--offline` / `--timeout` / `--retries` |
| 시간 초과와 재시도 | 없음(계속 멈춰 있을 수 있음) | 기본 20초 시간 초과와 지수 백오프 |
| KML 네임스페이스 | `http://www.opengis.net`(규격 아님) | `http://www.opengis.net/kml/2.2` |
| 문서 제목 | `<Document><name>` 없음 | 있음 |
| 파일 이름 | 작품명을 그대로 사용. `Re:Zero` 같은 제목은 Windows에서 파일 쓰기 실패 | `<>:"/\|?*`, 예약어, 끝의 점, 너무 긴 이름을 정리 |
| 빠진 항목 | `item['geo']` / `item['id']`에서 KeyError | 해당 지점을 건너뛰고 개수만 기록 |
| XML 안전성 | 이미지 URL을 이스케이프하지 않아 속성이 끊기거나 CDATA가 일찍 끝날 수 있음 | 속성 이스케이프와 CDATA 분할 |
| 쓰기 | 바로 덮어써서 중단되면 반쯤 쓴 파일이 남음 | `.tmp`에 쓴 뒤 `os.replace` |
| 검증 | 없음 | XML 형태와 좌표 순서를 테스트로 보장 |

## 테스트

```bash
python -m unittest discover -s tests -v
```

23개 모두 오프라인입니다. HTTP 호출을 가짜 구현으로 바꾸고 KML 구조·이스케이프·좌표 순서, 파일 이름 정리, 재시도와 대체 경로, 끝에서 끝까지의 생성과 종료 코드를 확인합니다.

## 알려진 한계

- 내보내는 것은 지점(Placemark)뿐입니다. 경로, 이미지 다운로드, 작품 표지는 포함하지 않습니다.
- 좌표는 anitabi가 주는 `[위도, 경도]`를 KML의 `경도,위도,0`으로 바꿀 뿐이고 측지계 보정은 하지 않습니다.
- API에 공개 문서가 없어, 항목이 빠진 지점은 전체 변환을 멈추지 않고 건너뜁니다.
- Windows 콘솔의 코드 페이지가 UTF-8이 아니면 65001로 바꾸려 시도합니다. 바꾸지 못하면 비ASCII가 `?`로 나오지만 `UnicodeEncodeError`로 변환이 중단되지는 않습니다. 파일로 리다이렉트하면 항상 UTF-8입니다.

## 제가 만든 지도 일부

1. 사에카노 (Saekano) - https://www.google.com/maps/d/viewer?mid=19CAvroXYoTebZ4wZ9tvg9XvoRiL6XvE&usp=sharing
2. 러브라이브! 슈퍼스타!! - https://www.google.com/maps/d/viewer?mid=1_shPyo5kTGYvp5Q2BGH9X8e36bfrk94&usp=sharing
3. 소드 아트 온라인 - https://www.google.com/maps/d/viewer?mid=1V2zw6YQYttRrdspKxNwpfAsRh4NLeys&usp=sharing
4. BanG Dream! It's MyGO!!!!! & Ave Mujica - https://www.google.com/maps/d/viewer?mid=1ty5EjnQo1LLCgDqHdhwijhZDN6ZdDlM&usp=sharing
5. 울려라! 유포니엄 - https://www.google.com/maps/d/viewer?mid=1XfU4x6KMA1FdQ2180QJ5Ua_wgYQIdTI&usp=sharing
6. 패배 히로인이 너무 많아! - https://www.google.com/maps/d/viewer?mid=1CNXd5Xkkh2Qf0QZPNG7azKCJC-aCDjE&usp=sharing
7. 봇치 더 록! - https://www.google.com/maps/d/viewer?mid=13FySg0WBFmL4ptTyzw5CDndq0NWQdkc&usp=sharing

## 라이선스

MIT. [LICENSE](LICENSE)를 보세요.
