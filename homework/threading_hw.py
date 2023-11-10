import shutil
import sys
from pathlib import Path
from threading import Thread, RLock


images = list()
documents = list()
audio = list()
video = list()
archives = list()
folders = list()
others = list()
unknown = set()
extensions = set()

registered_extensions = {
    "JPEG": images, "PNG": images, "JPG": images, "SVG": images,
    "AVI": video, "MP4": video, "MOV": video, "MKV": video,
    "TXT": documents, "DOC": documents, "DOCX": documents, "PDF": documents, "XLSX": documents, "PPTX": documents,
    "ZIP": archives, "GZ": archives, "TAR": archives,
    "MP3": audio, "OGG": audio, "WAV": audio, "AMR": audio
}

lock = RLock()


def get_extensions(file_name):
    return Path(file_name).suffix[1:].upper()


def scan(folder):
    for item in folder.iterdir():
        if item.is_dir():
            if item.name not in ("images", "documents", "audio", "video", "archives"):
                folders.append(item)
                t = Thread(target=scan, args=(item, ))
                t.start()
            continue

        extension = get_extensions(file_name=item.name)
        new_name = folder/item.name
        if not extension:
            with lock:
                others.append(new_name)
        else:
            try:
                with lock:
                    container = registered_extensions[extension]
                    extensions.add(extension)
                    container.append(new_name)
            except KeyError:
                with lock:
                    unknown.add(extension)
                    others.append(new_name)


def handle_file(path, root_folder, destination):
    target_folder = root_folder / destination
    target_folder.mkdir(exist_ok=True)
    with lock:
        path.replace(target_folder / path.name)


def handle_archive(path, root_folder, destination):
    target_folder = root_folder / destination
    target_folder.mkdir(exist_ok=True)

    new_name = path.stem

    archive_folder = root_folder / destination / new_name
    archive_folder.mkdir(exist_ok=True)

    try:
        shutil.unpack_archive(str(path), str(archive_folder))
        path.unlink()
    except (shutil.ReadError, FileNotFoundError):
        with lock:
            archive_folder.rmdir()
        return


def remove_empty_folders(path):
    for item in path.iterdir():
        if item.is_dir():
            remove_empty_folders(item)
            try:
                item.rmdir()
            except OSError:
                pass


def get_folder_objects(root_path):
    for folder in root_path.iterdir():
        if folder.is_dir():
            remove_empty_folders(folder)
            try:
                folder.rmdir()
            except OSError:
                pass


def main():
    path = sys.argv[1]
    folder_path = Path(path)

    scan_thread = Thread(target=scan, args=(folder_path,))
    scan_thread.start()
    scan_thread.join()

    threads = []
    for file in images:
        t = Thread(target=handle_file, args=(file, folder_path, "images"))
        threads.append(t)
        t.start()

    for file in documents:
        t = Thread(target=handle_file, args=(file, folder_path, "documents"))
        threads.append(t)
        t.start()

    for file in audio:
        t = Thread(target=handle_file, args=(file, folder_path, "audio"))
        threads.append(t)
        t.start()

    for file in video:
        t = Thread(target=handle_file, args=(file, folder_path, "video"))
        threads.append(t)
        t.start()

    for file in archives:
        t = Thread(target=handle_archive, args=(file, folder_path, "archives"))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    get_folder_objects(folder_path)
