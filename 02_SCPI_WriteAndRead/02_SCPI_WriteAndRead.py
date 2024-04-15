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
SCPI_WRITEANDREAD_DBC_PATH = os.path.join(SCRIPT_DIR,'02_SCPI_WriteAndRead.dbc')

MAX_RESPONSE_SIZE = 65535

class SCPI_WriteAndRead():

    # Defines
    #region

    # Sets the PCANHandle (Hardware Channel)
    PcanHandle = PCAN_USBBUS1

    # Sets the desired connection mode (CAN = false / CAN-FD = true)
    IsFD = False

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
            self.database = cantools.db.load_file(SCPI_WRITEANDREAD_DBC_PATH)
        except:
            print("Can not load the CAN database file.")
            self.getInput("Press <Enter> to quit...")
            return

        ## Writing messages...
        print("Successfully initialized.")
        self.getInput("Press <Enter> to start...")

        clrResult = self.SCPIClear()
        if clrResult[0] != PCAN_ERROR_OK or clrResult[1] != 0:
            print("Error sending SCPI Clear.")
            if clrResult[0] != PCAN_ERROR_OK:
                self.ShowStatus(clrResult[0])
            return

        writeResult = self.WriteSCPICommand("SYSTem:COMMunicate:LAN:VISA?")
        # Check transmission result and ACK receptions
        if writeResult[0] != PCAN_ERROR_OK or writeResult[1] != 0:
            print("Error sending SCPI command.")
            if writeResult[0] != PCAN_ERROR_OK:
                self.ShowStatus(writeResult[0])
            return

        readResult = self.ReadSCPIResponse()
        if readResult[0] != PCAN_ERROR_OK or readResult[1] != 0:
            print("Error reading response.")
            if readResult[0] != PCAN_ERROR_OK:
                self.ShowStatus(readResult[0])
            return
        print(f"Response read: \"{readResult[2]}\"")

        # Note that send a SCPI Write command doesn't produce a response
        # to read. We can send the SCPI "*STB?" to check if the last SCPI
        # command produce and error.
        writeResult = self.WriteSCPICommand("SOURce:VOLTage:AC 10")
        if writeResult[0] != PCAN_ERROR_OK or writeResult[1] != 0:
            print("Error sending SCPI command.")
            if writeResult[0] != PCAN_ERROR_OK:
                self.ShowStatus(writeResult[0])
            return

        writeResult = self.WriteSCPICommand("*STB?")
        if writeResult[0] != PCAN_ERROR_OK or writeResult[1] != 0:
            print("Error sending SCPI command.")
            if writeResult[0] != PCAN_ERROR_OK:
                self.ShowStatus(writeResult[0])
            return

        readResult = self.ReadSCPIResponse()
        if readResult[0] != PCAN_ERROR_OK or readResult[1] != 0:
            print("Error reading response.")
            if readResult[0] != PCAN_ERROR_OK:
                self.ShowStatus(readResult[0])
            return
        print(f"Response read: \"{readResult[2]}\"")

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

    def SCPIClear(self):
        """Send a message to clear the buffers 'SCPI_Clear_Message'

        Returns:
          A tuple of TPCANStatus error code and ACK_Signal value
        """
        message_clear = self.database.get_message_by_name('SCPI_Clear_Message')

        msgCanMessage = TPCANMsg()
        msgCanMessage.ID = message_clear.frame_id
        msgCanMessage.LEN = message_clear.length
        msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value
        for i in range(message_clear.length):
            msgCanMessage.DATA[i] = 0

        ack_status = 0

        stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
        # Checks if the message was sent
        if (stsResult != PCAN_ERROR_OK):
            return stsResult,ack_status

        stsResult = self.ReadAckMessage()
        if stsResult[0] == PCAN_ERROR_OK:
            if stsResult[1] != 0 or stsResult[2] != message_clear.frame_id:
                print("Error ACK response invalid")
                return stsResult[0], stsResult[1]

        return stsResult[0], stsResult[1]

    def WriteSCPICommand(self, scpi_cmd):
        """Write a SCPI command using the Message 'SCPI_Write_Message'

        To send the SCPI command this function convert the string in a list of
        bytearray, each item with size of the Signal 'SCPI_Write'. Sends all
        item in CAN frames and then wait for the reception of 'Confirmation_Message'

        Returns:
          A tuple of TPCANStatus error code and ACK_Signal value
        """
        print(f"Write SCPI: \"{scpi_cmd}\"")

        if not scpi_cmd.endswith("\n"):
            scpi_cmd += "\n"

        message_write = self.database.get_message_by_name('SCPI_Write_Message')
        signal = message_write.get_signal_by_name('SCPI_Write')
        length = signal.length // 8

        bytes_list = self.StringToBytesList(scpi_cmd, length)

        msgCanMessage = TPCANMsg()
        msgCanMessage.ID = message_write.frame_id
        msgCanMessage.LEN = message_write.length
        msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value

        ack_status = 0

        for item in bytes_list:
            # The bytes order for this Signal is Big-endian
            for i in range(length):
                msgCanMessage.DATA[i] = item[i]

            stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
            # Checks if the message was sent
            if (stsResult != PCAN_ERROR_OK):
                return stsResult,ack_status

            stsResult = self.ReadAckMessage()
            if stsResult[0] == PCAN_ERROR_OK:
                if stsResult[1] != 0 or stsResult[2] != message_write.frame_id:
                    print("Error ACK response invalid")
                    return stsResult[0], stsResult[1]

        # Wait for ACK frame from the device
        return stsResult[0], stsResult[1]

    def StringToBytesList(self, string, size):
        """Convert a String in a list of bytes of size `size`

        If `string` is empty or `size` is less or equal ``0`` return an empty list

        Returns:
          A list of bytearray
        """
        if len(string) == 0 or size <= 0:
            return list()

        num_blocks = len(string) // size
        if len(string) % size > 0:
            num_blocks += 1

        bytes_list = list()
        for n in range(num_blocks):
            idxFrom = n * size
            idxTo = n * size + size

            sub_string = string[idxFrom:idxTo]
            bytes_array = bytearray(sub_string.encode())

            # Fill with '0' if the length of sub_string is less than size
            while len(bytes_array) < size:
                bytes_array.append(0)

            bytes_list.append(bytes(bytes_array))

        return bytes_list

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
        ack_can_id = 0

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
                ack_can_id = decoded['ACK_CAN_ID']
                break

        return stsResult, ack_status, ack_can_id

    def ReadSCPIResponse(self):
        """Read the SCPI command response using the Message 'SCPI_Read_Response_Message'

        To Read the SCPI command response we have to request a series of chunk
        sending the message 'SCPI_Read_Request_Message' with a index value on the Signal
        'SCPI_Read_Request', and read the response chunk for each request sent.

        If the response length is 20 characters and response chunk is 8 bytes
        we need to request three messages. Starting from the first 8 characters
        sending 'index = 0', read the response chunk sent in message 'SCPI_Read_Response_Message'
        and then request the next 8 characters by sending 'index = 8', and so on
        until we get the end of the response.

        Returns:
          A tuple of TPCANStatus error code, ACK_Signal value and a String
        """
        message_scpi_index = self.database.get_message_by_name('SCPI_Read_Response_Message')
        signal_scpi_index = message_scpi_index.get_signal_by_name('SCPI_Read_Response')
        length = signal_scpi_index.length // 8

        message_scpi_read = self.database.get_message_by_name('SCPI_Read_Request_Message')

        msgCanMessage = TPCANMsg()
        msgCanMessage.ID = message_scpi_read.frame_id
        msgCanMessage.LEN = message_scpi_read.length
        msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value

        scpi_response_string = ""
        ack_value = 0

        termination_found = False
        index_to_read = 0

        while not termination_found and index_to_read < MAX_RESPONSE_SIZE:

            data = message_scpi_read.encode({'SCPI_Read_Request': index_to_read})
            for i in range(len(data)):
                msgCanMessage.DATA[i] = data[i]

            # Sends a CAN message with the "index" of read buffer to request the response chunk
            stsResult = self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
            ## Checks if the message was sent
            if (stsResult != PCAN_ERROR_OK):
                return stsResult,ack_value,scpi_response_string

            # Read the response chunk
            stsResult, ack_value, read_string = self.ReadSCPIMessage()
            if stsResult != PCAN_ERROR_OK or ack_value != 0:
                break

            # Append the read string to the response
            scpi_response_string += read_string

            # Request data until find the end of the response, looking for "\r\n" or NULL value
            if (scpi_response_string.find("\r\n") >= 0
                    or scpi_response_string.find("\x00") >= 0):
                scpi_response_string = scpi_response_string.rstrip("\r\n\x00")
                termination_found = True

            index_to_read += length

        return stsResult,ack_value,scpi_response_string

    def ReadSCPIMessage(self):
        """Read a chunk response from the Message 'SCPI_Read_Response_Message'

        Expect to read the message 'SCPI_Read_Response_Message' with the response chunk,
        if an error occurs requesting the response we will receive a message of
        'Confirmation_Message' with 'ACK_Signal' values distinct of '0'

        Returns:
          A tuple of TPCANStatus error code, ACK_Signal value and a String
        """
        message_scpi_index = self.database.get_message_by_name('SCPI_Read_Response_Message')
        message_confirmation = self.database.get_message_by_name('Confirmation_Message')

        read_string = ""
        ack_value = 0

        tries = 100
        while tries > 0:
            tries -= 1
            result = self.m_objPCANBasic.Read(self.PcanHandle)
            stsResult = result[0]

            # If an error occur, we get out from the while loop.
            if stsResult != PCAN_ERROR_OK and stsResult != PCAN_ERROR_QRCVEMPTY:
                break

            # If the queue is empty wait 100ms and read again.
            if (stsResult & PCAN_ERROR_QRCVEMPTY):
                time.sleep(0.1)
                continue

            if stsResult == PCAN_ERROR_OK:
                msgRead = result[1]
                if msgRead.ID == message_scpi_index.frame_id:
                    # Decode the bytes as String and exit
                    read_string = str(msgRead.DATA, encoding='utf-8')
                    break
                elif msgRead.ID == message_confirmation.frame_id:
                    decoded_message = message_confirmation.decode(msgRead.DATA)
                    ack_value = decoded_message['ACK_Signal']
                    print(decoded_message)
                    if ack_value != 0:
                        break

        return stsResult, ack_value, read_string

## Starts the program
SCPI_WriteAndRead()
