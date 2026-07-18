self.cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
cv2.VideoCapture(1)     
카메라마다 번호가 다를 수 있음

# 다른 카메라 연결할 때 이 코드를 삽입하여 카메라 번호를 확인하여야 함
for i in range(5):
    cap = cv2.VideoCapture(i)

    if cap.isOpened():
        print(f"{i}번 카메라 사용")
        self.cap = cap
        break
  [출력] ex) 이렇게 나온다면 cv2.VideoCapture(1) 이렇게 설정하면 됨
  0번 실패
  1번 성공

# 무선 카메라를 사용할 때: 카메라의 무선 IP 스트리밍 주소를 직접 입력
ex) self.cap = cv2.VideoCapture("rtsp://192.168.0.10:554/stream")

# 좌우 반전 문제 해결하는 법
def show_camera(self): 함수에서 frame = cv2.flip(frame, 1) 코드를 주석 처리 or 삭제


# 실행할 때 필요한 것
1. python, OpenCV, pillow가 설치 되어있어야 함
2. 카메라 사용 권한 허용
3. 카메라 번호 맞으면 실행 가능
