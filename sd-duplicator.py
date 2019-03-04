import time
import shlex
import os
import subprocess
from threading import Thread
from os import listdir
from os.path import isfile, join
from subprocess import Popen, PIPE
import Adafruit_CharLCD as LCD

lcd_rs        = 25
lcd_en        = 24
lcd_d4        = 23
lcd_d5        = 17
lcd_d6        = 18
lcd_d7        = 22
lcd_columns = 16
lcd_rows = 2


card_state = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]



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


def writeThreadFunction(arg, arg2):
    global card_state

    print("Thread started!")
    process = Popen(arg, stdout=PIPE, stderr=PIPE, shell=True, executable='/bin/bash')
    lines_iterator = iter(process.stderr.readline, b"")
    for line in lines_iterator:
        print(line)
        # print(process.stdout.read())

    print("SD card " + str(arg2) + " duplicated!")
    card_state[arg2] = 2;

def writeSdCard(drive, idx):

	command = constructCommand(drive)

	thread = Thread(target = writeThreadFunction, args = (command, idx))
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

# Initialize the LCD using the pins above.
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7,
                           lcd_columns, lcd_rows)


lcd.create_char(1, [17,10,4,4,4,4,10,17])
lcd.create_char(2, [31,17,17,17,17,17,17,31])
lcd.create_char(3, [31,31,31,31,31,31,31,31])


lcd.clear();
lcd.set_cursor(0,0)
lcd.message('-=Erica Synths=-')
lcd.set_cursor(0,1)
lcd.message(' SD card writer ')
time.sleep(2)

lcd.clear();
lcd.set_cursor(0,0)
lcd.message('   0123456789   ')
# lcd.set_cursor(0,1)
# lcd.message('   \x01\x01\x01\x01\x01\x01\x01\x01\x01\x01   ')

card_list = []

slot_list = ["sdc", "sdg", "sdk", "sdo", "sda", "sde", "sdi", "sds", "sdq", "sdm"]

x = 0

while True:
    time.sleep(0.01) #To prevent excessive CPU use

    # Detect connected SD cards
    new_list = getConnectedDrives()

    in_diff = list(set(new_list) - set(card_list))
    out_diff = list(set(card_list) - set(new_list))
    card_list = new_list

    if(in_diff):
    	for drive in in_diff:
            print("In: " + drive)
            indices = [i for i, s in enumerate(slot_list) if drive in s]
            print(indices[0])
            card_state[indices[0]] = 1;
            writeSdCard(drive, indices[0])

    if(out_diff):
        for drive in out_diff:
            print("Out: " + drive)
            indices = [i for i, s in enumerate(slot_list) if drive in s]
            card_state[indices[0]] = 0;

    x += 1
    if x > 10:
        x = 0
        lcd.set_cursor(0,1)
        lcd.message('   ')
        for i in range(0,10):
            if card_state[i] == 0:
                lcd.write8(ord('\x01'), True)
            elif card_state[i] == 1:
                lcd.write8(ord('\x02'), True)
            else:
                lcd.write8(ord('\x03'), True)
