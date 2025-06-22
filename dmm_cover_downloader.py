import requests
import os
import re
import time

# --- 설정 (Configuration) ---
# Docker 컨테이너 내부의 JAV 폴더 경로 (외부에서 마운트될 경로)
# 이 경로는 Docker run 명령어의 -v 옵션과 일치해야 합니다.
JAV_ROOT_FOLDER = "/jav_videos" # <--- Docker 컨테이너 내부 경로로 고정

# DMM 이미지 URL 패턴
# {PATH_ID}는 URL 경로에 사용될 ID, {FILE_ID}는 파일명에 사용될 ID
# 예시:
# sone00720 -> https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/sone00720/sone00720ps.jpg
# 1fsdss00708 -> https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/1fsdss00708/1fsdss00708ps.jpg
DMM_IMAGE_URL_PATTERN = "https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{PATH_ID}/{FILE_ID}ps.jpg"

# 웹 요청을 보낼 때 브라우저처럼 보이게 하기 위한 헤더 설정
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# --- 함수 (Functions) ---

def clean_product_id(folder_name):
    """
    폴더 이름을 DMM 상품 ID의 기본 형식으로 정리합니다.
    예시: 'sone-720' -> 'sone00720'
    예시: 'fsdss-708' -> 'fsdss00708' (여기서는 '1'을 붙이지 않음. '1'은 다운로드 시도 시에 붙입니다.)
    """
    # 하이픈을 제거하고 소문자로 변환합니다.
    cleaned = folder_name.replace('-', '').lower()
    
    # 숫자 부분이 5자리가 아닌 경우 앞에 0으로 채우는 일반적인 패턴
    # 예: 'sone720' -> 'sone00720'
    match = re.match(r'([a-zA-Z]+)(\d+)', cleaned)
    if match:
        prefix = match.group(1)
        number_str = match.group(2)
        padded_number = number_str.zfill(5) # 숫자를 5자리로 채웁니다.
        return prefix + padded_number
    
    return cleaned # 이 패턴에 해당하지 않는 경우 원본 그대로 반환

def download_image_attempt(image_url, save_path, folder_name_for_log):
    """
    실제로 이미지를 다운로드하는 내부 함수.
    이 함수는 HTTP 요청을 보내고 파일로 저장하는 역할을 합니다.
    """
    try:
        response = requests.get(image_url, stream=True, headers=HEADERS, timeout=10)
        response.raise_for_status() # HTTP 오류 (4xx, 5xx) 발생 시 예외 발생 (예: 404 Not Found)

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"  [성공] '{folder_name_for_log}' 이미지 저장 완료: {os.path.basename(save_path)}")
        return True
    except requests.exceptions.HTTPError as e:
        # HTTP 404 (Not Found)와 같은 특정 오류를 구분하기 위함
        print(f"  [실패] HTTP 오류 ({response.status_code}) '{folder_name_for_log}' ({image_url}): {e}")
        return False
    except requests.exceptions.Timeout:
        print(f"  [실패] 요청 시간 초과 '{folder_name_for_log}' ({image_url})")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  [실패] 네트워크 또는 기타 요청 오류 '{folder_name_for_log}' ({image_url}): {e}")
        return False
    except Exception as e:
        print(f"  [실패] 알 수 없는 오류 발생 '{folder_name_for_log}' ({image_url}): {e}")
        return False

def download_dmm_cover(dmm_product_id, save_path, folder_name):
    """
    DMM 커버 이미지를 다운로드합니다.
    기본 ID로 시도하고, 실패 시 '1'을 붙인 ID로 다시 시도합니다.
    """
    if os.path.exists(save_path):
        # 이 함수를 호출하기 전에 이미 main 루프에서 존재 여부를 확인합니다.
        # 따라서 여기서는 이미 존재하면 바로 True를 반환합니다.
        return True

    # 1차 시도: 기본 DMM 상품 ID 사용
    primary_image_url = DMM_IMAGE_URL_PATTERN.format(PATH_ID=dmm_product_id, FILE_ID=dmm_product_id)
    print(f"  1차 시도 중 (ID: {dmm_product_id})...")
    if download_image_attempt(primary_image_url, save_path, folder_name):
        return True

    # 1차 시도 실패 시: '1'을 붙인 ID로 2차 시도
    # 예시: 'sone00720' -> '1sone00720'
    # 예시: 'fsdss00708' -> '1fsdss00708'
    secondary_id_for_url = '1' + dmm_product_id
    secondary_image_url = DMM_IMAGE_URL_PATTERN.format(PATH_ID=secondary_id_for_url, FILE_ID=secondary_id_for_url)
    print(f"  1차 시도 실패. 2차 시도 중 (ID: {secondary_id_for_url})...")
    if download_image_attempt(secondary_image_url, save_path, folder_name):
        return True
    
    print(f"  [결과] '{folder_name}'의 이미지 다운로드에 최종 실패했습니다.")
    return False

def run_downloader():
    """
    모든 작품 폴더를 스캔하고 이미지 다운로드를 시도하는 함수입니다.
    """
    print(f"\n--- 폴더 스캔 및 이미지 다운로드 시작: {JAV_ROOT_FOLDER} ---")
    
    # JAV 루트 폴더 내의 모든 하위 디렉토리(작품 폴더로 간주)를 가져옵니다.
    product_folders = [d for d in os.listdir(JAV_ROOT_FOLDER)
                       if os.path.isdir(os.path.join(JAV_ROOT_FOLDER, d))]

    if not product_folders:
        print("  하위 작품 폴더가 없습니다.")
        return

    # 각 작품 폴더를 반복 처리합니다.
    for i, folder_name in enumerate(product_folders):
        full_folder_path = os.path.join(JAV_ROOT_FOLDER, folder_name) # 작품 폴더의 전체 경로
        save_image_path = os.path.join(full_folder_path, "folder.jpg") # 저장될 이미지의 전체 경로

        # 해당 폴더에 folder.jpg 파일이 이미 존재하면 건너뜁니다.
        if os.path.exists(save_image_path):
            continue # 이미 파일이 있으면 다음 폴더로

        print(f"--- [{i+1}/{len(product_folders)}] '{folder_name}' 폴더 처리 중... ---")
        
        # 폴더 이름을 DMM 상품 ID 형식으로 정리합니다.
        dmm_product_id = clean_product_id(folder_name)
        if not dmm_product_id:
            print(f"  [경고] 폴더 이름에서 DMM 상품 ID를 파싱할 수 없습니다: '{folder_name}'. 건너뜁니다.")
            continue

        # 새롭게 정의한 download_dmm_cover 함수를 호출합니다.
        # 이 함수 내부에서 1차/2차 시도가 이루어집니다.
        download_dmm_cover(dmm_product_id, save_image_path, folder_name)
        
        time.sleep(0.5) # 서버에 부담을 주지 않기 위해 작은 지연 시간을 둡니다.

    print("\n--- 모든 작품 폴더 처리 완료 ---")

# 이 파일이 단독으로 실행될 때를 대비하여 (테스트 등)
if __name__ == "__main__":
    if JAV_ROOT_FOLDER == "/jav_videos": # Docker 환경에 맞게 설정되었는지 확인
        print("경고: JAV_ROOT_FOLDER가 Docker 컨테이너용으로 설정되었습니다.")
        print("로컬 테스트를 원하시면 실제 로컬 경로로 변경하세요.")
    
    # run_downloader()는 watch_and_run.py에서 호출됩니다.
    # 이 파일을 직접 실행하여 테스트하려면 아래 주석을 해제하세요.
    # run_downloader()
    pass # 실제 실행은 watch_and_run.py에서 담당
