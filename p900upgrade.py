import os
import time
import zipfile
from threading import Timer

VER = "1.0"

FILE_UpgradeFlag       = "/root/upload/UpgradePending"

FILE_p900master        = "/root/upload/p900master.zip"
FILE_p900masterMD5     = "/root/upload/p900master.zip.md5"

FILE_p900webserver     = "/root/upload/p900webserver.zip"
FILE_p900webserverMD5  = "/root/upload/p900webserver.zip.md5"


#def checkMD5(file, fileMD5):
#    md5 = os.popen("md5sum -b " + file).readline()
#    fd = open(fileMD5)
#    md5ref = fd.readline()
#    fd.close()
#    if ( operator.eq(md5[0:31], md5ref[0:31]) ):
#        return True
#    else:
#        return False


def p900upgrade_Master():
    if ( os.path.isfile(FILE_p900master) != True or os.path.isfile(FILE_p900masterMD5) != True ):
        return False
    else:#if ( checkMD5(FILE_p900master, FILE_p900masterMD5) ):
        print("delete old p900master")
        os.system("rm -f /root/p900master")
        os.system("sync")
        os.system("sleep 1")

        print("decompress new p900master")
        os.system("unzip -q -o -d /root " + FILE_p900master)
        os.system("sync")
        os.system("sleep 1")

        os.system("chmod 775 /root/p900master")
        os.system("sync")
        os.system("sleep 1")

        return True
#    else:
#        print("p900upgrade Master fail: md5 not match")
#        return False


def p900upgrade_Webserver():
    if ( os.path.isfile(FILE_p900webserver) != True or os.path.isfile(FILE_p900webserverMD5) != True ):
        return False
    else:#if ( checkMD5(FILE_p900webserver, FILE_p900webserverMD5) ):
        print("stop old p900webserver")
        while(1):
            pid = os.popen("ps -eaf | grep manage.py | grep -v grep").readline()
            if (pid != ""):
                pid = pid[0:5]
                print("kill pid " + pid)
                os.system("kill " + pid)
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
        os.system("unzip -q -o -d /root " + FILE_p900webserver)
        print('success extract zip file')
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
#    else:
#        print("p900upgrade Webserver fail: md5 not match")
#        return False


def p900upgrade(inc):
    #print('P900Upgrade')
    if ( os.path.isfile(FILE_UpgradeFlag) == True ):
        print("p900upgrade: start upgrade")
        rt1 = p900upgrade_Webserver()
        rt2 = p900upgrade_Master()

        print("p900upgrade: delete upload files...")
        os.system("rm -rf /root/upload/*")
        os.system("sync")
        print("p900upgrade: finish upgrade")
        time.sleep(1)

        if (rt1 == True or rt2 == True):
            print("p900upgrade: system reboot...")
            os.system("reboot")
            time.sleep(60)

    t = Timer(inc, p900upgrade, (inc,))
    t.start()


print("\np900upgrade: version " + VER)
p900upgrade(3)


