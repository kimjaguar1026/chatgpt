# PDF 분할/번역 테스트 방법

1) `input/` 폴더에 OCR 완료 PDF를 넣습니다.
2) 아래 명령으로 텍스트 추출을 실행합니다.

```bash
python tools/translate_pdf.py ./input/your.pdf --output ./output
```

LibreTranslate 서버가 있다면 번역까지 실행할 수 있습니다.

```bash
python tools/translate_pdf.py ./input/your.pdf \
  --output ./output \
  --translate \
  --libretranslate-url http://localhost:5000/translate
```
