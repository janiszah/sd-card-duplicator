import time
import shlex
import os
import subprocess
from threading import Thread
from os import listdir
from os.path import isfile, join
from subprocess import Popen, PIPE


def runCommandAndGetStdout(cmd):
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    return out

def getConnectedDrives():
    commandOutput = runCommandAndGetStdout("lsblk -d | awk -F: '{print $1}' | awk '{print $1}'")
    splitted = commandOutput.splitlines()

    drives = []

    for drive in splitted:
        if drive != "NAME" and not drive.startswith("mmc"):
            drives.append(drive)
            # print(drive)

    return drives


def writeThreadFunction(arg):
	print("Thread started!")
	process = Popen(arg, stdout=PIPE, stderr=PIPE, shell=True, executable='/bin/bash')
	lines_iterator = iter(process.stderr.readline, b"")
	for line in lines_iterator:
		print(line)
	# print(process.stdout.read())
	print("SD card duplicated!")

def writeSdCard(drive):

	command = constructCommand(drive)

	thread = Thread(target = writeThreadFunction, args = (command, ))
	thread.start()


def constructCommand(drive):

	device = "/dev/" + drive + "1"
	mount_dir = "mount/" + drive

	cmd = ""
	cmd += "dosfslabel " + device + " ERICA;"			# Rename SD card
	cmd += "mkdir " + mount_dir + ";"					# Make mount directory
	cmd += "mount " + device + " " + mount_dir + ";"	# Mount sd card
	cmd += "cp -r content/. " + mount_dir + ";"			# Copy files
	cmd += "ls " + mount_dir + ";"						# List copied files
	cmd += "umount " + mount_dir + ";"					# Unmount SD card
	cmd += "rmdir " + mount_dir + ";"					# Remove mount directory

	return cmd

print("Erica Synths - SD card Duplicator")
# getConnectedDrives();
# writeSdCard("sdm");

card_list = []

while True:
    time.sleep(0.01) #To prevent excessive CPU use

    # Detect connected SD cards
    new_list = getConnectedDrives()

    diff = list(set(new_list) - set(card_list))
    card_list = new_list

    if(diff):

    	for drive in diff:
    		print(drive)
    		writeSdCard(drive)





