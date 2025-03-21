import os
import shutil
import subprocess
import tempfile
import zipfile
import time
import re

DATABASE_INITIALIZATION_FILE_PATH = "/root/p900scripts/database_initialization.sh"


def check_free_space(path, required_space):
    total, used, free = shutil.disk_usage(path)
    return free >= required_space


def unzip_upload():
    zip_pattern = r"^upload.*\.zip$"
    upload_dir = "/root/"
    zip_files = [f for f in os.listdir(upload_dir) if re.match(zip_pattern, f)]

    if not zip_files:
        return False

    zip_path = os.path.join(upload_dir, zip_files[0])
    extract_path = "/root/upload"

    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)

    p900webserver_path = "/root/p900webserver"
    if os.path.exists(p900webserver_path):
        shutil.rmtree(p900webserver_path)

    required_space = os.path.getsize(zip_path) * 2
    if not check_free_space("/", required_space):
        return False

    temp_extract_path = tempfile.mkdtemp()

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_extract_path)

        top_level_contents = os.listdir(temp_extract_path)
        if len(top_level_contents) == 1 and os.path.isdir(
            os.path.join(temp_extract_path, top_level_contents[0])
        ):
            nested_dir = os.path.join(temp_extract_path, top_level_contents[0])
            for item in os.listdir(nested_dir):
                shutil.move(os.path.join(nested_dir, item), temp_extract_path)
            os.rmdir(nested_dir)

        os.makedirs(extract_path, exist_ok=True)

        for item in os.listdir(temp_extract_path):
            src_path = os.path.join(temp_extract_path, item)
            dest_path = os.path.join(extract_path, item)
            if os.path.isdir(src_path):
                if os.path.exists(dest_path):
                    for root, dirs, files in os.walk(src_path):
                        rel_path = os.path.relpath(root, src_path)
                        target_dir = os.path.join(dest_path, rel_path)
                        os.makedirs(target_dir, exist_ok=True)
                        for file in files:
                            shutil.copy2(
                                os.path.join(root, file), os.path.join(target_dir, file)
                            )
                else:
                    shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)

        os.remove(zip_path)

        required_files = ["p900master", "p900webserver"]
        missing_files = [
            f
            for f in required_files
            if not os.path.exists(os.path.join(extract_path, f))
        ]

        if missing_files:
            return False

        return True
    except zipfile.BadZipFile as e:
        print(f"ERROR: Failed to unzip {zip_path}: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error during unzip: {e}")
    finally:
        if os.path.exists(temp_extract_path):
            shutil.rmtree(temp_extract_path)

    return False


def copy_and_make_executable(src_dir, dest_dir, make_executable=False):
    if not os.path.exists(src_dir):
        return

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for file_name in os.listdir(src_dir):
        src_file = os.path.join(src_dir, file_name)
        dest_file = os.path.join(dest_dir, file_name)

        if os.path.isfile(src_file):
            try:
                if dest_file == "/bin/busybox":
                    temp_file = f"{dest_file}.tmp"
                    os.rename(dest_file, temp_file)
                    try:
                        shutil.copy2(src_file, dest_file)
                        if make_executable:
                            os.chmod(dest_file, 0o755)
                    except Exception as e:
                        os.rename(temp_file, dest_file)
                        raise
                    else:
                        os.remove(temp_file)
                else:
                    shutil.copy2(src_file, dest_file)
                    if make_executable:
                        os.chmod(dest_file, 0o755)
            except Exception as e:
                print(f"ERROR: Failed to copy {file_name} to {dest_dir}: {e}")
        else:
            print(f"DEBUG: Skipping non-file {file_name} in {src_dir}.")


def handle_p900master():
    src = "/root/upload/p900master"
    dest = "/root/p900master"

    if os.path.exists(dest):
        os.remove(dest)

    if os.path.exists(src):
        shutil.move(src, dest)

        os.chmod(dest, 0o755)


def handle_p900webserver():
    src = "/root/upload/p900webserver"
    dest = "/root/p900webserver"

    if os.path.exists(dest):
        shutil.rmtree(dest)

    if os.path.exists(src):
        shutil.move(src, dest)

        try:
            subprocess.run(["python", "manage.py", "migrate"], check=True, cwd=dest)
        except Exception as e:
            print(f"ERROR: Failed to run migrations: {e}")
    else:
        print(f"ERROR: Source directory {src} does not exist. Skipping migrations.")


def copy_files_and_create_symlink():
    paths = [
        ("/root/upload/bin", "/bin", True),
        ("/root/upload/etc", "/etc/init.d", True),
        ("/root/upload/p900scripts", "/root/p900scripts", True),
        ("/root/upload/p900backups", "/root/p900backups", False),
        ("/root/upload/root", "/root", False),
        ("/root/upload/network", "/etc/network", False),
        ("/root/upload/nginx", "/etc/nginx", False),
    ]

    for src, dest, make_exec in paths:
        copy_and_make_executable(src, dest, make_exec)

    try:
        os.chdir("/usr/bin/")
        if not os.path.exists("nc"):
            os.symlink("../../bin/busybox", "nc")
        else:
            print("DEBUG: Symbolic link 'nc' already exists. Skipping...")
    except Exception as e:
        print(f"ERROR: Failed to create symbolic link for busybox nc: {e}")


def cleanup_and_reboot():
    upload_dir = "/root/upload"

    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)

    try:
        subprocess.run([DATABASE_INITIALIZATION_FILE_PATH], check=True)
    except Exception as e:
        print(f"ERROR: Failed to reboot the system: {e}")


def main():
    while True:
        try:
            if unzip_upload():
                handle_p900master()
                handle_p900webserver()
                copy_files_and_create_symlink()

                cleanup_and_reboot()
                break
            else:
                time.sleep(3)
        except Exception as e:
            print(f"ERROR: Exception in main loop: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
