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

import traceback                ## Error-Tracing library

import time                     ## Time-related library
from time import sleep

import threading                ## Threading-based Timer library

import logging

import cantools

import sys

from pprint import pprint

###*****************************************************************
### Can Database Import
db = cantools.database.load_file('test.dbc')

### Can Hardware setup
testBaudrate = PCAN_BAUD_500K
testHardwareType = PCAN_TYPE_ISA_SJA
testCANFD = False

tableSetPointsControl ={
    'Setpoint_Enable_Output': 0,
    'Setpoint_Current_Limit': 29.365,
    'Setpoint_KVA_Limit': 4.21,
    'Setpoint_Power_Limit': 3.156,
    'Setpoint_Program_Frequency': 54.32,
    'Setpoint_Program_Voltage_AC': 6.32,
    'Setpoint_Program_Voltage_DC': 5.28,

    'Setpoint_Current_Limit_A': 0,#18.365,
    'Setpoint_Current_Limit_B': 0,
    'Setpoint_Current_Limit_C': 0,

    'Setpoint_KVA_Limit_A': 0,#2.3,
    'Setpoint_KVA_Limit_B': 0,
    'Setpoint_KVA_Limit_C': 0,

    'Setpoint_Phase_Offset_Output_B': 0,
    'Setpoint_Phase_Offset_Output_C': 0,

    'Setpoint_Power_Limit_A': 0,#2.456,
    'Setpoint_Power_Limit_B': 0,
    'Setpoint_Power_Limit_C': 0,

    'Setpoint_Program_Frequency_A': 0,#63.41,
    'Setpoint_Program_Frequency_B': 0,
    'Setpoint_Program_Frequency_C': 0,
    
    'Setpoint_Program_Voltage_AC_A': 0,#5.82,
    'Setpoint_Program_Voltage_AC_B': 0,
    'Setpoint_Program_Voltage_AC_C': 0,
    
    'Setpoint_Program_Voltage_DC_A': 0,#9.11,
    'Setpoint_Program_Voltage_DC_B': 0,
    'Setpoint_Program_Voltage_DC_C': 0,
}

tableSetPointsConfigurationRampAndSlew ={
    'Config_Slew_Frequency':0,
    'Config_Slew_Phase':0,
    'Config_Slew_Ramp_Time':0,
    'Config_Slew_Voltage_AC':0,
    'Config_Slew_Voltage_DC':0
}

tableSetPointsConfigurationUnit = {
'Config_Unit_C_Self_Calibration':0,
'Config_Unit_Fault_On_Saturation':0,
'Config_Unit_Form':0,
'Config_Unit_Max_CSC_Gain':0,
'Config_Unit_Mode':0,
'Config_Unit_Out_Impedance_Mode':0,
'Config_Unit_Out_Phase_Disable':0,
'Config_Unit_Phase_Rotation':0,
'Config_Unit_Update_Phase':0,
'Config_Unit_Voltage_Range':0
}
###*****************************************************************
### PCANBasic Object 

m_objPCANBasic = PCANBasic()

###*****************************************************************
### Logger file configuration
loggerFileName = 'can_test_log.txt'
logging.FileHandler(loggerFileName,"w")

logging.basicConfig(
    filename=loggerFileName,
    encoding='utf-8',
    format='%(message)s',#:%(asctime)s:%(created)f %(levelname)s:
    datefmt='%I:%M:%S',
    level=logging.DEBUG
    )
logging.getLogger().addHandler(logging.StreamHandler())

logging.info('USB CAN TEST LOG\n')
logging.info(f'File : {loggerFileName}')
dateString = time.strftime('%I:%M:%S %m/%d/%Y')
logging.info(f'Date : {dateString}')

