######################################################################
#  PCAN-Test 
#
#  ~~~~~~~~~~~~
#
#  ------------------------------------------------------------------
#  Author : Keneth Wagner
#  Language: Python 3.7
#  ------------------------------------------------------------------
#
#  Copyright (C) 1999-2020  PEAK-System Technik GmbH, Darmstadt
######################################################################

from PCANBasic import *        ## PCAN-Basic library import

## Imports for UI
##
#from Tkinter import *          ## TK UI library
#import Tix                     ## TK extensions library
from tkinter import *
from tkinter import tix
from tkinter import messagebox
from tkinter import font

#import tkMessageBox            ## Simple-Messages library
import traceback                ## Error-Tracing library

import string                   ## String functions
#import tkFont                  ## Font-Management library

import time                     ## Time-related library
import threading                ## Threading-based Timer library

import platform                 ## Underlying platform�s info library

import logging

import cantools

from pprint import pprint

db = cantools.database.load_file('get_file_can.dbc')
db.messages
log_file_name = 'can_test_'+time.strftime('%Y_%m_%d_%I_%M_%S.log')
pprint(log_file_name)

logging.basicConfig(
    filename=log_file_name,
    encoding='utf-8',
    format='%(message)s',#:%(asctime)s:%(created)f %(levelname)s:
    datefmt='%I:%M:%S',
    level=logging.DEBUG
    )

logging.info('CANDB PARSE %d' ,time.time_ns())
logging.info(db.messages)
logging.warning('A mensaggem')

a_message = db.get_message_by_name('Periodic_Measurements_Total')
a_message = db.messages[0]

a_signals = a_message.signals

argument_data = dict()

pprint(a_message)
for signal in a_signals:
    argument_data[signal.name] = 0xFF

pprint("Data to add:")
pprint(argument_data)
#data = a_message.encode({'Temperature': 250.1, 'AverageRadius': 3.2, 'Enable': 1})
data = a_message.encode(argument_data)
a_message = str(a_message) + str(time.time_ns())
pprint(a_message)
pprint(data)


