import os
import argparse
from datetime import datetime

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--date", required=False,
	help="Expiration date (format YYYY-MM-DD)")
ap.add_argument("-p", "--path", required=True,
	help="Path of project (ex: .../Documents/camera-chinhcong/app)")
args = vars(ap.parse_args())

print("Start encrypt code.")
if args["date"]:
    cmd = "pyarmor licenses --expired {} r001".format(args["date"])
    os.system(cmd)
    os.system("pyarmor obfuscate --with-license licenses/r001/license.lic *.py")
else:
    os.system("pyarmor obfuscate *.py")

print("Move file to client folder.")
if os.path.exists("licenses"):
    os.system("cp -r licenses {}".format(args["path"]))

if os.path.exists("dist"):
    os.system("cp -r dist/* {}".format(args["path"]))

if os.path.isfile("{}/script.py".format(args["path"])):
    os.system("rm {}/script.py".format(args["path"]))