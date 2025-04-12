import sys
import os
import subprocess

EXIFTOOL_PATH = r"C:\exiftool\exiftool.exe"
TARGET_FOLDER = r"C:\Photos\Sorted"

def main():
    if len(sys.argv) < 2:
        print("Пожалуйста, перетащите папку на этот скрипт.")
        input("Нажмите Enter для завершения...")
        return
    
    source_folder = os.path.normpath(sys.argv[1])
    print(f"Перетащенная папка: {source_folder}")

    if not os.path.exists(TARGET_FOLDER):
        print(f"Целевая папка не существует: {TARGET_FOLDER}")
        input("Нажмите Enter для завершения...")
        return

    os.chdir(TARGET_FOLDER)
    subprocess.run(["explorer", TARGET_FOLDER], shell=True)

    command = [
        EXIFTOOL_PATH,
        "-r",
        "-d", "%Y/%m/%d",
        "-Directory<DateTimeOriginal",
        "-Directory<CreateDate",
        "-charset", "FileName=cp1251",
        source_folder
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="cp1251", timeout=3600)
        print("Вывод ExifTool:")
        print(result.stdout)
        if result.stderr:
            print("Ошибки ExifTool:")
            print(result.stderr)
    except subprocess.TimeoutExpired:
        print("ExifTool выполняется слишком долго. Возможно, ошибка.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

    input("Нажмите Enter для завершения...")

if __name__ == "__main__":
    main()