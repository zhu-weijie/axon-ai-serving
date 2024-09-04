import os
import time
import zipfile
from threading import Timer

VERSION = "1.1.0"

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
    if not os.path.isfile(FILE_P900MASTER) or not os.path.isfile(FILE_P900MASTER_MD5):
        return False

    print("delete old p900master")
    os.system("rm -f /root/p900master")
    os.system("sync")
    time.sleep(1)

    print("decompress new p900master")
    os.system(f"unzip -q -o -d /root {FILE_P900MASTER}")
    os.system("sync")
    time.sleep(1)

    os.system("chmod 775 /root/p900master")
    os.system("sync")
    time.sleep(1)

    return True


def p900upgrade_webserver():
    if not os.path.isfile(FILE_P900WEBSERVER) or not os.path.isfile(
        FILE_P900WEBSERVER_MD5
    ):
        return False

    print("stop old p900webserver")
    while True:
        pid = os.popen("ps -eaf | grep uwsgi | grep -v grep").readline()
        if pid:
            print(f"kill pid {pid}")
            os.system(f"kill {pid}")
            os.system("sync")
            time.sleep(0.1)
        else:
            break

    print("create backup for setting folders")
    os.system("mkdir -p /root/tmpData/{floorplans,script}")
    os.system("cp -avr /root/p900webserver/media/floorplans/* /root/tmpData/floorplans")
    os.system("cp -avr /root/p900webserver/script/import/* /root/tmpData/script")

    print("delete old p900webserver")
    os.system("rm -rf /root/p900webserver")
    os.system("sync")
    time.sleep(1)

    print("decompress new p900webserver")
    os.system(f"unzip -q -o -d /root {FILE_P900WEBSERVER}")
    print("success extract zip file")
    os.system("sync")
    time.sleep(1)

    print("restore setting folders")
    os.system("cp -avr /root/tmpData/floorplans/* /root/p900webserver/media/floorplans")
    os.system("cp -avr /root/tmpData/script/* /root/p900webserver/script/import")
    os.system("sync")
    time.sleep(1)

    print("delete backup folder")
    os.system("rm -rf /root/tmpData")
    os.system("sync")
    time.sleep(1)

    return True


def p900upgrade(interval):
    if os.path.isfile(FILE_UPGRADE_FLAG):
        print("rename upload files...")
        rename_files()

        print("p900upgrade: start upgrade...")
        rt1 = p900upgrade_webserver()
        rt2 = p900upgrade_master()

        print("p900upgrade: delete upload files...")
        os.system("rm -rf /root/upload/*")
        os.system("sync")
        print("p900upgrade: finish upgrade")
        time.sleep(1)

        if rt1 or rt2:
            print("p900upgrade: system reboot...")
            os.system("reboot")
            time.sleep(60)

    t = Timer(interval, p900upgrade, (interval,))
    t.start()


print(f"\np900upgrade: version {VERSION}")
p900upgrade(3)
