"""
For v4 and v5 boards.
Version: 1.1.2
"""
import os
import time
import zipfile
from threading import Timer


FILE_UPGRADE_FLAG_OLD = "/root/upload/UpgradePending"
FILE_UPGRADE_FLAG = "/root/upload/upgrade_pending"

FILE_P900MASTER = "/root/upload/p900master.zip"
FILE_P900MASTER_MD5 = "/root/upload/p900master.zip.md5"

FILE_P900WEBSERVER = "/root/upload/p900webserver.zip"
FILE_P900WEBSERVER_MD5 = "/root/upload/p900webserver.zip.md5"


def rename_files():
    for file in os.listdir("/root/upload"):
        if "p900master" in file:
            if file.endswith(".zip"):
                os.rename(os.path.join("/root/upload", file), FILE_P900MASTER)
            elif file.endswith(".md5"):
                os.rename(os.path.join("/root/upload", file), FILE_P900MASTER_MD5)
        elif "p900webserver" in file:
            if file.endswith(".zip"):
                os.rename(os.path.join("/root/upload", file), FILE_P900WEBSERVER)
            elif file.endswith(".md5"):
                os.rename(os.path.join("/root/upload", file), FILE_P900WEBSERVER_MD5)


def p900upgrade_master():
    if not os.path.isfile(FILE_P900MASTER):
        return False
    if not os.path.isfile(FILE_P900MASTER_MD5):
        return False

    os.system("rm -f /root/p900master")
    os.system("sync")
    time.sleep(1)

    if os.system(f"unzip -q -o -d /root {FILE_P900MASTER}") != 0:
        return False
    os.system("sync")
    time.sleep(1)

    os.system("chmod 775 /root/p900master")
    os.system("sync")
    time.sleep(1)

    return True


def p900upgrade_webserver():
    if not os.path.isfile(FILE_P900WEBSERVER):
        return False
    if not os.path.isfile(FILE_P900WEBSERVER_MD5):
        return False

    os.system("mkdir -p /root/tmp_data/{floorplans,script}")
    os.system("cp -avr /root/p900webserver/media/floorplans/* /root/tmp_data/floorplans")
    os.system("cp -avr /root/p900webserver/script/import/* /root/tmp_data/script")

    os.system("rm -rf /root/p900webserver")
    os.system("sync")
    time.sleep(1)

    if os.system(f"unzip -q -o -d /root {FILE_P900WEBSERVER}") != 0:
        return False
    os.system("sync")
    time.sleep(1)

    os.system("cp -avr /root/tmp_data/floorplans/* /root/p900webserver/media/floorplans")
    os.system("cp -avr /root/tmp_data/script/* /root/p900webserver/script/import")
    os.system("sync")
    time.sleep(1)

    os.system("rm -rf /root/tmp_data")
    os.system("sync")
    time.sleep(1)

    os.system("cd /root/p900webserver && python manage.py migrate")
    os.system("sync")
    time.sleep(1)

    return True


def p900upgrade(interval):
    if os.path.isfile(FILE_UPGRADE_FLAG) or os.path.isfile(FILE_UPGRADE_FLAG_OLD):
        rename_files()

        rt1 = p900upgrade_webserver()
        rt2 = p900upgrade_master()

        os.system("rm -rf /root/upload/*")
        os.system("sync")

        if rt1 or rt2:
            os.system("reboot")
            time.sleep(60)
        else:
            print("Upgrade failed. No reboot will be performed.")

    t = Timer(interval, p900upgrade, (interval,))
    t.start()


p900upgrade(3)
