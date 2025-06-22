import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import dmm_cover_downloader # dmm_cover_downloader.py 파일을 임포트

# 감시할 디렉토리 (Docker 컨테이너 내부의 마운트된 JAV 폴더 경로)
# dmm_cover_downloader.py와 동일하게 설정해야 합니다.
PATH_TO_WATCH = "/jav_videos"

class MyHandler(FileSystemEventHandler):
    """
    파일 시스템 이벤트(생성, 수정, 삭제 등)를 처리하는 핸들러 클래스입니다.
    """
    def on_created(self, event):
        """
        파일 또는 디렉토리가 생성될 때 호출됩니다.
        """
        if event.is_directory: # 디렉토리가 생성되었을 때만 (새 작품 폴더)
            print(f"\n[EVENT] 새 폴더 감지: {event.src_path}")
            # dmm_cover_downloader의 함수를 호출하여 전체 폴더를 스캔하고 다운로드합니다.
            dmm_cover_downloader.run_downloader()
            print("[INFO] 스캔 및 다운로드 프로세스 완료.")
        # else: # 파일 생성 이벤트를 무시하려면 주석 처리
        #     print(f"  [EVENT] 새 파일 감지: {event.src_path}")

    # 필요에 따라 on_modified, on_deleted 등 다른 이벤트를 처리할 수 있습니다.
    # on_modified(self, event):
    #     if event.is_directory:
    #         print(f"폴더 수정 감지: {event.src_path}")
    #         dmm_cover_downloader.run_downloader()

def main():
    event_handler = MyHandler()
    observer = Observer()
    
    # PATH_TO_WATCH 디렉토리를 재귀적으로 감시합니다.
    observer.schedule(event_handler, PATH_TO_WATCH, recursive=True)
    
    print(f"'{PATH_TO_WATCH}' 폴더 변경 감시 시작...")
    print("새 폴더가 감지되면 DMM 이미지 다운로더가 실행됩니다.")
    print("컨테이너를 종료하려면 Ctrl+C를 누르세요.")
    
    # 초기 실행: 컨테이너 시작 시 한 번 전체 스캔을 수행합니다.
    # 이전에 다운로드하지 못한 파일이 있을 수 있기 때문입니다.
    print("\n[초기 실행] 기존 폴더에 대한 첫 스캔 시작...")
    dmm_cover_downloader.run_downloader()
    print("[초기 실행] 첫 스캔 완료. 이제 폴더 변경을 감시합니다.")


    try:
        while True:
            time.sleep(1) # 1초마다 대기하면서 이벤트를 처리합니다.
    except KeyboardInterrupt:
        observer.stop() # Ctrl+C 누르면 감시 중지
    observer.join() # 감시자 스레드가 완전히 종료될 때까지 기다립니다.

if __name__ == "__main__":
    main()
