# 파이썬 공식 이미지를 기반으로 합니다.
FROM python:3.9-slim-buster

# 작업 디렉토리를 설정합니다.
WORKDIR /app

# 파이썬 종속성 파일을 복사합니다.
# requirements.txt 파일에 필요한 라이브러리 목록을 적어둡니다.
COPY requirements.txt .

# 파이썬 종속성을 설치합니다.
RUN pip install --no-cache-dir -r requirements.txt

# JAV 이미지 다운로드 스크립트를 복사합니다.
COPY dmm_cover_downloader.py .

# 파일 변경을 감지하고 스크립트를 실행할 진입점 스크립트를 복사합니다.
COPY watch_and_run.py .

# 컨테이너가 시작될 때 watch_and_run.py 스크립트를 실행합니다.
CMD ["python", "watch_and_run.py"]
