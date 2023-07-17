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

from struct import *

###*****************************************************************
### Can Database Import
db = cantools.database.load_file('updatedcanfdtest.dbc')

### Can Hardware setup
testBaudrate = PCAN_BAUD_1M
testHardwareType = PCAN_TYPE_ISA_SJA
testCANFD = False

tableSetPointsControl ={
    'SP_ALL_Current_Limit': 29.365,
    'SP_ALL_Enable_Output': 0,
    'SP_ALL_Frequency': 54.32, #  Fail value: 2.2
    'SP_ALL_KVA_Limit': 4.21,
    'SP_ALL_Power_Limit': 3.156,
    'SP_ALL_Voltage_AC': 6.32,
    'SP_ALL_Voltage_DC': 5.28,
    'SP_ALL_Phase': 0,
    

    'SP_A_Current_Limit': 18.365,
    'SP_B_Current_Limit': 0.0,
    'SP_C_Current_Limit': 0.0,

    'SP_A_KVA_Limit': 2.3,
    'SP_B_KVA_Limit': 0.0,
    'SP_C_KVA_Limit': 0.0,

    'SP_A_Phase': 0.0,
    'SP_B_Phase': 0.0,
    'SP_C_Phase': 0.0,

    'SP_A_Power_Limit': 2.456,
    'SP_B_Power_Limit': 0.0,
    'SP_C_Power_Limit': 0.0,

    'SP_A_Frequency': 63.41,
    'SP_B_Frequency': 0.0,
    'SP_C_Frequency': 0.0,

    'SP_A_Voltage_AC': 5.82, # Fail value: -1.0
    'SP_B_Voltage_AC': 0.0,
    'SP_C_Voltage_AC': 0.0,

    'SP_A_Voltage_DC': 9.11,
    'SP_B_Voltage_DC': 0.0,
    'SP_C_Voltage_DC': 0.0,
}

tableRampAndSlew ={
    'SC_Slew_Frequency':5.5,
    'SC_Slew_Phase':5.1,
    'SC_Slew_Voltage_AC':9.3,
    'SC_Slew_Voltage_DC':7.2
}

tableUnitSettings = {
    'SC_CSC_Enable':0,
    'SC_CSC_Fault_on_Saturation':0,
    'SC_CSC_Max_Gain':1.15,
    'SC_Form':3,
    'SC_Mode':2,
    'SC_Output_Disable_Phase':0,
    'SC_Output_Impedance_Mode':0,
    'SC_Phase_Rotation':0,
    'SC_Range':0,
    'SC_Update_Phase':0,
    'SC_Ramp_Time':1.2
}

