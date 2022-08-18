from operator import eq
from pickletools import read_stringnl_noescape, read_uint8
import string
import time, socket
import matplotlib.pyplot as plt
import numpy as np



def readUint32(array, arrayIndex):
    variableBytes = array[arrayIndex : arrayIndex + 4]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 4
    return variable, arrayIndex

def readInt32(array, arrayIndex):
    variableBytes = array[arrayIndex : arrayIndex + 4]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=True)
    arrayIndex = arrayIndex + 4
    return variable, arrayIndex

def readUint16(array, arrayIndex):
    variableBytes = array[arrayIndex : arrayIndex + 2]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 2
    return variable, arrayIndex

def readUint8(array, arrayIndex):
    variableBytes = array[arrayIndex : arrayIndex + 1]
    variable = int.from_bytes(variableBytes, byteorder='little', signed=False)
    arrayIndex = arrayIndex + 1
    return variable, arrayIndex

def read5char(array, arrayIndex):
    variableBytes = array[arrayIndex : arrayIndex + 5]
    variable = variableBytes.decode('utf-8')
    arrayIndex = arrayIndex + 5
    return variable, arrayIndex


def ReadWaveformDataDemo():

    # Declare buffer size for reading from TCP command socket
    # This is the maximum number of bytes expected for 1 read. 1024 is plenty for a single text command
    COMMAND_BUFFER_SIZE = 1024 # Increase if many return commands are expected

    # Declare buffer size for reading from TCP waveform socket.
    # This is the maximum number of bytes expected for 1 read

    # There will be some TCP lag in both starting and stopping acquisition, so the exact number of data blocks may vary slightly.
    # At 30 kHz with 1 channel, 1 second of wideband waveform data is 181,420 byte. See 'Calculations for accurate parsing' for more details
    # To allow for some TCP lag in stopping acquisition resulting in slightly more than 1 second of data, 200000 should be a safe buffer size
    WAVEFORM_BUFFER_SIZE = 200000 # Increase if channels, filter bands, or acquisition time increase

    # Connect to TCP command server - default home IP address at port 5000
    print('Connecting to TCP command server...')
    scommand = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    scommand.connect(('127.0.0.1', 5000))

    # Connect to TCP waveform server - default home IP address at port 5001
    print('Connecting to TCP waveform server...')
    swaveform = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    swaveform.connect(('127.0.0.1', 5001))

    # Connect to TCP spikeData server - default home IP address at port 5002
    print('Connecting to TCP spike server...')
    sspikeform = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sspikeform.connect(('127.0.0.1', 5002))






    # Query if the controller currently has an upload in progress
    scommand.sendall(b'get uploadinprogress');
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    expectedReturnString = 'Return: UploadInProgress ';
    if commandReturn.find(expectedReturnString) == -1: # Look for "Return: SampleRateHertz N" where N is the sample rate
        raise Exception('Unable to get sample rate from server')
    else:
        getuploadInProgress = commandReturn[len(expectedReturnString):]

    # Query sample rate from RHX software
    scommand.sendall(b'get sampleratehertz')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    expectedReturnString = "Return: SampleRateHertz "
    if commandReturn.find(expectedReturnString) == -1: # Look for "Return: SampleRateHertz N" where N is the sample rate
        raise Exception('Unable to get sample rate from server')
    else:
        sampleRate = float(commandReturn[len(expectedReturnString):])

    # Query stimstepsizemicroamps from RHX software
    scommand.sendall(b'get stimstepsizemicroamps')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    expectedReturnString = "Return: StimStepSizeMicroAmps "
    if commandReturn.find(expectedReturnString) == -1:
        raise Exception('Unable to get StimStepSizeMicroAmps from server')
    else:
        StimStepSizeMicroAmps = float(commandReturn[len(expectedReturnString):])


    # Query controller type from RHX software - throw an error and exit if controller type is not Stim
    scommand.sendall(b'get type')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    isStim = commandReturn == "Return: Type ControllerStimRecordUSB2"
    if not isStim:
        raise Exception('This example script should only be used with a Stimulation/Recording Controller')


    # Query runmode from RHX software
    scommand.sendall(b'get runmode')
    commandReturn = str(scommand.recv(COMMAND_BUFFER_SIZE), "utf-8")
    isStopped = commandReturn == "Return: RunMode Stop"

    # If controller is running, stop it
    if not isStopped:
        scommand.sendall(b'set runmode stop')
        time.sleep(0.1) # Allow time for RHX software to accept this command before the next one comes




    # Calculate timestep from sample rate
    timestep = 1 / sampleRate

    # Clear TCP data output to ensure no TCP channels are enabled
    scommand.sendall(b'execute clearalldataoutputs')
    time.sleep(0.1)

    # Send TCP commands to set up TCP Data Output Enabled for wide
    # band of channel A-010
    scommand.sendall(b'set a-010.tcpdataoutputenabledhigh true')
    time.sleep(0.1)
    scommand.sendall(b'set a-010.tcpdataoutputenabledspike true')
    time.sleep(0.1)

    
    framesPerBlock = 128
    waveformBytesPerFrame = 4 + 2 + 2
    waveformBytesPerBlock = framesPerBlock * waveformBytesPerFrame + 4
    blocksPerRead = 100
    waveformBytes100Blocks = blocksPerRead * waveformBytesPerBlock



    # Run controller for 1 second
    scommand.sendall(b'set runmode run')
    time.sleep(1)
    scommand.sendall(b'set runmode stop')

    # Read waveform data
    rawData = swaveform.recv(102800)
    spikeArray = sspikeform.recv(1024)
    
    print(len(rawData))
    # if len(rawData) % waveformBytesPerBlock != 0:
    #     raise Exception('An unexpected amount of data arrived that is not an integer multiple of the expected data size per block')
    # numBlocks = int(len(rawData) / waveformBytesPerBlock)

    rawIndex = 0 # Index used to read the raw data that came in through the TCP socket
    spikeIndex = 0
    amplifierTimestamps = [] # List used to contain scaled timestamp values in seconds
    amplifierData = [] # List used to contain scaled amplifier data in microVolts
    for block in range(100):
        # Expect 4 bytes to be TCP Magic Number as uint32.
        # If not what's expected, raise an exception.
        magicNumber, rawIndex = readUint32(rawData, rawIndex)
        if magicNumber != 0x2ef07a08:
            raise Exception('Error... magic number incorrect')
        # Each block should contain 128 frames of data - process each
        # of these one-by-one
        for frame in range(framesPerBlock):
            # Expect 4 bytes to be timestamp as int32.
            rawTimestamp, rawIndex = readInt32(rawData, rawIndex)
            
            # Multiply by 'timestep' to convert timestamp to seconds
            amplifierTimestamps.append(rawTimestamp * timestep)
            # Expect 2 bytes of wideband data.
            rawSample, rawIndex = readUint16(rawData, rawIndex)
            
            # Scale this sample to convert to microVolts
            amplifierData.append(0.195 * (rawSample - 32768))

    
    # If using matplotlib to plot is not desired, the following plot lines can be removed.
    # Data is still accessible at this point in the amplifierTimestamps and amplifierData
    plt.plot(amplifierTimestamps, amplifierData)
    plt.title('A-010 Amplifier Data')
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (uV)')
    
    # % Each spike chunk contains 4 bytes for magic number, 5 bytes for native
    # % channel name, 4 bytes for timestamp, and 1 byte for id. Total: 14 bytes
    bytesPerSpikeChunk = 14;
    spikeBytesToRead = len(spikeArray)
    print(spikeBytesToRead)
    chunksToRead = int(spikeBytesToRead / bytesPerSpikeChunk);
    print(chunksToRead)
    if chunksToRead > 0 :
        for chunk in range(chunksToRead) :
            magicNumber, spikeIndex = readUint32(spikeArray, spikeIndex)
            if magicNumber != 0x3ae2710f:
                raise Exception('Error... magic number incorrect')
                print(chunk)
                
            nativeChannelName, spikeIndex = read5char(spikeArray, spikeIndex)
            singleTimestamp, spikeIndex = readUint32(spikeArray, spikeIndex)
            singleID, spikeIndex = readUint8(spikeArray, spikeIndex)
            print(nativeChannelName)
            print(singleTimestamp)
            print(singleID)
  


          
                
            












ReadWaveformDataDemo()

plt.show()
