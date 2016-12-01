#!/usr/bin/env python
# -*- coding: utf8 -*-
import RPi.GPIO as GPIO
import MFRC522
import signal
import requests
import json
import time
import syncano
import os
from syncano.models import Object
connection = syncano.connect(instance_name=os.environ['INSTANCE_NAME'], api_key=os.environ['SYNCANO_API_KEY'], user_key=os.environ['SYNCANO_USER_KEY'])
#----------- CONFIGURATION -------
global pinNumber
global curr_state
global prev_state
__input = {'sensor': 11}
output = {'relay': 13, 'greenDiode': 18, 'redDiode': 16, 'buzzer': 7, 'sensor': 11}
pinNumber = []
#---------------- END CONFIG --------
class keypad():
      # CONSTANTS
      KEYPAD = [
      [1,2,3,"A"],
      [4,5,6,"B"],
      [7,8,9,"C"],
      ["*",0,"#","D"]
      ]

      COLUMN         = [32,36,38,40]
      ROW        = [31,33,35,37]
      def getKey(self):


		#set all columns as output low
        for j in range(len(self.COLUMN)):
            GPIO.setup(self.COLUMN[j], GPIO.OUT)
            GPIO.output(self.COLUMN[j], GPIO.LOW)
	#set all rows as input
        for i in range(len(self.ROW)):
            GPIO.setup(self.ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)
	#Scan rows for pushed key/button
	# A valid key press should set "rowVal" between 0 and 4
        rowVal = -1
        for i in range(len(self.ROW)):
            tmpRead = GPIO.input(self.ROW[i])
            if tmpRead == 0:
                rowVal = i
	#if rowVal is not 0 and 4 no button was pressed (exit)
        if rowVal < 0 or rowVal > 4:
            self.exit()
            return
	#convert columns to input
        for j in range(len(self.COLUMN)):
            GPIO.setup(self.COLUMN[j], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
	#swith the i-th row found from scan to output
        GPIO.setup(self.ROW[rowVal], GPIO.OUT)
        GPIO.output(self.ROW[rowVal], GPIO.HIGH)
	#Scan columns for still-pushed key/button
	#A valid key press should set "colVal" Between 0 and 2
        colVal = -1
        for j in range(len(self.COLUMN)):
            tmpRead = GPIO.input(self.COLUMN[j])
            if tmpRead == 1:
                colVal = j
	#if colVAl is not from 0 to  2 then no button was pressed
        if colVal < 0 or colVal > 3:
            self.exit()
            return
	#return the value of the key pressed
        self.exit()
        return self.KEYPAD[rowVal][colVal]
      def exit(self):
        for i in range(len(self.ROW)):
          GPIO.setup(self.ROW[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        for j in range(len(self.COLUMN)):
          GPIO.setup(self.COLUMN[j], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def diodeControl(status):
	print "STATUS OF LOCK: "
	print status
	GPIO.output(output['buzzer'],status)
	GPIO.output(output['greenDiode'],status)
	GPIO.output(output['redDiode'],not status)
	Object.please.update(class_name='doors', status='Open', id='758')
	GPIO.output(output['relay'],not status)
	if status==False:
		for x in range(0,5):
			GPIO.output(output['buzzer'], 1)
			GPIO.output(output['redDiode'],1)
			time.sleep(0.1)
			GPIO.output(output['buzzer'], 0)
			GPIO.output(output['redDiode'],0)
			time.sleep(0.1)
			GPIO.output(output['redDiode'],1)
	else:
		doorClose()
def doorClose():
	#TODO Implement post request with update on door status
	time.sleep(1.5)
	GPIO.output(output['greenDiode'],GPIO.LOW)
	GPIO.output(output['redDiode'],GPIO.HIGH)
	GPIO.output(output['buzzer'],GPIO.LOW)
	Object.please.update(class_name='doors', status='Close', id='758')
	GPIO.output(output['relay'], True)
continue_reading = True
# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print "Ctrl+C captured, ending read."
    continue_reading = False
    GPIO.cleanup()

# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)

# Create an object of the class MFRC522
MIFAREReader = MFRC522.MFRC522()
prev_state = False
GPIO.setup(__input['sensor'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
curr_state = False
GPIO.setup(output['relay'], GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(output['redDiode'], GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(output['greenDiode'], GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(output['buzzer'], GPIO.OUT, initial=GPIO.LOW)
url = 'https://api.syncano.io/v1.1/instances/muddy-paper-3302/endpoints/scripts/p/fce74a641ded7f277d2aeeaeafff7561146cac9b/door_open/'

# Welcome message
print "Welcome to the MFRC522 data read example"
print "Press Ctrl-C to stop."
# This loop keeps checking for chips. If one is near it will get the UID and authenticate
def readReedSwitch():
	global prev_tate
	global curr_state
	prev_state = curr_state
	curr_state = GPIO.input(__input['sensor'])
	if curr_state != prev_state:
		if curr_state:
			doors = Object.please.update(class_name='doors', id=758, status='Open')
			print (curr_state, str(doors.name))
		else:
			Object.please.update(class_name='doors',status= 'Closed',id='758')
			print curr_state


def readKeypad():
	global pinNumber
	kp = keypad()
	digit=kp.getKey()
	if digit is not None:
		if digit is not '*':
			pinNumber.append(digit)
			print pinNumber
		if digit is '*':
			pinString = ''.join(str(e) for e in pinNumber)
			print pinString
			r = requests.post(url, data ={'input_type': 'pin', 'door':758 , 'code': pinString})
			json_response = json.loads(r.text)
			diodeControl(json_response["door_status"])
			doorClose()
			pinNumber = []
			pinString = ''
		print digit
def readRFID():
	(status,TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
	# If we have the UID, continue
	(status,uid) = MIFAREReader.MFRC522_Anticoll()
	if status == MIFAREReader.MI_OK:

        # Print UID
		print "Card read UID: "+str(uid[0])+","+str(uid[1])+","+str(uid[2])+","+str(uid[3])

		r = requests.post(url, data = {'code':','.join(map(str,uid[:4])), 'door':758,'input_type':'rfid'})
		json_response = json.loads(r.text)
		print json_response['door_status']
		diodeControl(json_response['door_status'])
		continue_reading = True
while continue_reading:
	readReedSwitch()
	readKeypad()
    # Get the UID of the card
	readRFID()
