import time
import shlex
import os
import subprocess
import enum
from threading import Thread
from os import listdir
from os.path import isfile, join
from subprocess import Popen, PIPE, call
import Adafruit_CharLCD as LCD
import RPi.GPIO as GPIO


lcd_rs        = 25
lcd_en        = 24
lcd_d4        = 23
lcd_d5        = 17
lcd_d6        = 18
lcd_d7        = 22
lcd_columns = 16
lcd_rows = 2


card_state = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


button_pin  = 6
led_pin     = 12


ctrl_buttons = [26, 16, 13]

btn_press_time = 0
accept_time = 0

program_state = False


class State(enum.Enum):
  program = 0
  load = 1

state = State.program
slot = 0


# Get available slots
availableSlots = os.listdir("/home/pi/sd_duplicator/slots")


def buttonCallback(channel):
    global btn_press_time
    if GPIO.input(channel) == 0:
        btn_press_time = time.time()
    else:
        btn_press_time = 0



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
    card_state[arg2] = 2

def writeSdCard(drive, idx, slot):

	command = constructCommand(drive, slot)

	thread = Thread(target = writeThreadFunction, args = (command, idx))
	thread.start()


def constructCommand(drive, slot):
  device = "/dev/" + drive + "1" 
  mount_dir = "/home/pi/sd_duplicator/mount/" + drive
  src_dir = "/home/pi/sd_duplicator/slots/" + slot

  cmd = ""
  cmd += "dosfslabel " + device + " " + slot + ";"    # Rename SD card
  cmd += "mkdir " + mount_dir + ";"					          # Make mount directory
  cmd += "mount " + device + " " + mount_dir + ";"	  # Mount sd card
  cmd += "cp -r " + src_dir + "/. " + mount_dir + ";"	# Copy files
  cmd += "ls " + mount_dir + ";"						          # List copied files
  cmd += "umount " + mount_dir + ";"					        # Unmount SD card
  cmd += "rmdir " + mount_dir + ";"					          # Remove mount directory

  return cmd



def needScreenUpdate():
  needScreenUpdate.cnt += 1
  if needScreenUpdate.cnt > 10:
    needScreenUpdate.cnt = 0
    return 1
  else:
    return 0
needScreenUpdate.cnt = 0



def loadSlot():
  drive = "sdc"
  device = "/dev/" + drive + "1"
  mount_dir = "/home/pi/sd_duplicator/mount/" + drive

  # Get label
  res = runCommandAndGetStdout("dosfslabel " + device)
  lines = res.splitlines()
  if len(lines) == 0:
    print("No new content")
    return ""
  else:
    label = lines[len(lines)-1].rstrip()
    print(label)
    dest_dir = "/home/pi/sd_duplicator/slots/" + label

    # TODO: Check if content already exist
    print(dest_dir)
    if os.path.isdir(dest_dir):
      print("Path exists")
      runCommandAndGetStdout("rm -r " + dest_dir)
    else:
      print("New path")
      

    # Copy content from SD card to internal memory
    cmd = ""
    cmd += "mkdir " + dest_dir + ";"                    # Make destination directory
    cmd += "mkdir " + mount_dir + ";"                   # Make source directory (mount)
    cmd += "mount " + device + " " + mount_dir + ";"	  # Mount sd card
    cmd += "cp -r " + mount_dir + "/. " + dest_dir + ";"  # Copy files
    cmd += "ls " + dest_dir + ";"						            # List copied files
    cmd += "umount " + mount_dir + ";"					        # Unmount SD card
    cmd += "rmdir " + mount_dir + ";"					          # Remove mount directory

    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True, executable='/bin/bash')
    lines_iterator = iter(proc.stderr.readline, b"")
    for line in lines_iterator:
      print(line)

    print("New slot created!")

    return label
    

  






def ctrlButtonCallback(channel):
  global state, slot, availableSlots, accept_time, program_state

  if channel == ctrl_buttons[0]:
    # Increment state
    program_state = False
    state = State((state.value + 1) % len(State))
    print(state.name)

  elif channel == ctrl_buttons[1]:
    if state == State.program and program_state == False:
      if len(availableSlots) > 0:
        slot = (slot + 1) % len(availableSlots)

  elif channel == ctrl_buttons[2]:
    if GPIO.input(channel) == 0:
      accept_time = time.time()
    else:
      accept_time = 0





print("Erica Synths - SD card Duplicator")


# Setup GPIO
GPIO.setmode(GPIO.BCM)

# Configure Shutdown button
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(button_pin, GPIO.BOTH, callback=buttonCallback)

# Configure Shutdown button LED
GPIO.setup(led_pin, GPIO.OUT)
GPIO.output(led_pin, GPIO.HIGH)

