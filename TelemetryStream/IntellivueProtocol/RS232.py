"""
Requires pyserial

On OSX, dl the Mac 1.6 driver at http://plugable.com/drivers/prolific/
(https://s3.amazonaws.com/plugable/bin/PL2303_MacOSX-Driver_1.6.0_20151012.zip)

"""

import serial
import serial.tools.list_ports
import struct
import logging
import os.path
import itertools

class RS232(object):
    """
    Methods to engage in RS232 connection with monitor
    """

    def __init__(self, specifiedPort):

        # Check to see if the named port exists
        if specifiedPort not in itertools.chain.from_iterable(serial.tools.list_ports.comports()):
        # can't use os.path.exists on Windows!
        # if not os.path.exists(specifiedPort):
            logging.warn('Device at {0} does not exist!'.format(specifiedPort))
            logging.info('Available ports: {0}'.format(serial.tools.list_ports.comports()))
            self.socket = None
            return

        logging.debug('Trying to open serial connection to device at {0}'.format(specifiedPort))

        self.socket = serial.Serial(port=specifiedPort,
                                    baudrate=115200, bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE, timeout=2, writeTimeout=2)
        if not self.socket:
            logging.warn("Failed to open serial connection")
            raise IOError

        # Create CRC16 Table
        self.CRCTable = self.getCRCTable()
        logging.debug('Serial connection opened')

    # Returns value from uint16 binary
    def get16(self, data):
        return struct.unpack('>H', data)[0]

    # Returns uint16 binary from value
    def set16(self, data):
        return bytearray(struct.pack('>H', data))

    # create CRC16 table
    def getCRCTable(self):
        """
        generates table used in CRC16 calculations (as defined in manual)

        returns: table - table of 16 bit numbers
        """

        table = list()

        for i in range(0, 256):
            x = i
            for j in range(0, 8):
                if (x & 1):

                    x = (x >> 1) ^ 0x8408
                else:
                    x = x >> 1

            table.append(x & 0xFFFF)

        return table

    # get CRC16
    def getCRC16(self, message, table):
        """
        generates CRC16 as defined by manual

        returns: fcs - 16 bit crc code
        """
        length = len(message)
        fcs = 0xFFFF

        if type(message) != bytearray:
            message = bytearray(message)

        # logging.debug("CRC16->Message as bytes {0}:".format(message))

        for i in range(0, length):
            # fcs = (fcs >> 8) ^ table[(fcs ^ message[i]) & 0xFF]
            fcs = (fcs >> 8) ^ table[(fcs ^ message[i]) & 0xFF]

        # One's Complement
        fcs = ~fcs & 0xFFFF

        # Byte Swap
        fcs = struct.pack('<H', fcs)

        return fcs

    # write transparency check
    def writeTransparencyCheck(self, message):
        """
        performs transparency check on written messages as defined by manual

        returns: message - bytes to be sent to monitor
        """
        # iterate through each byte for start, stop, esc bytes
        for i in range(1, len(message)-1):
            if message[i] == 0xC0 or message[i] == 0xC1 or message[i] == 0x7D:
                replace_byte = message[i] ^ 0x20
                message[i] = 0x7D
                message.insert(i+1, replace_byte)

        return message

    # read transparency check
    def readTransparencyCheck(self, message):
        """
        performs transparency check while reading as defined by manual

        returns: message - bytes ready to be deciphered
        """

        if type(message) != bytearray:
            message = bytearray(message)

        # store (index, bin) in these lists
        indices = []

        # iterate through message and store indices of 0xc1,0xc0,0x7d
        for i in range(0, len(message)):
            if message[i] == 0x7D:
                if message[i+1] == 0xC0 ^ 0x20:
                    indices.append((i, 192))  # 0xc0 = 192
                elif message[i+1] == 0xC1 ^ 0x20:
                    indices.append((i, 193))  # 0xc1 = 193
                elif message[i+1] == 0x7D ^ 0x20:
                    indices.append((i, 125))  # 0x7d = 125

        # Sort indices
        sortedIndices = sorted(indices, reverse=True)

        # Iterate through list and change message
        for value in sortedIndices:
            if value[1] == 192:
                message[value[0]:value[0]+2] = b'\xC0'
            elif value[1] == 193:
                message[value[0]:value[0]+2] = b'\xC1'
            elif value[1] == 125:
                message[value[0]:value[0]+2] = b'\x7D'

        return bytes(message)

    # Adds header, fcs, transparency check to messages
    def frameCheckWrite(self, message):
        """
        Takes message and adds beginning of frame, header, fcs, end of frame,
        as well as performs transparency check

        Frame = |BOF|Hdr|Hdr_len|message|FCS|EOF

        returns: finalMessage - bytes to send to monitor
        """

        BOF = bytearray(b'\xC0')

        Hdr = bytearray(b'\x11\x01')

        Hdr_len = self.set16(len(message))

        FCS = bytearray(self.getCRC16(Hdr + Hdr_len + message, self.CRCTable))

        EOF = bytearray(b'\xC1')

        finalMessage = self.writeTransparencyCheck(BOF + Hdr + Hdr_len +
                                                   message + FCS + EOF)
        return finalMessage

    # Reads in and interprets framing of messages
    def frameCheckRead(self, message):
        """
        Reads in messages and strips BOF, Hdr, FCS, EOF,
        so it can be read by IntellivueDecoder.readData()

        Also checks FCS to ensure proper format

        returns: decodedMessage - dict of deciphered message
        """

        finalMessage = None
        # Check for start bit and correct protocol id
        if message[0:3] == b'\xC0\x11\x01':

            # Transparency Check (not including start, stop)
            message = self.readTransparencyCheck(message[1:-1])

            # Length, CRC calculations
            length = self.get16(message[2:4])
            givenCRC = message[4+length:6+length]
            validatedCRC = self.getCRC16(message[:4+length], self.CRCTable)

            # Check that CRC's match up, otherwise ignore message
            if givenCRC == validatedCRC:
                finalMessage = message[4:4+length]
            # If they are not the same, output CRC mismatch
            else:
                finalMessage = b''

        else:
            logging.error('RS232: Incorrect framing...')

        return finalMessage

    # Recieves each byte and outputs final message
    def receive(self):
        """
        Takes in input from serial port and strings into messages
        based on start bit (0xC0) and stop bit (0xC1)

        will stop after reading in one message

        returns: message - ready to be interpreted by IntellivueDecoder()
        """

        if not self.socket:
            logging.warn('Trying to receive without a socket')
            return

        # initialize message
        message = bytearray()

        # initialize boolean
        messageNotDone = True

        # read in current byte
        currentByte = self.socket.read(1)

        # Loop to read in entire message
        if currentByte == b'\xC0':
            message = message + currentByte

            while(messageNotDone):
                messageByte = self.socket.read(1)

                if messageByte is None:
                    # Bail out! The message is incomplete.
                    logging.warn('Incomplete message received!')
                    return None
                elif messageByte != b'\xC1':
                    message = message + messageByte
                else:
                    message = message + messageByte
                    messageNotDone = False

            # Frame check message
            finalMessage = self.frameCheckRead(bytes(message))

        # If not at start bit return nothing
        else:
            finalMessage = b''

        return finalMessage

    # Sends final messages to monitor
    def send(self, message):
        """
        Sends the finalized message to the monitor
        """
        if not self.socket:
            logging.warn('Trying to write without a socket')
            return

        self.socket.write(self.frameCheckWrite(message))

    def __del__(self):
        print('Tearing down socket.')
        self.close()

    # closes port
    def close(self):
        if not self.socket:
            print('Trying to close without a socket')
            return

        # Maybe help with hangs?
        self.socket.flush()
        self.socket.close()
        print('Serial Port Closed.')


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    ser = RS232('/dev/cu.usbserial')

