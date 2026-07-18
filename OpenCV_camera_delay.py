# threading 라이브러리 추가로 카메라를 백그라운드에서 독립적으로 제어

import cv2 # open cv
from PIL import Image, ImageTk # open cv
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading  # [추가] 딜레이 제거를 위한 쓰레드 라이브러리
import time


class RCCarController: # RC카 GuI 프로그램 클래스
    def __init__(self, window): # 가장 먼저 호출되는 생성자
        self.window = window
        self.window.protocol("WM_DELETE_WINDOW", self.close_program) # 프로그램 종료 시 카메라 종료
        self.window.title("RC Car Control")
        self.window.geometry("900x600")
        self.window.resizable(False, False)

        self.cap = None # open cv
        self.camera_job = None # open cv
        self.current_frame = None # open cv
        self.latest_frame = None  # [추가] 쓰레드에서 읽은 최신 프레임 저장용
        self.connected = False
        self.camera_on = False
        self.camera_thread_running = False  # [추가] 쓰레드 제어 플래그
        self.current_direction = "정지"

        self.create_styles()
        self.create_layout()

        # 키보드 조작
        self.window.bind("<KeyPress-w>", lambda event: self.move_forward())
        self.window.bind("<KeyPress-s>", lambda event: self.move_backward())
        self.window.bind("<KeyPress-a>", lambda event: self.turn_left())
        self.window.bind("<KeyPress-d>", lambda event: self.turn_right())
        self.window.bind("<KeyPress-space>", lambda event: self.stop_car())

    def create_styles(self): # GUI 스타일 설정(버튼, 글씨)
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Title.TLabel", font=("맑은 고딕", 22, "bold"))
        style.configure("Status.TLabel", font=("맑은 고딕", 11))
        style.configure("Control.TButton", font=("맑은 고딕", 13, "bold"), padding=10)
        style.configure("Stop.TButton", font=("맑은 고딕", 13, "bold"), padding=10)

    def create_layout(self): # GUI 전체 화면 배치
        # 전체 상단 제목
        title_frame = ttk.Frame(self.window, padding=15)
        title_frame.pack(fill="x")

        title_label = ttk.Label(title_frame, text="RC CAR CONTROL SYSTEM", style="Title.TLabel")
        title_label.pack(side="left")

        self.connection_label = ttk.Label(title_frame, text="● 연결 안 됨", foreground="red", font=("맑은 고딕", 12, "bold"))
        self.connection_label.pack(side="right")

        # 메인 영역
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill="both", expand=True)

        # 왼쪽: 카메라 영역
        camera_frame = ttk.LabelFrame(main_frame, text="카메라 화면", padding=10)
        camera_frame.grid(row=0, column=0, padx=(0, 15), sticky="nsew")

        self.camera_canvas = tk.Canvas(camera_frame, width=520, height=390, bg="#1f1f1f", highlightthickness=0)
        self.camera_canvas.pack()

        self.camera_text = self.camera_canvas.create_text(260, 195, text="카메라가 꺼져 있습니다.", fill="white", font=("맑은 고딕", 16))

        camera_button_frame = ttk.Frame(camera_frame)
        camera_button_frame.pack(pady=12)

        self.camera_button = ttk.Button(camera_button_frame, text="카메라 켜기", command=self.toggle_camera)
        self.camera_button.grid(row=0, column=0, padx=5)

        capture_button = ttk.Button(camera_button_frame, text="화면 캡처", command=self.capture_screen)
        capture_button.grid(row=0, column=1, padx=5)

        # 오른쪽: 조종기 영역
        control_frame = ttk.LabelFrame(main_frame, text="RC카 조종기", padding=15)
        control_frame.grid(row=0, column=1, sticky="nsew")

        # 연결 버튼
        self.connect_button = ttk.Button(control_frame, text="RC카 연결", command=self.toggle_connection)
        self.connect_button.pack(fill="x", pady=(0, 20))

        # 방향 버튼 영역
        direction_frame = ttk.Frame(control_frame)
        direction_frame.pack(pady=10)

        forward_button = ttk.Button(direction_frame, text="▲\n전진", width=10, style="Control.TButton", command=self.move_forward)
        forward_button.grid(row=0, column=1, padx=5, pady=5)

        left_button = ttk.Button(direction_frame, text="◀\n좌회전", width=10, style="Control.TButton", command=self.turn_left)
        left_button.grid(row=1, column=0, padx=5, pady=5)

        stop_button = ttk.Button(direction_frame, text="■\n정지", width=10, style="Stop.TButton", command=self.stop_car)
        stop_button.grid(row=1, column=1, padx=5, pady=5)

        right_button = ttk.Button(direction_frame, text="▶\n우회전", width=10, style="Control.TButton", command=self.turn_right)
        right_button.grid(row=1, column=2, padx=5, pady=5)

        backward_button = ttk.Button(direction_frame, text="▼\n후진", width=10, style="Control.TButton", command=self.move_backward)
        backward_button.grid(row=2, column=1, padx=5, pady=5)

        # 속도 조절
        speed_frame = ttk.LabelFrame(control_frame, text="속도 조절", padding=10)
        speed_frame.pack(fill="x", pady=20)

        self.speed_value = tk.IntVar(value=50)
        self.speed_scale = ttk.Scale(speed_frame, from_=0, to=100, orient="horizontal", variable=self.speed_value, command=self.change_speed)
        self.speed_scale.pack(fill="x")

        self.speed_label = ttk.Label(speed_frame, text="현재 속도: 50%", font=("맑은 고딕", 11, "bold"))
        self.speed_label.pack(pady=(8, 0))

        # 현재 상태
        status_frame = ttk.LabelFrame(control_frame, text="주행 상태", padding=10)
        status_frame.pack(fill="x")

        self.direction_label = ttk.Label(status_frame, text="방향: 정지", style="Status.TLabel")
        self.direction_label.pack(anchor="w")

        self.time_label = ttk.Label(status_frame, text="최근 명령: 없음", style="Status.TLabel")
        self.time_label.pack(anchor="w", pady=(5, 0))

        # 키보드 안내
        keyboard_label = ttk.Label(control_frame, text="키보드: W 전진 / S 후진 / A 좌회전 / D 우회전 / Space 정지", wraplength=260, justify="center", foreground="#555555")
        keyboard_label.pack(pady=(20, 0))

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=0)

    def toggle_connection(self): # RC카와 연결 및 해제를 수행
        self.connected = not self.connected
        if self.connected:
            self.connection_label.config(text="● RC카 연결됨", foreground="green")
            self.connect_button.config(text="연결 해제")
            self.update_status("RC카 연결")
        else:
            self.connection_label.config(text="● 연결 안 됨", foreground="red")
            self.connect_button.config(text="RC카 연결")
            self.stop_car()
            self.update_status("RC카 연결 해제")

    def check_connection(self): # RC카 연결 확인 or 경고장 출력
        if not self.connected:
            messagebox.showwarning("연결 오류", "먼저 RC카를 연결해 주세요.")
            return False
        return True

    def move_forward(self): # RC카 전진 명령
        if not self.check_connection(): return
        self.current_direction = "전진"
        self.direction_label.config(text="방향: 전진")
        self.update_status("전진 명령")
        self.send_command("FORWARD")

    def move_backward(self): # RC카 후진 명령
        if not self.check_connection(): return
        self.current_direction = "후진"
        self.direction_label.config(text="방향: 후진")
        self.update_status("후진 명령")
        self.send_command("BACKWARD")

    def turn_left(self): # RC카 좌회전 명령
        if not self.check_connection(): return
        self.current_direction = "좌회전"
        self.direction_label.config(text="방향: 좌회전")
        self.update_status("좌회전 명령")
        self.send_command("LEFT")

    def turn_right(self): # RC카 우회전 명령
        if not self.check_connection(): return
        self.current_direction = "우회전"
        self.direction_label.config(text="방향: 우회전")
        self.update_status("우회전 명령")
        self.send_command("RIGHT")

    def stop_car(self): # RC카 정지 명령
        self.current_direction = "정지"
        self.direction_label.config(text="방향: 정지")
        self.update_status("정지 명령")
        if self.connected:
            self.send_command("STOP")

    def change_speed(self, value): # 속도 슬라이더 값 변경
        speed = int(float(value))
        self.speed_label.config(text=f"현재 속도: {speed}%")
        if self.connected:
            self.send_command(f"SPEED:{speed}")

    def toggle_camera(self): # 카메라 켜기/끄기
        if not self.camera_on:
            print("카메라 연결 시도")
            
            camera_source = 0 
            
            self.cap = cv2.VideoCapture("http://192.168.0.110:8080/video") # IP주소나 번호 삽입
            
            # OpenCV 자체 내부 버퍼 크기 최소화 (IP 카메라 환경용)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self.cap.isOpened():
                messagebox.showerror("카메라 오류", "카메라를 열 수 없습니다.")
                self.cap = None
                return

            print("카메라 열기 성공")
            self.camera_on = True
            self.camera_button.config(text="카메라 끄기")

            # [수정] 백그라운드에서 프레임을 무한 주입받는 쓰레드 가동
            self.camera_thread_running = True
            self.latest_frame = None
            self.grab_thread = threading.Thread(target=self.update_frame_background, daemon=True)
            self.grab_thread.start()

            # GUI에 그리는 루프 시작
            self.show_camera()
        else:
            self.stop_camera()

    def update_frame_background(self):
        """ [추가] 백그라운드에서 OpenCV 버퍼를 강제로 비우며 가장 최신 프레임만 선점하는 함수 """
        while self.camera_thread_running:
            if self.cap is not None and self.cap.isOpened():
                success, frame = self.cap.read()
                if success:
                    self.latest_frame = frame
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.1)

    def show_camera(self): # 백그라운드 쓰레드가 낚아챈 최신 화면을 GUI에 매핑
        if not self.camera_on:
            return

        # 최신 프레임이 아직 없으면 대기 후 재시도
        if self.latest_frame is None:
            self.camera_job = self.window.after(10, self.show_camera)
            return

        # 쓰레드가 확보한 가장 최신 프레임 복사 복사
        frame = self.latest_frame.copy()

        # GUI 카메라 영역 크기에 맞추기
        frame = cv2.resize(frame, (520, 390))
        self.current_frame = frame.copy()

        # OpenCV BGR -> RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        tkinter_image = ImageTk.PhotoImage(image=pil_image)

        self.camera_canvas.delete("all")
        self.camera_canvas.create_image(0, 0, anchor="nw", image=tkinter_image)
        self.camera_canvas.image = tkinter_image

        # 약 30fps 속도로 화면을 갱신하되 최신 데이터만 미러링
        self.camera_job = self.window.after(30, self.show_camera)

    def stop_camera(self): # 카메라 종료
        self.camera_on = False
        self.camera_thread_running = False # 쓰레드 종료

        if self.camera_job is not None:
            self.window.after_cancel(self.camera_job)
            self.camera_job = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.current_frame = None
        self.latest_frame = None

        self.camera_canvas.delete("all")
        self.camera_text = self.camera_canvas.create_text(260, 195, text="카메라가 꺼져 있습니다.", fill="white", font=("맑은 고딕", 16))
        self.camera_button.config(text="카메라 켜기")
        self.update_status("카메라 끄기")

    def capture_screen(self): # 현재 카메라 화면 이미지 파일로 저장
        if not self.camera_on or self.current_frame is None:
            messagebox.showwarning("카메라 오류", "카메라를 먼저 켜 주세요.")
            return

        filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
        success = cv2.imwrite(filename, self.current_frame)

        if success:
            messagebox.showinfo("화면 캡처", f"사진이 저장되었습니다.\n\n파일명: {filename}")
            self.update_status("카메라 화면 캡처")
        else:
            messagebox.showerror("저장 오류", "사진을 저장하지 못했습니다.")

    def close_program(self): # 프로그램 종료
        self.stop_camera()
        self.window.destroy()

    def send_command(self, command): # RC카에게 명령 전송
        speed = self.speed_value.get()
        print(f"명령: {command}, 속도: {speed}%")

    def update_status(self, command): # 최근 실행 명령과 시간을 GUI에 표시
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=f"최근 명령: {command} ({current_time})")


if __name__ == "__main__":
    root = tk.Tk()
    app = RCCarController(root)
    root.mainloop()