# Configure Control Buttons
for btn in ctrl_buttons:
  GPIO.setup(btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)

  if btn == ctrl_buttons[2]:
    GPIO.add_event_detect(btn, GPIO.BOTH, callback=ctrlButtonCallback)
  else:
    GPIO.add_event_detect(btn, GPIO.FALLING, callback=ctrlButtonCallback, bouncetime=300)



# Initialize the LCD using the pins above.
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7,
                           lcd_columns, lcd_rows)

# Reset display
lcd.enable_display(0)
time.sleep(1)
lcd.enable_display(1)


lcd.create_char(1, [17,10,4,4,4,4,10,17])
lcd.create_char(2, [31,17,17,17,17,17,17,31])
lcd.create_char(3, [31,31,31,31,31,31,31,31])


lcd.clear()
lcd.set_cursor(0,0)
lcd.message('-=Erica Synths=-')
lcd.set_cursor(0,1)
lcd.message(' SD card writer ')
time.sleep(2)

lcd.clear()
lcd.set_cursor(0,0)
lcd.message('   0123456789   ')
# lcd.set_cursor(0,1)
# lcd.message('   \x01\x01\x01\x01\x01\x01\x01\x01\x01\x01   ')

card_list = []

slot_list = ["sdc", "sdg", "sdk", "sdo", "sda", "sde", "sdi", "sds", "sdq", "sdm"]
slot_micro_list = ["sdd", "sdh", "sdl", "sdp", "sdb", "sdf", "sdj", "sdt", "sdr", "sdn"]

x = 0


device_state = True







while device_state:
    time.sleep(0.01) #To prevent excessive CPU use


    if btn_press_time != 0 and (time.time() - btn_press_time) > 3:
        btn_press_time = 0
        GPIO.output(led_pin, GPIO.LOW)
        device_state = False
        print("Shutdown")



    if state == State.load:

      if accept_time != 0 and (time.time() - accept_time) > 3:
        accept_time = 0
        lcd.set_cursor(0,1)
        lcd.message("Working...")
        load_result = loadSlot()
        if load_result != "":
          lcd.set_cursor(0,1)
          txt = "Load: %-10s" % (load_result)
          lcd.message(txt)

          # Update available slots
          availableSlots = os.listdir("/home/pi/sd_duplicator/slots")
        else:
          lcd.set_cursor(0,1)
          lcd.message("Load failed!    ")
        time.sleep(1)

      if needScreenUpdate():
        lcd.set_cursor(0,0)
        lcd.message('Load new content')
        lcd.set_cursor(0,1)
        txt = "Hold            "
        if accept_time != 0:
          txt = "%-4d" % (3 - (time.time() - accept_time))
        lcd.message(txt)

    elif state == State.program:

      if program_state:
        # Detect connected SD cards
        new_list = getConnectedDrives()

        in_diff = list(set(new_list) - set(card_list))
        out_diff = list(set(card_list) - set(new_list))
        card_list = new_list

        if(in_diff):
          for drive in in_diff:
            print("In: " + drive)
            indices = [i for i, s in enumerate(slot_list) if drive in s]
            if len(indices) == 0:
                indices = [i for i, s in enumerate(slot_micro_list) if drive in s]

            if len(indices) != 0:
                print(indices[0])
                card_state[indices[0]] = 1
                writeSdCard(drive, indices[0], availableSlots[slot])

        if(out_diff):
          for drive in out_diff:
            print("Out: " + drive)
            indices = [i for i, s in enumerate(slot_list) if drive in s]
            if len(indices) == 0:
                indices = [i for i, s in enumerate(slot_micro_list) if drive in s]

            if len(indices) != 0:
                card_state[indices[0]] = 0

        if needScreenUpdate():
          lcd.set_cursor(0,0)
          lcd.message('   0123456789   ')
          lcd.set_cursor(0,1)
          lcd.message('   ')
          for i in range(0,10):
            if card_state[i] == 0:
                lcd.write8(ord('\x01'), True)
            elif card_state[i] == 1:
                lcd.write8(ord('\x02'), True)
            else:
                lcd.write8(ord('\x03'), True)
      else:
        if accept_time != 0 and (time.time() - accept_time) > 3:
          accept_time = 0
          if len(availableSlots) > 0:
            program_state = True

        if needScreenUpdate():
          lcd.set_cursor(0,0)
          if accept_time != 0:
            txt = '     Program   %d' % (3 - (time.time() - accept_time))
          else:
            txt = '     Program    '
          lcd.message(txt)
          lcd.set_cursor(0,1)
          if len(availableSlots) > 0:
            txt = "%-16s" % (availableSlots[slot])
          else:
            txt = "No data!"
          lcd.message(txt)
        


lcd.clear()
lcd.set_cursor(0,0)
lcd.message('    Shutdown    ')

call("sudo shutdown now", shell=True)