tableProtections = {
    'SPP_Peak_Current_Enable': 1,
    'SPP_Peak_Current_Level': 41.67,
    'SPP_Peak_Current_Limit': 104.0,
    'SPP_Peak_Voltage_Enable': 1,
    'SPP_Peak_Voltage_Level': 275.0,
    'SPP_Peak_Voltage_Margin': 100.0,
    'SPP_Peak_Voltage_Mode': 0,
    'SPP_RMS_Current_Enable': 0,
    'SPP_RMS_Current_Level': 41.62,
    'SPP_RMS_KVA_Level': 5.0,
    'SPP_RMS_Power_Enable': 0,
    'SPP_RMS_Power_Level': 5.0,
    'SPP_RMS_Trip_Time': 15
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
        self.writeSem = threading.Semaphore(0)
        self.canMsgWrt= TPCANMsg()
        self.canMesageReceived = db.messages[0]
        self.tmrRead = TimerRepeater("tmrRead", 0.010, self.ReadMessages, False)
        self.uniqueTimerInitialized = False
        self.ackStatus = 0
        self.ackRequestFlag = False
        self.answerBytes = bytes()

    ## Destructor
    ##
    def Destroy (self):
        self.StopTimer()

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
        self.StopTimer()
        self.processMessageFunction = self.PeriodicsProcessMessage
        self.InitializeTimer()
        sleep(2)
        self.StopTimer()

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
        self.InitializeTimer()
        
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
                    self.StopTimer()
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
                    self.StopTimer()
                    return testStage2Result

            pprint(f'{a_message.name} {countString}')
            for signame,value in self.canMesageReceived.items():
                logging.info(f'{a_message.name} {deltaTime:0.0f} ms - {signame}: {round(value,2)}' )
    
        self.StopTimer()
        return testStage2Result

    def StageTest2(self):
        logging.info(f'Measurements Get')
        error = self.RequestGetMessages('Get_messages_1',11)
        if error !=0 :  return

        logging.info(f'\nConfigurations')
        error = self.RequestGetMessages('Get_configuration_1',7)
        if error !=0 :  return

        logging.info(f'\nProtection Parameters')
        error = self.RequestGetMessages('Get_Protection_1',8)
        if error !=0 :  return
 
        logging.info(f'\nSetpoints')
        error = self.RequestGetMessages('Get_Setpoints_1',16)
        return error

    def SetpointMessages (self, name , nMessages, tableValues):
        try:
            firstMessage = db.get_message_by_name(name)
        except KeyError:
            logging.info(f'Failed getting messages from data base')
            return 3
        
        self.processMessageFunction = self.ProcessSetpointAnswer
        self.InitializeTimer()
        for i in range(nMessages):
            setMessage = db.get_message_by_frame_id(firstMessage.frame_id+i)
            toSendData = dict()
            for signal in setMessage.signals:
                toSendData[signal.name] = tableValues[signal.name]

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
                self.StopTimer()
                return testStage3Result
            deltaTime = time.time_ns()
            if self.writeSem.acquire(True, 5):
                deltaTime = (time.time_ns() - deltaTime) / 1000000
                testStage3Result = 0
                signalsArray = ''
                for signame,value in toSendData.items():
                    signalsArray += (f'{signame}: as {value} ' )
                logging.info(f'{deltaTime:0.0f} ms - Set Done {signalsArray}')

            else:
                logging.info(f'Fail to set {toSendData} {setMessage}')

                testStage3Result = 1
                self.StopTimer()
                return testStage3Result

        self.StopTimer()
        return testStage3Result

    def StageTest3(self):
        logging.info(f'n\Protection Setpoints')
        self.SetpointMessages('Protection_Setpoint_1' , 8,tableProtections)

        logging.info(f'\nConfiguration Ramp and Slew Setpoints')
        self.SetpointMessages('Setpoint_Ramp_And_Slew_1' , 4,tableRampAndSlew)

        logging.info(f'\nConfiguration Unit Settings Setpoints')
        self.SetpointMessages('Setpoint_Unit_Settings_1' , 5,tableUnitSettings)

        logging.info(f'\nSetpoints B Write')
        self.SetpointMessages('Setpoint_B_1' , 4,tableSetPointsControl)

        logging.info(f'\nSetpoints C Write')
        self.SetpointMessages('Setpoint_C_1' , 4,tableSetPointsControl)

        logging.info(f'\nSetpoints A Write')
        self.SetpointMessages('Setpoint_A_1' , 3 ,tableSetPointsControl)
 
        sleep(3)
        logging.info(f'\nSetpoints All Write')
        return self.SetpointMessages('Setpoint_All_1' , 4,tableSetPointsControl)

    def StageTest4(self):

        self.CommandTest("\n")# clean buffer
        commandList = [
            "MEASure:ALL1?\n",
            "MEASure:FREQ1?\n",
            "MEASure:FREQ?\n",
            ]
        for command in commandList:
            result = self.CommandTest(command)
            if result != 0 :
                return
        return result

    def CommandTest(self,command):
        if self.WriteCommand(command) == 0 :
            if self.ReadCommand() == 0:
                answerString = self.answerBytes.decode('utf-8', 'ignore')
                pprint(command)
                pprint (answerString[0:answerString.index('\n')+1])
                return 0
        return 1

    def ReadCommand(self):
        self.readIndexMessageID = db.get_message_by_name('SCPI_INDEX_MESSAGE').frame_id
        self.readIndexMessageSignal = db.get_message_by_name('SCPI_INDEX_MESSAGE').signals[0]
        try:
            readMessage = db.get_message_by_name('SCPI_READ_MESSAGE')
        except KeyError:
            logging.info(f'Failed getting messages from data base')
            return 3

        self.ackRequestFlag = False
        localAnswerBytes = bytes()

        self.processMessageFunction = self.ProcessRequestCommand
        self.InitializeTimer()

        self.canMsgWrt= TPCANMsg()
        self.canMsgWrt.ID  = readMessage.frame_id
        self.canMsgWrt.LEN = readMessage.length
        self.canMsgWrt.MSGTYPE = PCAN_MESSAGE_STANDARD
        self.canMsgWrt.DATA[3]= 0

        for j in range(50):
            self.canMsgWrt.DATA[0]= 8*j
            stsResult = self.WriteFrameFD() if self.m_IsFD else self.WriteFrame()
            if stsResult != PCAN_ERROR_OK:
                logging.info(m_objPCANBasic.GetErrorText(stsResult, 0x09)[1])
                testStage2Result = 2
                self.StopTimer()
                return testStage2Result
            deltaTime = time.time_ns()
            if self.writeSem.acquire(True, 5):
                deltaTime = (time.time_ns() - deltaTime) / 1000000
                testStage2Result = 0
            else:
                if(self.ackRequestFlag):
                    pprint(f'ackRequestFlag {self.ackStatus}')
                    break
                else:
                    logging.info(f'Fail to read Get messages')
                    testStage2Result = 1
                    self.StopTimer()
                    return testStage2Result

            for signame,value in self.canMesageReceived.items():
                localAnswerBytes =localAnswerBytes+ (value).to_bytes(8, byteorder='little')

            if(self.ackRequestFlag):
                pprint(f'ackRequestFlag {self.ackStatus}')
                break

        self.answerBytes = localAnswerBytes
        self.StopTimer()
        return testStage2Result

    def WriteCommand(self,commandStr):
        try:
            writeMessage = db.get_message_by_name('SCPI_WRITE_MESSAGE')
        except KeyError:
            logging.info(f'Failed getting messages from data base')
            return 3

        self.processMessageFunction = self.ProcessSetpointAnswer
        self.InitializeTimer()
        toSendData = dict()

        chunks = [commandStr[i:i+8] for i in range(0, len(commandStr), 8)]
        for st in chunks:
            s_binary= bytearray(st, 'utf-8').ljust(8,b'\0')
            # b_binary = bytes(s_binary)
            value = unpack('<Q', s_binary)
            toSendData[writeMessage.signals[0].name] = value[0]
            data = writeMessage.encode(toSendData)
            self.canMsgWrt= TPCANMsg()
            self.canMsgWrt.ID  = writeMessage.frame_id
            self.canMsgWrt.LEN = writeMessage.length
            self.canMsgWrt.MSGTYPE = PCAN_MESSAGE_STANDARD
            for i in range(8 if (self.canMsgWrt.LEN > 8) else self.canMsgWrt.LEN):
                self.canMsgWrt.DATA[i]=  data[i]
            stsResult = self.WriteFrameFD() if self.m_IsFD else self.WriteFrame()
            if stsResult != PCAN_ERROR_OK:
                logging.info(m_objPCANBasic.GetErrorText(stsResult, 0x09)[1])
                testStageResult = 2
                self.StopTimer()
                return testStageResult

        deltaTime = time.time_ns()
        if self.writeSem.acquire(True, 5):
            deltaTime = (time.time_ns() - deltaTime) / 1000000
            testStageResult = 0
            signalsArray = ''
            for signame,value in toSendData.items():
                signalsArray += (f'{signame}: as {value} ' )
                logging.info(f'{deltaTime:0.0f} ms - Set Done {signalsArray}')
        else:
            logging.info(f'{toSendData} failed: {commandStr}')
            testStageResult = 1
        self.StopTimer()
        return testStageResult

    def StageTest5(self):
        logging.info(f'StageTest5')

    def WriteFrame(self):
        return m_objPCANBasic.Write(self.m_PcanHandle, self.canMsgWrt)

    def InitializeTimer(self):
        if self.uniqueTimerInitialized: return
        self.tmrRead.Start()
        self.uniqueTimerInitialized = True

    def StopTimer(self):
        self.tmrRead.Stop()
        self.uniqueTimerInitialized = False

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
                ackStatus = db.decode_message(theMsg.ID, theMsg.DATA )["ACK_Signal"]
                if ackStatus == 0:
                    self.writeSem.release(1)
                else:
                    logging.info(f'ack: Error {ackStatus}')
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
    def ProcessRequestCommand(self, *args):
        with self._lock:
            theMsg = args[0][0]
            try:
                self.ackStatus = db.decode_message(theMsg.ID, theMsg.DATA )["ACK_Signal"]
                self.ackRequestFlag = True
            except KeyError:
                pass
            try:
                self.canMesageReceived = db.decode_message(self.readIndexMessageID, theMsg.DATA )
                self.writeSem.release(1)
            except KeyError:
                return

    def PeriodicsProcessMessage(self, *args):
        with self._lock:
            theMsg = args[0][0]
            itsTimeStamp = args[0][1]
            try:
                db.decode_message(theMsg.ID, theMsg.DATA )["PM_ALL_Voltage_ACDC"]
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
logging.info(f'###*    Stage 1 end at {stageResult} {ErrorString(stageResult)}\n')

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 2 Start')
logging.info(f'###*    Reading all get messages avaiable in can database file\n')
stageResult = basicExl.StageTest2()
if stageResult != 0:
    stageResultText = ''
    logging.info(f'###*    Stage 2 end at {stageResult} {ErrorString(stageResult)}\n')
    basicExl.Destroy()
    exit()
logging.info(f'###*    Stage end at {stageResult} {ErrorString(stageResult)} \n')

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 3 Start')
stageResult = basicExl.StageTest3()
logging.info(f'###*    Stage 3 end at {stageResult} {ErrorString(stageResult)} \n')

logging.info(f'###*****************************************************************')
logging.info(f'###*    Stage 4 Start')
stageResult = basicExl.StageTest4()
logging.info(f'###*    Stage 4 end at {stageResult} {ErrorString(stageResult)} \n')

logging.info(f'###*    Test end')
logging.info(f'###*****************************************************************')