# SeanKim Mock Archive

수학 / 과학탐구 모의고사 배포 사이트입니다.

## 관리자 로그인
- 주소: `/admin/login`
- 아이디: `admin`
- 비밀번호: `1234`

## Render 설정
- Service Type: Web Service
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

## GitHub에 올릴 파일 구조
app.py  
requirements.txt  
render.yaml  
Procfile  
templates/  
static/  
uploads/  
