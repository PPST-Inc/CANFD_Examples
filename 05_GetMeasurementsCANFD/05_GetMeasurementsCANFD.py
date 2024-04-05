## Needed Imports
from PCANBasic import *

import os
import sys
import time

import cantools
import cantools.database

from importlib.metadata import version
if version('cantools') != '38.0.2':
  raise Exception("Please, install cantools 38.0.2 using the command \'pip install cantools==38.0.2\'")

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GET_MEASUREMENTS_CANFD_DBC_PATH = os.path.join(SCRIPT_DIR,'05_GetMeasurementsCANFD.dbc')

class GetMeasurementsCANFD():

    # Defines
    #region

    # Sets the PCANHandle (Hardware Channel)
    PcanHandle = PCAN_USBBUS1

    # Sets the desired connection mode (CAN = false / CAN-FD = true)
    IsFD = True

    # Sets the bitrate for normal CAN devices
    Bitrate = PCAN_BAUD_1M

    # Sets the bitrate for CAN FD devices.
    # Example - Bitrate Nom: 1Mbit/s Data: 2Mbit/s:
    #   "f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1"
    BitrateFD = b'f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1'
    #endregion

    # Members
    #region

    # Shows if DLL was found
    m_DLLFound = False

    #endregion

    def __init__(self):
        """
        Create an object starts the program
        """

        ## Shows the current parameters configuration
        self.ShowCurrentConfiguration()

        ## Checks if PCANBasic.dll is available, if not, the program terminates
        try:
            self.m_objPCANBasic = PCANBasic()
            self.m_DLLFound = True
        except:
            print("Unable to find the library: PCANBasic.dll !")
            self.getInput("Press <Enter> to quit...")
            self.m_DLLFound = False
            return

        ## Initialization of the selected channel
        if self.IsFD:
            stsResult = self.m_objPCANBasic.InitializeFD(self.PcanHandle,self.BitrateFD)
        else:
            stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle,self.Bitrate)

        if stsResult != PCAN_ERROR_OK:
            print("Can not initialize. Please check the defines in the code.")
            self.ShowStatus(stsResult)
            print("")
            self.getInput("Press <Enter> to quit...")
            return

        ## Load the CAN database
        try:
            self.database = cantools.db.load_file(GET_MEASUREMENTS_CANFD_DBC_PATH)
        except:
            print("Can not load the CAN database file.")
            self.getInput("Press <Enter> to quit...")
            return

        ## Writing messages...
        print("Successfully initialized.")
        self.getInput("Press <Enter> to start...")

        # print("")
        # sendResult = self.SendSetpointFrequency(60)
        # if sendResult[0] != PCAN_ERROR_OK or sendResult[1] != 0:
        #     print("Error sending Setpoint message.")
        #     if sendResult[0] != PCAN_ERROR_OK:
        #         self.ShowStatus(sendResult[0])
        #     elif sendResult[1] != 0:
        #         print("Error ACK value: " + str(sendResult[1]))
        #     return

        # print("")
        # sendResult = self.SendSetpointVoltage(21.34, 5.78)
        # if sendResult[0] != PCAN_ERROR_OK or sendResult[1] != 0:
        #     print("Error sending Setpoint message.")
        #     if sendResult[0] != PCAN_ERROR_OK:
        #         self.ShowStatus(sendResult[0])
        #     elif sendResult[1] != 0:
        #         print("Error ACK value: " + str(sendResult[1]))
        #     return

        # print("")
        # reqResult = self.RequestMessage('GP_ALL_Frequency_Message')
        # if reqResult != PCAN_ERROR_OK:
        #     print("Error requesting Setpoint message.")
        #     self.ShowStatus(reqResult)
        #     return

        # print("")
        # reqResult = self.RequestMessage('GP_ALL_Voltage_Message')
        # if reqResult != PCAN_ERROR_OK:
        #     print("Error requesting Setpoint message.")
        #     self.ShowStatus(reqResult)
        #     return

        print("")
        reqResult = self.RequestMessage('Get_Measurements_Message')
        if reqResult != PCAN_ERROR_OK:
            print("Error requesting Setpoint message.")
            self.ShowStatus(reqResult)
            return

        self.getInput("Press <Enter> to quit...")
        return

    def __del__(self):
        if self.m_DLLFound:
            self.m_objPCANBasic.Uninitialize(PCAN_NONEBUS)

    def ShowCurrentConfiguration(self):
        """
        Shows/prints the configured parameters
        """
        print("Parameter values used")
        print("----------------------")
        print("* PCANHandle: " + self.FormatChannelName(self.PcanHandle))
        print("* IsFD: " + str(self.IsFD))
        if not self.IsFD:
            print("* Bitrate: " + self.ConvertBitrateToString(self.Bitrate))
        else:
            print("* BitrateFD: " + self.ConvertBytesToString(self.BitrateFD))
        print("")

    def ShowStatus(self,status):
        """
        Shows formatted status

        Parameters:
            status = Will be formatted
        """
        print("=========================================================================================")
        print(self.GetFormattedError(status))
        print("=========================================================================================")

    def GetFormattedError(self, error):
        """
        Help Function used to get an error as text

        Parameters:
            error = Error code to be translated

        Returns:
            A text with the translated error
        """
        ## Gets the text using the GetErrorText API function. If the function success, the translated error is returned.
        ## If it fails, a text describing the current error is returned.
        stsReturn = self.m_objPCANBasic.GetErrorText(error,0x09)
        if stsReturn[0] != PCAN_ERROR_OK:
            return "An error occurred. Error-code's text ({0:X}h) couldn't be retrieved".format(error)
        else:
            message = str(stsReturn[1])
            return message.replace("'","",2).replace("b","",1)

    def FormatChannelName(self, handle, isFD=False):
        """
        Gets the formatted text for a PCAN-Basic channel handle

        Parameters:
            handle = PCAN-Basic Handle to format
            isFD = If the channel is FD capable

        Returns:
            The formatted text for a channel
        """
        handleValue = handle.value
        if handleValue < 0x100:
            devDevice = TPCANDevice(handleValue >> 4)
            byChannel = handleValue & 0xF
        else:
            devDevice = TPCANDevice(handleValue >> 8)
            byChannel = handleValue & 0xFF

        if isFD:
           return ('%s:FD %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handleValue))
        else:
           return ('%s %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handleValue))

    def GetDeviceName(self, handle):
        """
        Gets the name of a PCAN device

        Parameters:
            handle = PCAN-Basic Handle for getting the name

        Returns:
            The name of the handle
        """
        switcher = {
            PCAN_NONEBUS.value: "PCAN_NONEBUS",
            PCAN_PEAKCAN.value: "PCAN_PEAKCAN",
            PCAN_DNG.value: "PCAN_DNG",
            PCAN_PCI.value: "PCAN_PCI",
            PCAN_USB.value: "PCAN_USB",
            PCAN_VIRTUAL.value: "PCAN_VIRTUAL",
            PCAN_LAN.value: "PCAN_LAN"
        }

        return switcher.get(handle,"UNKNOWN")

    def ConvertBitrateToString(self, bitrate):
        """
        Convert bitrate c_short value to readable string

        Parameters:
            bitrate = Bitrate to be converted

        Returns:
            A text with the converted bitrate
        """
        m_BAUDRATES = {PCAN_BAUD_1M.value:'1 MBit/sec', PCAN_BAUD_800K.value:'800 kBit/sec',
                       PCAN_BAUD_500K.value:'500 kBit/sec', PCAN_BAUD_250K.value:'250 kBit/sec',
                       PCAN_BAUD_125K.value:'125 kBit/sec', PCAN_BAUD_100K.value:'100 kBit/sec',
                       PCAN_BAUD_95K.value:'95,238 kBit/sec', PCAN_BAUD_83K.value:'83,333 kBit/sec',
                       PCAN_BAUD_50K.value:'50 kBit/sec', PCAN_BAUD_47K.value:'47,619 kBit/sec',
                       PCAN_BAUD_33K.value:'33,333 kBit/sec', PCAN_BAUD_20K.value:'20 kBit/sec',
                       PCAN_BAUD_10K.value:'10 kBit/sec', PCAN_BAUD_5K.value:'5 kBit/sec'}

        return m_BAUDRATES[bitrate.value]

    def ConvertBytesToString(self, bytes):
        """
        Convert bytes value to string

        Parameters:
            bytes = Bytes to be converted

        Returns:
            Converted bytes value as string
        """
        return str(bytes).replace("'","",2).replace("b","",1)

    def getInput(self, msg="Press <Enter> to continue...", default=""):
        res = default
        if sys.version_info[0] >= 3:
            res = input(msg + " ")
        else:
            res = raw_input(msg + " ")
        if len(res) == 0:
            res = default
        return res

    def GetLengthFromDLC(dlc):
        """
        Gets the data length of a CAN message

        Parameters:
            dlc = Data length code of a CAN message

        Returns:
            Data length as integer represented by the given DLC code
        """
        if dlc == 9:
            return 12
        elif dlc == 10:
            return 16
        elif dlc == 11:
            return 20
        elif dlc == 12:
            return 24
        elif dlc == 13:
            return 32
        elif dlc == 14:
            return 48
        elif dlc == 15:
            return 64

        return dlc

    def GetDLCFromLength(self, length):
        """
        Gets the Data length code form a Data Length of a CAN message

        Parameters:
            length = Data length of a CAN message

        Returns:
            DLC code as integer corresponding for a Data length
        """
        if length <= 8:
            return length
        if length <= 12:
            return 9
        if length <= 16:
            return 10
        if length <= 20:
            return 11
        if length <= 24:
            return 12
        if length <= 32:
            return 13
        if length <= 48:
            return 14
        if length <= 64:
            return 15

    def SendSetpointFrequency(self, freq):
        """Send a message to set the Setpoint "Frequency" with value `value`

        After sent the message we wait for the 'Confirmation_Message'

        Returns:
          A tuple of TPCANStatus error code and ACK_Signal value
        """

        try:
            # Get from the database the message 'SP_ALL_Frequency_Message' to send
            # the signal 'SP_ALL_Voltage_AC'
            message = self.database.get_message_by_name('SP_ALL_Frequency_Message')
        except:
            print("Error trying to get \'SP_ALL_Frequency_Message\'")
            return

        try:
            data = message.encode({'SP_ALL_Frequency': freq})
        except:
            print("Error encoding message \'SP_ALL_Frequency\'")
            return

        print("Send message:")
        print("  " + message.name)
        print("  signal: " + message.signals[0].name + ": " + str(freq))

        msgCanMessage = TPCANMsg()
        msgCanMessage.ID = message.frame_id
        msgCanMessage.LEN = message.length
        msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value
        for i in range(len(data)):
            msgCanMessage.DATA[i] = data[i]

        ack_status = -1
        # Send a message to set the Frequency setpoint
        stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
        ## Checks if the message was sent
        if (stsResult != PCAN_ERROR_OK):
            return stsResult, ack_status

        return self.ReadAckMessage()

    def SendSetpointVoltage(self, volt_ac, volt_dc):
        """Send a message to set the Setpoint "Voltage AC" with value `volt_ac`
        and the Setpoint "Voltage DC" with value `volt_dc`

        After sent the message we wait for the 'Confirmation_Message'

        Returns:
          A tuple of TPCANStatus error code and ACK_Signal value
        """

        try:
            # Get from the database the message 'SP_ALL_Voltage_AC_Message' to send
            # the signal 'SP_ALL_Voltage_AC'
            message = self.database.get_message_by_name('SP_ALL_Voltage_Message')
        except:
            print("Error trying to get \'SP_ALL_Voltage_Message\'")
            return

        try:
            data = message.encode({'SP_ALL_Voltage_AC': volt_ac,
                                   'SP_ALL_Voltage_DC': volt_dc})
        except:
            print("Error encoding message \'SP_ALL_Voltage_AC_Message\'")
            return

        print("Send message:")
        print("  " + message.name)
        print("  signal: " + message.signals[0].name + ": " + str(volt_ac))
        print("  signal: " + message.signals[1].name + ": " + str(volt_dc))

        msgCanMessage = TPCANMsg()
        msgCanMessage.ID = message.frame_id
        msgCanMessage.LEN = message.length
        msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value
        for i in range(len(data)):
            msgCanMessage.DATA[i] = data[i]

        ack_status = -1
        # Send a message to set the Voltage AC setpoint
        stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
        ## Checks if the message was sent
        if (stsResult != PCAN_ERROR_OK):
            return stsResult, ack_status

        return self.ReadAckMessage()

    def RequestMessage(self, name):
        """Request a message name `name` and read the response

        To request a message we send an empty CAN frame with the with the desired ID
        and wait for the response.

        Returns:
          A TPCANStatus error code
        """
        try:
            message = self.database.get_message_by_name(name)
        except:
            print(f"Error trying to get \"{name}\".")
            return

        print(f"Request message \"{message.name}\"")

        if self.IsFD:
            msgCanMessageFD = TPCANMsgFD()
            msgCanMessageFD.ID = message.frame_id
            msgCanMessageFD.DLC = self.GetDLCFromLength(message.length)
            msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_FD.value | PCAN_MESSAGE_BRS.value
            for i in range(message.length):
                msgCanMessageFD.DATA[i] = 0
            stsResult = self.m_objPCANBasic.WriteFD(self.PcanHandle, msgCanMessageFD)
        else:
            msgCanMessageFD = TPCANMsgFD()
            msgCanMessage = TPCANMsg()
            msgCanMessage.ID = message.frame_id
            msgCanMessage.LEN = message.length
            msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value
            for i in range(message.length):
                msgCanMessage.DATA[i] = 0
            # Send a message to request
            stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)

        ## Checks if the message was sent
        if (stsResult != PCAN_ERROR_OK):
            return stsResult

        # Wait to read the reply of the request message
        response_received = False
        tries = 100
        while tries > 0:
            tries -= 1
            if self.IsFD:
                result = self.m_objPCANBasic.ReadFD(self.PcanHandle)
            else:
                result = self.m_objPCANBasic.Read(self.PcanHandle)

            stsResult = result[0]
            if stsResult != PCAN_ERROR_OK and stsResult != PCAN_ERROR_QRCVEMPTY:
                break

            if (stsResult & PCAN_ERROR_QRCVEMPTY):
                time.sleep(0.1)
                continue

            if stsResult == PCAN_ERROR_OK:
                msgRead = result[1]
                if msgRead.ID != message.frame_id:
                    continue

                response_received = True
                response_decoded = message.decode(msgRead.DATA)
                break

        if not response_received:
            print("Response not received.")
            return stsResult

        print("Response message:")
        print(f"  {message.name}")
        for signal in response_decoded:
            print(f"  signal: {signal}: {response_decoded[signal]}")

        return stsResult

    def ReadAckMessage(self):
        """Try to read the 'Confirmation_Message' in order the get the ACK status

        Read the queue up to 100 tries waiting for the message 'Confirmation_Message'
        if is not received return `ack_status = -1`

        Returns:
          A tuple of TPCANStatus error code and ACK_Signal value
        """
        message_confirmation = self.database.get_message_by_name('Confirmation_Message')

        stsResult = PCAN_ERROR_OK
        ack_status = -1

        tries = 100
        while tries > 0:
            tries -= 1
            result = self.m_objPCANBasic.Read(self.PcanHandle)
            stsResult = result[0]

            if stsResult != PCAN_ERROR_OK and stsResult != PCAN_ERROR_QRCVEMPTY:
                break

            if (stsResult & PCAN_ERROR_QRCVEMPTY):
                time.sleep(0.1)
                continue

            if stsResult == PCAN_ERROR_OK:
                msgRead = result[1]
                if msgRead.ID != message_confirmation.frame_id:
                    continue

                decoded = message_confirmation.decode(msgRead.DATA)
                ack_status = decoded['ACK_Signal']
                break

        return stsResult, ack_status

## Starts the program
GetMeasurementsCANFD()
