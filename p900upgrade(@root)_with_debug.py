"""
For v4 and v5 boards.
Version: 1.2.0
"""
import os
import shutil
import subprocess
import tempfile
import zipfile
import time
import re


def check_free_space(path, required_space):
    """Check if the specified path has the required free space."""
    total, used, free = shutil.disk_usage(path)
    return free >= required_space

def get_free_space(path):
    """Get the free disk space of the specified path in bytes."""
    _, _, free = shutil.disk_usage(path)
    return free

def unzip_upload():
    zip_pattern = r"^upload.*\.zip$"
    upload_dir = "/root/"
    zip_files = [f for f in os.listdir(upload_dir) if re.match(zip_pattern, f)]

    if not zip_files:
        print("DEBUG: No matching upload zip file found. Retrying...")
        return False

    zip_path = os.path.join(upload_dir, zip_files[0])
    extract_path = "/root/upload"

    # Clean up any previous extraction
    if os.path.exists(extract_path):
        print(f"DEBUG: Deleting existing {extract_path}...")
        shutil.rmtree(extract_path)

    # Delete the existing /root/p900webserver directory before unzipping
    p900webserver_path = "/root/p900webserver"
    if os.path.exists(p900webserver_path):
        print(f"DEBUG: Deleting existing {p900webserver_path} directory...")
        shutil.rmtree(p900webserver_path)

    # Check free space before file extraction
    free_space_before = get_free_space("/")
    print(f"DEBUG: Free space before extraction: {free_space_before / (1024 * 1024):.2f} MB")
    
    # Estimate required space (zip file size + overhead)
    required_space = os.path.getsize(zip_path) * 2
    if not check_free_space("/", required_space):
        print(f"ERROR: Not enough disk space. Required: {required_space / (1024 * 1024):.2f} MB")
        return False

    # Create a temporary extraction directory to handle nested issues
    temp_extract_path = tempfile.mkdtemp()

    print(f"DEBUG: Extracting {zip_path} to temporary directory {temp_extract_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_path)

        # Check if the ZIP contains a single top-level directory
        top_level_contents = os.listdir(temp_extract_path)
        if len(top_level_contents) == 1 and os.path.isdir(os.path.join(temp_extract_path, top_level_contents[0])):
            # Flatten the structure by moving the contents of the single directory up one level
            nested_dir = os.path.join(temp_extract_path, top_level_contents[0])
            for item in os.listdir(nested_dir):
                shutil.move(os.path.join(nested_dir, item), temp_extract_path)
            os.rmdir(nested_dir)

        # Move extracted contents to /root/upload
        print(f"DEBUG: Moving extracted files to {extract_path}...")
        os.makedirs(extract_path, exist_ok=True)

        for item in os.listdir(temp_extract_path):
            src_path = os.path.join(temp_extract_path, item)
            dest_path = os.path.join(extract_path, item)
            if os.path.isdir(src_path):
                if os.path.exists(dest_path):
                    # Merge directories
                    for root, dirs, files in os.walk(src_path):
                        rel_path = os.path.relpath(root, src_path)
                        target_dir = os.path.join(dest_path, rel_path)
                        os.makedirs(target_dir, exist_ok=True)
                        for file in files:
                            shutil.copy2(os.path.join(root, file), os.path.join(target_dir, file))
                else:
                    shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)

        print(f"DEBUG: Successfully moved extracted files to {extract_path}.")
        os.remove(zip_path)
        print(f"DEBUG: Deleted {zip_path} after extraction.")

        # Check free space after file extraction
        free_space_after = get_free_space("/")
        print(f"DEBUG: Free space after extraction: {free_space_after / (1024 * 1024):.2f} MB")

        # Verify extracted contents
        required_files = ["p900master", "p900webserver"]
        missing_files = [f for f in required_files if not os.path.exists(os.path.join(extract_path, f))]

        if missing_files:
            print(f"ERROR: Missing required files after extraction: {missing_files}")
            return False

        return True
    except zipfile.BadZipFile as e:
        print(f"ERROR: Failed to unzip {zip_path}: {e}")
    except Exception as e:
        print(f"ERROR: Unexpected error during unzip: {e}")
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_extract_path):
            shutil.rmtree(temp_extract_path)

    return False



