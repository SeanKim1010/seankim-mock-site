# SeanKim 모의고사 배포 사이트 - Render 배포용

## GitHub 업로드
1. GitHub 로그인
2. New repository 생성
3. Add file → Upload files
4. 이 폴더 파일 전부 업로드
5. Commit changes

## Render 배포
1. Render 로그인
2. New + 클릭
3. Web Service 선택
4. GitHub 저장소 연결
5. Build Command: pip install -r requirements.txt
6. Start Command: gunicorn app:app
7. Create Web Service 클릭
8. 배포 후 공개 주소 확인

## 관리자 계정
- 아이디: admin
- 비밀번호: 1234