###*****************************************************************
### Error strings
###*****************************************************************
def ErrorString(status):
    match status:
        case 0:
            return "Ok"
        case 1:
            return "Error"
        case 2:
            return "Communication error"
        case 3:
            return "Failed getting messages from data base"
        case _:
            return "Unspecified error"

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

    # Runs the thread that emulates the timer
    #
    def Run(self):
        """
        Runs the thread that emulates the timer.

        Returns:
            None
        """
        while not self._event.wait(self._interval):
            self._target(*self._args, **self._kwargs)

    def Start(self):
        if (self._thread == None):
            self._event = threading.Event()
            self._thread = threading.Thread(None, self.Run, self._name)
            self._thread.start()

    # Stops the timer
    #
    def Stop(self):
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
        self.m_IsFD = testCANFD
        self._lock = threading.RLock()
        self.m_PcanHandle = self.InitializeCan()
        self.periodicTimestampList = []
        self.processMessageFunction = self.ProcessMessage
        self.Initializetimer()
        self.writeSem = threading.Semaphore(0)
        self.canMsgWrt= TPCANMsg()
        self.canMesageReceived = db.messages[0]


    ## Destructor
    ##
    def Destroy (self):
        self.tmrRead.Stop()


    def Loop(self):
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


    def StageTest1(self):
        sleep(0.500)
        self.tmrRead.Stop()
        self.processMessageFunction = self.PeriodicsProcessMessage
        self.Initializetimer()
        sleep(3)
        self.tmrRead.Stop()

        if len(self.periodicTimestampList) > 1 :
            prevSt=self.periodicTimestampList.pop(0)
            averagePeriod = 0
            for stamp in self.periodicTimestampList:
                stampValue = (stamp.micros + 1000 * stamp.millis + 0x100000000 * 1000 * stamp.millis_overflow)
                prevStvalue = (prevSt.micros + 1000 * prevSt.millis + 0x100000000 * 1000 * prevSt.millis_overflow)
                averagePeriod += (stampValue - prevStvalue) / 1000

                prevSt = stamp

            averagePeriod = averagePeriod / len(self.periodicTimestampList)

            logging.info(f'Periodics enable, periodic messages reception at {averagePeriod:03.2f} ms')
        else:
            logging.info(f'Periodics messages are disabled')
            return 1
        return 0

    def RequestGetMessages(self, name, nMessages): 
        try:
            firstMessage = db.get_message_by_name(name)
        except KeyError:
            logging.info(f'Failed getting messages from data base')
            return 3
 
        self.processMessageFunction = self.ProcessRequestAnswer
        self.Initializetimer()
        
        for i in range(nMessages):
            a_message = db.get_message_by_frame_id(firstMessage.frame_id+i)
            self.canMsgWrt= TPCANMsg()
            self.canMsgWrt.ID  = a_message.frame_id
            self.canMsgWrt.LEN = a_message.length
            self.canMsgWrt.MSGTYPE = PCAN_MESSAGE_STANDARD
            countString = ''
            for j in range(2):
                stsResult = self.WriteFrameFD() if self.m_IsFD else self.WriteFrame()
                if stsResult != PCAN_ERROR_OK:
                    logging.info(m_objPCANBasic.GetErrorText(stsResult, 0x09)[1])
                    testStage2Result = 2
                    self.tmrRead.Stop()
                    return testStage2Result
                deltaTime = time.time_ns()
                if self.writeSem.acquire(True, 5):
                    deltaTime = (time.time_ns() - deltaTime) / 1000000
                    countString =countString + '-'
                    self.canMesageReceived
                    testStage2Result = 0
                else:
                    logging.info(f'Fail to read Get messages')
                    testStage2Result = 1
                    self.tmrRead.Stop()
                    return testStage2Result

            pprint(f'{a_message.name} {countString}')
            for signame,value in self.canMesageReceived.items():
                logging.info(f'{a_message.name} {deltaTime:0.0f} ms - {signame}: {round(value,2)}' )
    
        self.tmrRead.Stop()
        return testStage2Result

    def StageTest2(self):
        logging.info(f'Measurements Get')
        error = self.RequestGetMessages('Get_messages_1',4)
        if error !=0 :  return

        logging.info(f'\nConfigurations')
        error = self.RequestGetMessages('Get_configuration_1',6)
        if error !=0 :  return

        logging.info(f'\nProtection Parameters')
        error = self.RequestGetMessages('Get_Protection_1',8)
        if error !=0 :  return
 
        logging.info(f'\nProtection Parameters')
        error = self.RequestGetMessages('Get_Setpoints_1',14)
        return error

    def SetpointMessages (self, name , nMessages):

        try:
            firstMessage = db.get_message_by_name(name)
        except KeyError:
            logging.info(f'Failed getting messages from data base')
            return 3
        
        self.processMessageFunction = self.ProcessSetpointAnswer
        self.Initializetimer()
        for i in range(nMessages):
            setMessage = db.get_message_by_frame_id(firstMessage.frame_id+i)
            toSendData = dict()
            for signal in setMessage.signals:
                toSendData[signal.name]=tableSetPointsControl[signal.name]

            data = setMessage.encode(toSendData)

            self.canMsgWrt= TPCANMsg()
            self.canMsgWrt.ID  = setMessage.frame_id
            self.canMsgWrt.LEN = setMessage.length
            self.canMsgWrt.MSGTYPE = PCAN_MESSAGE_STANDARD
            for i in range(8 if (self.canMsgWrt.LEN > 8) else self.canMsgWrt.LEN):
                self.canMsgWrt.DATA[i]=  data[i]

            #Send Data
            stsResult = self.WriteFrameFD() if self.m_IsFD else self.WriteFrame()
            if stsResult != PCAN_ERROR_OK:
                logging.info(m_objPCANBasic.GetErrorText(stsResult, 0x09)[1])
                testStage3Result = 2
                self.tmrRead.Stop()
                return testStage3Result
            deltaTime = time.time_ns()
            if self.writeSem.acquire(True, 2):
                deltaTime = (time.time_ns() - deltaTime) / 1000000
                testStage3Result = 0
                for signame,value in toSendData.items():
                    signalsArray = (f'{signame}: as {value}' )
                logging.info(f'{deltaTime:0.0f} ms - Setpoints Seted {signalsArray}')

            else:
                logging.info(f'Fail to communicate setpoint')
                testStage3Result = 1
                self.tmrRead.Stop()
                return testStage3Result

        self.tmrRead.Stop()
        return testStage3Result

    def StageTest3(self):
        logging.info(f'StageTest3 process')

        logging.info(f'Setpoints B Write')
        self.SetpointMessages('Setpoint_B_1' , 4)

        logging.info(f'Setpoints C Write')
        self.SetpointMessages('Setpoint_C_1' , 4)

        logging.info(f'Setpoints A Write')
        self.SetpointMessages('Setpoint_A_1' , 3)

        logging.info(f'Setpoints All Write')
        return self.SetpointMessages('Setpoint_All_1' , 3)




    def StageTest4(self):
        logging.info(f'StageTest4')

    def StageTest5(self):
        logging.info(f'StageTest5')

    def WriteFrame(self):
        return m_objPCANBasic.Write(self.m_PcanHandle, self.canMsgWrt)

    def Initializetimer(self):
        self.tmrRead = TimerRepeater("tmrRead", 0.010, self.ReadMessages, False)
        
        self.tmrRead.Start()
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

    def InitializeCan(self):
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
    
        baudrate = testBaudrate
        hwtype = testHardwareType
        ioport = 0x100
        interrupt = 3
        
        result =  m_objPCANBasic.GetValue(PCAN_NONEBUS, PCAN_ATTACHED_CHANNELS)

        if  (result[0] == PCAN_ERROR_OK):
            # Include only connectable channels
            for channel in result[1]:
                if  (channel.channel_condition & PCAN_CHANNEL_AVAILABLE):
                        l_PcanHandle = channel.channel_handle
                        verstring =f'l_PcanHandle is {l_PcanHandle}'
                        result =  m_objPCANBasic.Initialize(l_PcanHandle,baudrate,hwtype,ioport,interrupt)
                        if result != PCAN_ERROR_OK:
                            if result != PCAN_ERROR_CAUTION:
                                logging.info(m_objPCANBasic.GetErrorText(result, 0x09)[1])
                        else:
                            logging.info(f'Channel handle {channel.channel_handle}')
                            logging.info("USB CAN - connection established\n")
                            return  l_PcanHandle
        logging.info("USB CAN - connection failed\n")
        logging.info(f'###*    Test End')
        logging.info(f'###*****************************************************************')
        exit()

    ###*****************************************************************
    ### Message-proccessing functions
    def ProcessMessageFD(self, *args):
        with self._lock:
            # Split the arguments. [0] TPCANMsgFD, [1] TPCANTimestampFD
            #
            theMsg = args[0][0]
            itsTimeStamp = args[0][1]

    def ProcessSetpointAnswer(self, *args):
        with self._lock:
            theMsg = args[0][0]
            try:
                ackStatus = db.decode_message(theMsg.ID, theMsg.DATA )["Ack_App_Signal"]
                if ackStatus == 0:
                    self.writeSem.release(1)
            except KeyError:
                return

    def ProcessRequestAnswer(self, *args):
        with self._lock:
            theMsg = args[0][0]
            if self.canMsgWrt.ID == theMsg.ID:
                try:
                    self.canMesageReceived = db.decode_message(self.canMsgWrt.ID, theMsg.DATA )
                    self.writeSem.release(1)
                except KeyError:
                    return

    def PeriodicsProcessMessage(self, *args):
        with self._lock:
            theMsg = args[0][0]
            itsTimeStamp = args[0][1]
            try:
                db.decode_message(theMsg.ID, theMsg.DATA )["Periodic_Voltage_ACDC"]
                self.periodicTimestampList.append(itsTimeStamp)
            except KeyError:
                return

    def ProcessMessage(self, *args):        
        with self._lock:       
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
###*    Run Test
logging.info(f'###*****************************************************************')
logging.info(f'###*    Test Start')

basicExl = PCANTester()

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 1 Start')
stageResult = basicExl.StageTest1()
logging.info(f'###*    Stage end at {stageResult} {ErrorString(stageResult)}\n')

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 2 Start')
logging.info(f'###*    Reading all get messages avaiable in can database file\n')
stageResult = basicExl.StageTest2()
if stageResult != 0:
    stageResultText = ''
    logging.info(f'###*    Stage end at {stageResult} {ErrorString(stageResult)}\n')
    basicExl.Destroy()
    exit()
logging.info(f'###*    Stage end at {stageResult} {ErrorString(stageResult)} \n')

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 3 Start')
stageResult = basicExl.StageTest3()
logging.info(f'###*    Stage end at {stageResult} {ErrorString(stageResult)} \n')

logging.info(f'###*    Test end')
logging.info(f'###*****************************************************************')
basicExl.Destroy()