def copy_and_make_executable(src_dir, dest_dir, make_executable=False):
    if not os.path.exists(src_dir):
        print(f"DEBUG: Source directory {src_dir} does not exist. Skipping...")
        return

    if not os.path.exists(dest_dir):
        print(f"DEBUG: Destination directory {dest_dir} does not exist. Creating it...")
        os.makedirs(dest_dir)

    for file_name in os.listdir(src_dir):
        src_file = os.path.join(src_dir, file_name)
        dest_file = os.path.join(dest_dir, file_name)

        if os.path.isfile(src_file):
            try:
                # Special handling for /bin/busybox
                if dest_file == "/bin/busybox":
                    temp_file = f"{dest_file}.tmp"
                    print(f"DEBUG: Renaming existing {dest_file} to {temp_file}...")
                    os.rename(dest_file, temp_file)
                    try:
                        print(f"DEBUG: Copying {src_file} to {dest_file}...")
                        shutil.copy2(src_file, dest_file)
                        if make_executable:
                            os.chmod(dest_file, 0o755)
                            print(f"DEBUG: Made {dest_file} executable.")
                        print(f"DEBUG: Successfully copied {file_name} to {dest_dir}.")
                    except Exception as e:
                        print(f"ERROR: Failed to copy {file_name} to {dest_dir}: {e}")
                        os.rename(temp_file, dest_file)  # Restore original file if copy fails
                        raise
                    else:
                        print(f"DEBUG: Removing temporary file {temp_file}...")
                        os.remove(temp_file)
                else:
                    print(f"DEBUG: Copying {src_file} to {dest_file}...")
                    shutil.copy2(src_file, dest_file)
                    if make_executable:
                        os.chmod(dest_file, 0o755)
                        print(f"DEBUG: Made {dest_file} executable.")
                    print(f"DEBUG: Successfully copied {file_name} to {dest_dir}.")
            except Exception as e:
                print(f"ERROR: Failed to copy {file_name} to {dest_dir}: {e}")
        else:
            print(f"DEBUG: Skipping non-file {file_name} in {src_dir}.")

def handle_p900master():
    src = "/root/upload/p900master"
    dest = "/root/p900master"

    if os.path.exists(dest):
        print(f"DEBUG: Deleting existing {dest}...")
        os.remove(dest)

    if os.path.exists(src):
        print(f"DEBUG: Moving {src} to {dest}...")
        shutil.move(src, dest)

        print(f"DEBUG: Making {dest} executable...")
        os.chmod(dest, 0o755)

def handle_p900webserver():
    src = "/root/upload/p900webserver"
    dest = "/root/p900webserver"

    if os.path.exists(dest):
        print(f"DEBUG: Deleting existing {dest} directory...")
        shutil.rmtree(dest)

    if os.path.exists(src):
        print(f"DEBUG: Moving {src} to {dest}...")
        shutil.move(src, dest)

        print(f"DEBUG: Running migrations for {dest}...")
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
        ("/root/upload/settings", "/root/settings", True),
        ("/root/upload/root", "/root", False),
    ]

    # Copy files and set permissions
    for src, dest, make_exec in paths:
        copy_and_make_executable(src, dest, make_exec)

    # Create symbolic link for busybox nc
    try:
        print("DEBUG: Creating symbolic link for busybox nc...")
        os.chdir("/usr/bin/")
        if not os.path.exists("nc"):
            os.symlink("../../bin/busybox", "nc")
            print("DEBUG: Symbolic link 'nc' created successfully.")
        else:
            print("DEBUG: Symbolic link 'nc' already exists. Skipping...")
    except Exception as e:
        print(f"ERROR: Failed to create symbolic link for busybox nc: {e}")

def cleanup_and_reboot():
    upload_dir = "/root/upload"

    if os.path.exists(upload_dir):
        print(f"DEBUG: Deleting {upload_dir} directory...")
        shutil.rmtree(upload_dir)

    print("DEBUG: Rebooting the system...")
    try:
        subprocess.run(["reboot"], check=True)
    except Exception as e:
        print(f"ERROR: Failed to reboot the system: {e}")

def main():
    print("DEBUG: Script started.")
    while True:
        print("DEBUG: Checking for upload zip file...")
        try:
            if unzip_upload():
                print("DEBUG: Starting upgrade process...")
                
                handle_p900master()
                handle_p900webserver()
                copy_files_and_create_symlink()

                print("DEBUG: Cleaning up and rebooting...")
                cleanup_and_reboot()
                break
            else:
                print("DEBUG: No matching ZIP file found. Sleeping for 3 seconds...")
                time.sleep(3)
        except Exception as e:
            print(f"ERROR: Exception in main loop: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
