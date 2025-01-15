import os
import shutil

def delete_ss_temp_directory():
    """
    SS_temp 디렉토리와 그 내부의 모든 파일을 삭제합니다.
    삭제 전에 사용자 확인을 요청합니다.
    """
    # 현재 실행 중인 디렉토리
    current_dir = os.path.dirname(os.path.realpath(__file__))

    # SS_temp 폴더 경로
    ss_temp_dir = os.path.join(current_dir, "SS_temp")

    # 디렉토리가 존재하는지 확인
    if not os.path.exists(ss_temp_dir):
        print(f"디렉토리가 존재하지 않습니다: {ss_temp_dir}")
        return

    # 사용자 확인
    confirmation = input(f"'{ss_temp_dir}' 디렉토리와 그 내부의 모든 파일을 삭제하시겠습니까? (y/n): ").strip().lower()

    if confirmation == 'y':
        try:
            # 디렉토리 삭제
            shutil.rmtree(ss_temp_dir)
            print(f"디렉토리가 삭제되었습니다: {ss_temp_dir}")
        except Exception as e:
            print(f"디렉토리를 삭제하는 중 오류가 발생했습니다: {e}")
    else:
        print(f"삭제하지 않고 '{ss_temp_dir}' 디렉토리를 남겨둡니다.")

# 함수 호출
delete_ss_temp_directory()