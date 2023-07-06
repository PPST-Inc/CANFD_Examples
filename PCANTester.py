######################################################################
#  PCAN-Test 
#
#
#  ------------------------------------------------------------------
#  Author : Hernan Ferreyra
#  Language: Python 3.11
#  ------------------------------------------------------------------
#
######################################################################

from PCANBasic import *        ## PCAN-Basic library import

#import tkMessageBox            ## Simple-Messages library
import traceback                ## Error-Tracing library

import string                   ## String functions
#import tkFont                  ## Font-Management library

import time                     ## Time-related library
from time import sleep

import threading                ## Threading-based Timer library

import platform                 ## Underlying platform�s info library

import logging

import cantools

import sys

import asyncio

from pprint import pprint

db = cantools.database.load_file('test.dbc')
db.messages
log_file_name = 'can_test_log.txt'#+time.strftime('%Y_%m_%d_%I_%M_%S.log')

logging.FileHandler(log_file_name,"w")

logging.basicConfig(
    filename=log_file_name,
    encoding='utf-8',
    format='%(message)s',#:%(asctime)s:%(created)f %(levelname)s:
    datefmt='%I:%M:%S',
    level=logging.DEBUG
    )
logging.getLogger().addHandler(logging.StreamHandler())

logging.info('USB CAN TEST LOG\n')
logging.info(f'File : {log_file_name}')
dateString = time.strftime('%I:%M:%S %m/%d/%Y')
logging.info(f'Date : {dateString}')


a_message = db.messages[0]

a_signals = a_message.signals
argument_data = dict()

for signal in a_signals:
    pprint(signal.name)

m_PcanHandle = PCAN_NONEBUS

m_objPCANBasic = PCANBasic()

###*****************************************************************
### Error def 
###*****************************************************************

#Make a const dict
#const Errors_String = dict  [error num]

def ErrorStringEq(num):
    nucase
    return ""

###*****************************************************************
### Timer class
###*****************************************************************
class TimerRepeater(object):

    """
    A simple timer implementation that repeats itself
    """

    # Constructor
    #
    def __init__(self, name, interval, target, isUi, args=[], kwargs={}):
        """
        Creates a timer.

        Parameters:
            name        name of the thread
            interval    interval in second between execution of target
            target      function that is called every 'interval' seconds
            args        non keyword-argument list for target function
            kwargs      keyword-argument list for target function
        """
        # define thread and stopping thread event
        self._name = name
        self._thread = None
        self._event = None
        self._isUi = isUi
        # initialize target and its arguments
        self._target = target
        self._args = args
        self._kwargs = kwargs
        # initialize timer
        self._interval = interval
        self._bStarted = False

    # Runs the thread that emulates the timer
    #
    def _run(self):
        """
        Runs the thread that emulates the timer.

        Returns:
            None
        """
        while not self._event.wait(self._interval):
            self._target(*self._args, **self._kwargs)

    # Starts the timer
    #
    def start(self):
        """
        Starts the timer

        Returns:
            None
        """
        # avoid multiple start calls
        if (self._thread == None):
            self._event = threading.Event()
            self._thread = threading.Thread(None, self._run, self._name)
            self._thread.start()

    # Stops the timer
    #
    def stop(self):
        """
        Stops the timer

        Returns:
            None
        """
        if (self._thread != None):
            self._event.set()
            self._thread = None


###*****************************************************************


