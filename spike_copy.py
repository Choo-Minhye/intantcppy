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


def ReadWaveformDataDemo():


    COMMAND_BUFFER_SIZE = 1024 # Increase if many return commands are expected
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
        uploadInProgress = commandReturn[len(expectedReturnString):]

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
    stimStepSizeuA = StimStepSizeMicroAmps



    
    # Clear TCP data output to ensure no TCP channels are enabled
    scommand.sendall(b'execute clearalldataoutputs')
    time.sleep(0.1)

    scommand.sendall(b'set a-010.tcpdataoutputenabled true')
    time.sleep(0.1)
    # scommand.sendall(b'set a-010.tcpdataoutputenabledhigh true')
    # time.sleep(0.1)
    # scommand.sendall(b'set a-010.tcpdataoutputenabledspike true')
    # time.sleep(0.1)
    # scommand.sendall(b'set a-010.tcpdataoutputenabledstim true')
    # time.sleep(0.1)
    

    framesPerBlock = 128
    waveformBytesPerFrame = 4 + (2+2)
    waveformBytesPerBlock = framesPerBlock * waveformBytesPerFrame + 4
    blocksPerRead = 100
    waveformBytes100Blocks = blocksPerRead * waveformBytesPerBlock


    
    amplifierData1 = np.zeros(framesPerBlock * blocksPerRead)
    stimData1 = np.zeros(framesPerBlock * blocksPerRead)
    amplifierTimestamps1 = np.zeros(framesPerBlock * blocksPerRead)

    amplifierData2 = np.zeros(framesPerBlock * blocksPerRead)
    stimData2 = np.zeros(framesPerBlock * blocksPerRead)
    amplifierTimestamps2 = np.zeros(framesPerBlock * blocksPerRead)
    
    amplifierData3 = np.zeros(framesPerBlock * blocksPerRead)
    stimData3 = np.zeros(framesPerBlock * blocksPerRead)
    amplifierTimestamps3 = np.zeros(framesPerBlock * blocksPerRead)
    
    amplifierTimestampsIndex = 1;

    bytesPerSpikeChunk = 14;

    


    # Send commands to configure some stimulation parameters on channel A-010, and execute UploadStimParameters for that channel
    scommand.sendall(b'set a-010.stimenabled true')
    time.sleep(0.1)
    scommand.sendall(b'set a-010.source keypressf1')
    time.sleep(0.1)
    
    print("stimable true")
    
    
    for cyclesCompleted in range(3) :
        numSpikes = 0
        if cyclesCompleted == 1 :
            thisCycleAmplifierData = amplifierData1;
            thisCycleStimData = stimData1;
            thisCycleAmplifierTimestamps = amplifierTimestamps1;
        elif cyclesCompleted == 2 :
            thisCycleAmplifierData = amplifierData2;
            thisCycleStimData = stimData2;
            thisCycleAmplifierTimestamps = amplifierTimestamps2;
        else :
            thisCycleAmplifierData = amplifierData3;
            thisCycleStimData = stimData3;
            thisCycleAmplifierTimestamps = amplifierTimestamps3;
        
    
    # Set up stim parameters
    amplitudeMicroAmps = stimStepSizeuA * cyclesCompleted
    amplitudeStr = str(amplitudeMicroAmps)
    print(amplitudeMicroAmps)
    durationMicroSeconds = 5000
    durationStr = str(durationMicroSeconds)
    print(durationMicroSeconds)

    
    scommand.sendall(b'set a-010.firstphaseamplitudemicroamps ' + amplitudeStr.encode('utf-8') )
    time.sleep(0.1)
    scommand.sendall(b'set a-010.secondphaseamplitudemicroamps ' + amplitudeStr.encode('utf-8') )
    time.sleep(0.1)
    scommand.sendall(b'set a-010.firstphasedurationmicroseconds ' + durationStr.encode('utf-8') )
    time.sleep(0.1)
    scommand.sendall(b'set a-010.secondphasedurationmicroseconds ' + durationStr.encode('utf-8') )
    time.sleep(0.1)
    scommand.sendall(b'execute uploadstimparameters a-010')
    time.sleep(0.1)
    
    print("set stim")
    # Read waveform data
    print("read waveform data")
    waveformArray = swaveform.recv(2000)
    
    # Send command to set board running
    scommand.sendall(b'set runmode run')
    time.sleep(0.05)
    scommand.sendall(b'execute manualstimtriggerpulse f1')
    time.sleep(3)

    # Send command to RHX software to stop recording
    scommand.sendall(b'set runmode stop')
    print("runmode stop")
    

    # numBlocks = int(len(waveformArray) / waveformBytesPerBlock)
    
    rawIndex = 0 # Index used to read the raw data that came in through the TCP socket
    spikeIndex = 0
    
    amplifierTimestamps = [] # List used to contain scaled timestamp values in seconds
    amplifierData = [] # List used to contain scaled amplifier data in microVolts
    
