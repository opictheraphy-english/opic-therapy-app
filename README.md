# OPIc Therapy Clinic

Streamlit 기반 오픽 모의고사 · AI 진단 앱입니다.

## 로컬 실행

```bash
cd opic-therapy-app
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

브라우저: `http://localhost:8501`

## API 키

`.streamlit/secrets.toml`에 다음을 넣거나, 환경 변수 `GEMINI_API_KEY`를 설정하세요.

```toml
GEMINI_API_KEY = "여기에_키"
```

## Docker로 실행

```bash
docker build -t opic-therapy .
docker run --rm -p 8501:8501 -e GEMINI_API_KEY="여기에_키" opic-therapy
```

접속: `http://localhost:8501`

## Streamlit Community Cloud

GitHub에 푸시한 뒤 [share.streamlit.io](https://share.streamlit.io)에서 저장소를 연결하고, Secrets에 `GEMINI_API_KEY`를 등록하면 됩니다.
