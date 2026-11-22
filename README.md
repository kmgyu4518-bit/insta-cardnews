# insta-cardnews

경제·투자 카드뉴스를 인스타그램에 캐러셀로 게시하는 연습용 저장소입니다.

## 구조

```
cards/
  2026-11-23/
    01.jpg ... 05.jpg   # 카드 이미지 (JPEG, 같은 비율)
    caption.txt         # 캡션
publish.py              # 게시 스크립트
.github/workflows/publish.yml
```

## 게시 방법

1. 승인된 카드와 캡션을 `cards/<날짜>/`에 올립니다.
2. Actions 탭 > Publish card news > Run workflow에서 날짜를 입력해 실행합니다.

- 수동 실행만 됩니다. 승인 전에는 실행하지 않습니다.
- 실패하면 원인만 로그에 남기고 재시도하지 않습니다.
- 게시 전에 24시간 게시 사용량을 조회하고, 50건 이상이면 중단합니다.

## 필요한 Secrets

- `IG_ACCESS_TOKEN`: Meta 앱에서 발급한 토큰
- `IG_USER_ID`: 인스타그램 계정 ID

토큰은 저장소 파일에 절대 넣지 않습니다.