###*****************************************************************
### PCAN Tester app
###*****************************************************************
class PCANTester(object):
    ## Constructor
    ##
    def __init__(self):
        self.m_Parent = 1
        self.exit = -1
        self.m_IsFD = False
        self._lock = threading.RLock()
        self.m_PcanHandle = self.ReadTest()
        self.LastMsgTimeStamp = TPCANTimestampFD()
        self.m_LastMsgsList = []
        self.periodicTimestampList = []
        self.processMessageFunction = self.ProcessMessage
        self.Initializetimer()
        self.writeSem = threading.Semaphore(0)
        self.CANMsgWrt= TPCANMsg()
        self.CANMesageReceived = db.messages[0]


    ## Destructor
    ##
    def destroy (self):
        self.tmrRead.stop()


    ## Message loop
    def loop(self):
        # Catch keyboard interrupts easier, and avoids
        # 20 mseconds dead sleep() which burns a constant CPU.
        while self.exit < 0:
            try:
                while self.exit < 0:
                    sleep(1)
            except SystemExit:
                self.exit = 1
                return
            except KeyboardInterrupt:
                self.exit = 1
                return
            except:
                # Otherwise it's some other error
                t, v, tb = sys.exc_info()
                text = ""
                for line in traceback.format_exception(t,v,tb):
                    text += line + '\n'
                try: logging.info(text)
                except: pass
                self.exit = 1
                raise(SystemExit, 1)


    def TestStage1(self):
        sleep(0.500)
        self.tmrRead.stop()
        self.processMessageFunction = self.PeriodicsProcessMessage
        self.Initializetimer()
        sleep(3)
        self.tmrRead.stop()

        if len(self.periodicTimestampList) > 1 :
            prevSt=self.periodicTimestampList.pop(0)
            average_period = 0
            for stamp in self.periodicTimestampList:
                stamp_value = (stamp.micros + 1000 * stamp.millis + 0x100000000 * 1000 * stamp.millis_overflow)
                prevSt_value = (prevSt.micros + 1000 * prevSt.millis + 0x100000000 * 1000 * prevSt.millis_overflow)
                average_period += (stamp_value - prevSt_value) / 1000

                prevSt = stamp

            average_period = average_period / len(self.periodicTimestampList)

            logging.info(f'Periodics enable, periodic messages reception at {average_period:03.2f} ms')
        else:
            logging.info(f'Periodics messages are disabled')
            return 1
        return 0

    def getter_sended(self, name, n_messages): 
        try:
            first_message = db.get_message_by_name(name)
        except KeyError:
            logging.info(f'Failed getting messages from data base')
            return 3
 
        self.processMessageFunction = self.ProcessWriteAnswer
        self.Initializetimer()
        
        for i in range(n_messages):
            a_message = db.get_message_by_frame_id(first_message.frame_id+i)
            self.CANMsgWrt= TPCANMsg()
            self.CANMsgWrt.ID  = a_message.frame_id
            self.CANMsgWrt.LEN = a_message.length
            self.CANMsgWrt.MSGTYPE = PCAN_MESSAGE_STANDARD
            #self.CANMsgWrt.DATA
            stsResult = self.WriteFrameFD() if self.m_IsFD else self.WriteFrame()
            if stsResult != PCAN_ERROR_OK:
                logging.debug(m_objPCANBasic.GetErrorText(stsResult, 0x09)[1])
                testStage2Result = 2
                break
            delta_time = time.time_ns()
            if self.writeSem.acquire(True, 5):
                delta_time = (time.time_ns() - delta_time) / 1000000
                for signame,value in self.CANMesageReceived.items():
                    logging.info(f'{a_message.name} {delta_time:0.0f} ms - {signame}: {value:0.2f}' )
                self.CANMesageReceived
                testStage2Result = 0
            else:
                logging.info(f'Fail to read Get messages')
                testStage2Result = 1
        
        self.tmrRead.stop()
        return testStage2Result

    def TestStage2(self):
        return self.getter_sended('Get_messages_1',4)

    def TestStage3(self):
        return self.getter_sended('Get_configuration_1',6)

    def TestStage4(self):
        return self.getter_sended('Get_Protection_1',8)


    def WriteFrame(self):
        return m_objPCANBasic.Write(self.m_PcanHandle, self.CANMsgWrt)

    def Initializetimer(self):
        self.tmrRead = TimerRepeater("tmrRead", 0.010, self.ReadMessages, False)
        
        self.tmrRead.start()
        ##self.PCANBasicWrite()

    def PCANBasicReadMessage(self):
            result = m_objPCANBasic.Read(self.m_PcanHandle)
            if result[0] == PCAN_ERROR_OK:
                #self.ProcessMessageFD(result[1:])
                self.processMessageFunction(result[1:])

            return result[0]

    def ReadMessages(self):
        stsResult = PCAN_ERROR_OK
        m_CanRead = True
        # We read at least one time the queue looking for messages.
        # If a message is found, we look again trying to find more.
        # If the queue is empty or an error occurr, we get out from
        # the dowhile statement.
        #
        while (m_CanRead and not (stsResult & PCAN_ERROR_QRCVEMPTY)):
            stsResult = self.PCANBasicReadMessage()
            if stsResult == PCAN_ERROR_ILLOPERATION:
                break

    def ReadTest(self):
        m_LastMsgsList = []


        #init.Read();


        m_NonPnPHandles = {'PCAN_ISABUS1':PCAN_ISABUS1, 'PCAN_ISABUS2':PCAN_ISABUS2, 'PCAN_ISABUS3':PCAN_ISABUS3, 'PCAN_ISABUS4':PCAN_ISABUS4, 
                                    'PCAN_ISABUS5':PCAN_ISABUS5, 'PCAN_ISABUS6':PCAN_ISABUS6, 'PCAN_ISABUS7':PCAN_ISABUS7, 'PCAN_ISABUS8':PCAN_ISABUS8, 
                                    'PCAN_DNGBUS1':PCAN_DNGBUS1}

        m_BAUDRATES = {'1 MBit/sec':PCAN_BAUD_1M, '800 kBit/sec':PCAN_BAUD_800K, '500 kBit/sec':PCAN_BAUD_500K, '250 kBit/sec':PCAN_BAUD_250K,
                                '125 kBit/sec':PCAN_BAUD_125K, '100 kBit/sec':PCAN_BAUD_100K, '95,238 kBit/sec':PCAN_BAUD_95K, '83,333 kBit/sec':PCAN_BAUD_83K,
                                '50 kBit/sec':PCAN_BAUD_50K, '47,619 kBit/sec':PCAN_BAUD_47K, '33,333 kBit/sec':PCAN_BAUD_33K, '20 kBit/sec':PCAN_BAUD_20K,
                                '10 kBit/sec':PCAN_BAUD_10K, '5 kBit/sec':PCAN_BAUD_5K}

        m_HWTYPES = {'ISA-82C200':PCAN_TYPE_ISA, 'ISA-SJA1000':PCAN_TYPE_ISA_SJA, 'ISA-PHYTEC':PCAN_TYPE_ISA_PHYTEC, 'DNG-82C200':PCAN_TYPE_DNG,
                            'DNG-82C200 EPP':PCAN_TYPE_DNG_EPP, 'DNG-SJA1000':PCAN_TYPE_DNG_SJA, 'DNG-SJA1000 EPP':PCAN_TYPE_DNG_SJA_EPP}

        m_IOPORTS = {'0100':0x100, '0120':0x120, '0140':0x140, '0200':0x200, '0220':0x220, '0240':0x240, '0260':0x260, '0278':0x278, 
                            '0280':0x280, '02A0':0x2A0, '02C0':0x2C0, '02E0':0x2E0, '02E8':0x2E8, '02F8':0x2F8, '0300':0x300, '0320':0x320,
                            '0340':0x340, '0360':0x360, '0378':0x378, '0380':0x380, '03BC':0x3BC, '03E0':0x3E0, '03E8':0x3E8, '03F8':0x3F8}

        m_INTERRUPTS = {'3':3, '4':4, '5':5, '7':7, '9':9, '10':10, '11':11, '12':12, '15':15}
    
        baudrate = PCAN_BAUD_500K
        hwtype = PCAN_TYPE_ISA_SJA
        ioport = 0x100
        interrupt = 3
        
        result =  m_objPCANBasic.GetValue(PCAN_NONEBUS, PCAN_ATTACHED_CHANNELS)
        channels_handlers = []
        if  (result[0] == PCAN_ERROR_OK):
            # Include only connectable channels
            #
            for channel in result[1]:
                if  (channel.channel_condition & PCAN_CHANNEL_AVAILABLE):
                        l_PcanHandle = channel.channel_handle
                        verstring =f'l_PcanHandle is {l_PcanHandle}'
                        result =  m_objPCANBasic.Initialize(l_PcanHandle,baudrate,hwtype,ioport,interrupt)
                        if result != PCAN_ERROR_OK:
                            if result != PCAN_ERROR_CAUTION:
                                logging.debug(m_objPCANBasic.GetErrorText(result, 0x09)[1])
                        else:
                            logging.debug(f'Channel handle {channel.channel_handle}')
                            break
        logging.debug("USB CAN - connection established\n")
        return  l_PcanHandle


    ###*****************************************************************
    ### Message-proccessing functions
    def ProcessMessageFD(self, *args):
        with self._lock:
            # Split the arguments. [0] TPCANMsgFD, [1] TPCANTimestampFD
            #
            theMsg = args[0][0]
            itsTimeStamp = args[0][1]


    def ProcessWriteAnswer(self, *args):
        with self._lock:
            theMsg = args[0][0]
            if self.CANMsgWrt.ID == theMsg.ID:
                try:
                    self.CANMesageReceived = db.decode_message(self.CANMsgWrt.ID, theMsg.DATA )
                    self.writeSem.release(1)
                except KeyError:
                    return


    def PeriodicsProcessMessage(self, *args):
        with self._lock:
            theMsg = args[0][0]
            itsTimeStamp = args[0][1]
            try:
                decoded = db.decode_message(theMsg.ID, theMsg.DATA )
                #for key in decoded.keys():
                #    if key > "Periodic_":
                #        periodic_key = key
                #decoded_val = decoded[periodic_key]

                decoded_val = decoded["Periodic_Voltage_ACDC"]
                self.periodicTimestampList.append(itsTimeStamp)
            except KeyError:
                return
            return


    def ProcessMessage(self, *args):        
        with self._lock:       
            # Split the arguments. [0] TPCANMsg, [1] TPCANTimestamp
            #
            theMsg = args[0][0]
            itsTimeStamp = args[0][1]    

            newMsg = TPCANMsgFD()
            newMsg.ID = theMsg.ID
            newMsg.DLC = theMsg.LEN
            for i in range(8 if (theMsg.LEN > 8) else theMsg.LEN):
                newMsg.DATA[i] = theMsg.DATA[i]
            newMsg.MSGTYPE = theMsg.MSGTYPE
            newTimestamp = TPCANTimestampFD()
            newTimestamp.value = (itsTimeStamp.micros + 1000 * itsTimeStamp.millis + 0x100000000 * 1000 * itsTimeStamp.millis_overflow)
            self.ProcessMessageFD([newMsg, newTimestamp])


###*****************************************************************
###*    Run program
basicExl = PCANTester()

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 1 start')
stageResult = basicExl.TestStage1()
stageResultText =''
logging.info(f'###*    Stage end at {stageResult} {stageResultText}\n')


logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 2 start')
stageResult =basicExl.TestStage2()
if stageResult != 0:
    stageResultText = ''
    logging.info(f'###*    Stage end at {stageResult} {stageResultText}\n')
    basicExl.destroy()
    exit()
logging.info(f'###*    Stage end at {stageResult}\n')


logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 3 start')
stageResult = basicExl.TestStage3()
logging.info(f'###*    Stage end at {stageResult}\n')

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 4 start')
stageResult = basicExl.TestStage4()
logging.info(f'###*    Stage end at {stageResult}\n')



basicExl.destroy()