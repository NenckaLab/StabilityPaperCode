#! /usr/bin/env python

#Load libraries for working with command line arguments
import os
import glob
#Load libraries for working with DICOM images
import dicom
import argparse
import subprocess

#Load the dataset
#myFile = "/rcc/stor1/users/bswearingen/DWI_PreProcessing.log"
myFolder = 'thisProject'
#myFile = "temp.log"
args = []
logName = 'notFound'

#OFI
#clean up checking of scans to make sure we use the newest one if there are duplicates
#    Somewhat framed in.
#get rid of the absolute path names

#functions
def parseArgs():
    #parses all of the passed in arguments
    global args
    parser = argparse.ArgumentParser(description='This is a demo script by nixCraft.')
    parser.add_argument('-D', '--directory', help='Scan directory to search for scan description. Subdir should be #/DICOM/files', default='.')
    parser.add_argument('-f', '--InfileDescription', help='Scan description to flag for use as a/p', action='append', default = [])
    parser.add_argument('-up', '--usrPath', help='Folder path for input configuration files.', default='.')
    parser.add_argument('-ac', '--AcParamFile', help='Acquisition parameters file to use. File should be located in SupportDirectory', default='acqparams.txt')
    args = parser.parse_args()
    return


def getNewScanNumber(base, scanDir):
    #new series number will be *100
    newNum = base*100
    #save current dir
    prevDir = os.getcwd()
    #change directory to the location of the scans
    os.chdir(scanDir) 
    while(os.path.basename(os.getcwd()).lower() != "scans"):
        os.chdir("..") 
        #if we've run down to the root, give up
        if(os.path.basename(os.getcwd()) == ''):
            break; 
    #then offset to the next open number
    errorcatch=0
    while(len(glob.glob(str(newNum)+'*')) > 0):
        errorcatch+=1
        newNum+=1
        if(errorcatch > 100):
            newNum=base*1000+1
            break
        
    #move back to original directory
    os.chdir(prevDir)
    return newNum

def main():
    parseArgs()

    #open/create the log file
    myFile = os.path.join(args.usrPath, 'MPRAGE_dcm2nii.log')
    outputList = open(myFile,"w+")
    #look through each directory for the appropriate s in DICOM tag(0008,103E)
    #start in SCANS - note, this utility expects a very specific structure underneath SCANS - specifically .../SCANS/#/DICOM/files.dcm
    #enumerate the directories
    directories = os.listdir(args.directory)
    #for each directory, go to the first DICOM file
    fileFound = False
    #apAcqTime = 
    #paAcqTime = 
    filePath = ''
    modalityFrontEnd = 'modality'
    for dirs in directories:
        print("Search directory: %s \n" % args.directory)
        print("Current directory %s \n" % dirs)
        testPath = os.path.join(args.directory, dirs, 'resources/DICOM/files/*')
        print("Test directory: %s \n" % testPath)
        for filename in glob.glob(testPath):
            #I really just need one, all files should have the same series description or we have bigger issues
            firstFile = filename
            break;
        else:
            continue;
        #potential issues - if we need to exclude file extensions here, have them continue
        print("First file found is %s \n" % firstFile)
        #read the Series Description
        ds = dicom.read_file(firstFile)
        tagValue = ds[0x0008, 0x103E].value
        logName = ds[0x0010,0x0010].value
        #acqTagValue = ???????
        print("Tag value: %s \n" % tagValue)
        
        #find ap and pa directories
        #check is simple, so go ahead and recheck even if one was previously foundi
	InfileList = args.InfileDescription
	print("\nInput file description: " % InfileList) 
	for desc in args.InfileDescription:
	    print('  Checking: %s\n' % desc)
            if(desc in tagValue):
                if(fileFound==False): # or acqTagValue is newer than apAcqTime):
                    fileFound = True
                    filePath = os.path.join(args.directory, dirs, 'resources/DICOM/files/')
                    temp=ds[0x0020,0x0011].value
                    #scan number_scan description
                    modalityFrontEnd = "%d_%s" % (temp,  tagValue.replace('/', '').replace(' ', '_')) 
                    #apAcqTime = acqTagValue                                                                                           #JUST THE PATH OR THE DCM TOO?
        
    #if both have been found, run function and break  
    print("Found input file: %s \n" % fileFound)
  
    if(fileFound):
        print("calling subprocess dcm2nii \n")
        cmd='%s/MPRAGE_dcm2nii.py %s %s "MPRAGE.nii.gz" "-debug" > %s%s_dcm2niiProcess.log' % (os.path.join(args.usrPath,'utils'), filePath, args.usrPath, args.directory, logName)
        #cmd='%s/DWIPreprocessing %s %s %s "%s" "%s" %s %s > %s%s_DWIpreprocessing.log' % (args.files, args.directory, apPath, paPath, modalityFrontEnd, modalityFrontEnd2, args.useGeneratedBFiles, args.files, args.directory, logName)
        print(cmd+ '\n')
        subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]
	# call MPRAGE processing script
        print("calling subprocess MPRAGEprocessing \n")
        cmd='%s/MPRAGEprocessing.sh %s %s "%s"  > %s%s_MPRAGEprocessing.log' % (os.path.join(args.usrPath,'utils'), args.usrPath, os.path.join(args.usrPath,'utils'), modalityFrontEnd, args.directory, logName)
        print(cmd+ '\n')
        subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]

    outputList.close()
    
    return

if(__name__ == "__main__"):
    main()