# asndmad
    for block in range(100) :
            # Each block should contain 128 frames of data - process each
            # of these one-by-one
        magicNumber, rawIndex = readUint32(waveformArray, rawIndex)
        if magicNumber != 0x2ef07a08:
            print(block)
            raise Exception('Error... magic number incorrect')
        for frame in range(framesPerBlock):
            # Expect 4 bytes to be timestamp as int32.
            rawTimestamp, rawIndex = readInt32(waveformArray, rawIndex)
            
            # Multiply by 'timestep' to convert timestamp to seconds
            amplifierTimestamps.append(rawTimestamp * timestep)
            # Expect 2 bytes of wideband data.
            rawSample, rawIndex = readUint16(waveformArray, rawIndex)
            
            # Scale this sample to convert to microVolts
            amplifierData.append(0.195 * (rawSample - 32768))

    print("plot waveform")
    plt.plot(amplifierTimestamps, amplifierData)
    plt.title('A-010 Amplifier Data')
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (uV)')
    plt.show()
    
    
    

    # Read spike data
    # spikeArray = sspikeform.recv(1024) 
    # print("read spike data")
    
    # if len(waveformArray) % waveformBytesPerBlock != 0:
    #     raise Exception('An unexpected amount of data arrived that is not an integer multiple of the expected data size per block')
    # Read spike data
    

    # scommand.sendall(b'set a-010.tcpdataoutputenabledspike true')
    # time.sleep(0.1)

    # # Read spike data
    # spikedata = sspikeform.recv(300000)
    # print("read spike data")
    
    # spikeBytesToRead = len(spikedata)
    # chunksToRead = spikeBytesToRead / bytesPerSpikeChunk
    
    # ThisSpikeStruct = SpikesToPlot1
    # spikeIndex = 0;

    # # % Process all spike chunks
    # for chunk in range(int(chunksToRead)) :

    #     # % Make sure we get the correct magic number for this chunk
    #     magicNumber, spikeIndex = readUint32(spikedata, spikeIndex);
    #     if magicNumber != 0x3ae2710f :
    #         raise Exception('Error... magic number incorrect')

    #     # % Next 5 bytes are chars of native channel name
    #     # nativeChannelName, spikeIndex = read_stringnl_noescape(spikedata, spikeIndex)

    #     # % Next 4 bytes are uint32 timestamp
    #     singleTimestamp, spikeIndex = readUint32(spikedata, spikeIndex)

    #     # % Next 1 byte is uint8 id
    #     singleID, spikeIndex = read_uint8(spikedata, spikeIndex)
        
    #     # % For every spike event, add it to ThisSpikeStruct struct
    #     if singleID != 0 :
    #         nextSpikeIndex = np.size(ThisSpikeStruct, 2) + 1

    #         # % If this is the first spike in this struct, start with an
    #         # % index of 1
    #         if numSpikes == 0 :
    #             nextSpikeIndex = 1

    #         # % Add Name, Timestamp, and ID to SpikesToPlot
    #         # ThisSpikeStruct(nextSpikeIndex).Name = nativeChannelName
    #         ThisSpikeStruct(nextSpikeIndex).Timestamp = float(singleTimestamp) * timestep
    #         ThisSpikeStruct(nextSpikeIndex).ID = singleID

    #         # % Increment numSpikes for this section of 100 datablocks
    #         numSpikes = numSpikes + 1
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

ReadWaveformDataDemo()