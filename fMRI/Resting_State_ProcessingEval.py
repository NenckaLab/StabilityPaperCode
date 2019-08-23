#! /usr/bin/env python2.7

#Load libraries for working with command line arguments
import os
import glob
#Load libraries for working with DICOM images
import dicom
import argparse
import subprocess
import json

#Load the dataset
myFolder = 'thisProject'
args = []
logName = 'notFound'
usabilityScores = {'unusable':0, 'questionable':1,'usable':2}
usabilityList = []

#functions
def parseArgs():
    #parses all of the passed in arguments
    global args
    parser = argparse.ArgumentParser(description='This is a demo script by nixCraft.')
    parser.add_argument('-D', '--directory', help='Scan directory to search for scan description. Subdir should be #/DICOM/files', default='.')
    parser.add_argument('-AP', '--APFileDescription', help='Scan description to flag for use as a/p', action='append', default = [])
    parser.add_argument('-PA', '--PAFileDescription', help='Scan description to flag for use as p/a', action='append', default = [])
    parser.add_argument('-up', '--usrPath', help='Folder path for input configuration files.', default='.')
    parser.add_argument('-ac', '--AcParamFile', help='Acquisition parameters file to use. File should be located in SupportDirectory', default='acqparams.txt')
    parser.add_argument('-us', '--UsabilityScores', help='List of dictionaries. Dictionaries must contain ID and quality.', action='append', default=[])    
    args = parser.parse_args()
    return

def newScoreBetter(oldAPscore, usability, scanNumber):
    #assesses whether the new score is better than the existing one
    if(usabilityScores[usability] > usabilityScores[oldAPscore['Usability']]):
        print "new score better because of usability %s %s %s" % (str(scanNumber), usability, oldAPscore['Usability'])
        return True
    elif(usabilityScores[usability] == usabilityScores[oldAPscore['Usability']]):
        print "usability identical, returning time point newer %s:%s %s:%s" % (str(scanNumber), usability, str(oldAPscore['ScanID']), oldAPscore['Usability'])
        return (scanNumber > int(oldAPscore['ScanID']))
    return False

def getUsability(scanNumber):
    global usabilityList
    if(usabilityList == []):
#         print args.UsabilityScores
        #only populate the global list the first time
        for a in args.UsabilityScores:
#             print a
#             print a.replace("'", "")
            usabilityList.append(json.loads(a.replace("'","")))
    #returns the usability of the scan
    for j in usabilityList:
        if(j['ID'] == scanNumber):
            return j['quality']
    return 'unusable'

def checkFile(currentDirectory, dicomHeader, tagList, resultDictionary):
    #checks if the current file is in the taglist and is better suited than any listed in the resultDictionary
    #i.e. if it is the best known result
    tagValue = dicomHeader[0x0008, 0x103E].value
    for a in tagList:
        if(tagValue == a):
            scanNumber = dicomHeader[0x0020, 0x0011].value
            #need a check to see if this is a better option than any previous success
            usability = getUsability(str(scanNumber))
            #outputList.write("Usability of %s is %s\n" % (scanNumber, usability)) 
            if(newScoreBetter(resultDictionary, usability, scanNumber)): # or acqTagValue is newer than apAcqTime):
                resultDictionary['Usability']= usability
                resultDictionary['ScanID']= scanNumber
                #resultDictionary['found'] = True
                resultDictionary['filepath'] = os.path.join(args.directory, currentDirectory, 'resources/DICOM/files/')
                #scan number_scan description
                resultDictionary['modalityFrontEnd'] = "%d_%s" % (scanNumber,  tagValue.replace('/', '').replace(' ', '_'))
                resultDictionary['trms'] = dicomHeader[0x0018,0x0080].value
                #multivalue tags really don't like .upper()
                try:
                    resultDictionary['siemens'] = ('SIEMENS' in (dicomHeader[0x0008,0x0070].value).upper())
                except:
                    resultDictionary['siemens'] = ('SIEMENS' in dicomHeader[0x0008,0x0070].value)
                #our DV25 scans were actually run through Orchestra and only contains 25, which, unfortunately, also appears in the build version in DV26
                #I am concerned that, at some point in the future, we could wind up with a DV26+ that would have 25 and Orchestra appear in the tag...
                if( ('DV25' in dicomHeader[0x0018,0x1020].value) or
                    (('25' in dicomHeader[0x0018,0x1020].value) and ('Orchestra SDK' in dicomHeader[0x0018,0x1020].value)) ):
                    resultDictionary['old'] = True
                else:
                    resultDictionary['old'] = False
                #acquisition duration    0019,105A     dv26 ARC 6.0000058E8
                #tr                      0018,0080     dv26 ARC 2000 720
                
                #resultDictionary['outpath'] = os.path.join(args.usrPath, 'epiNifTi', 'orig')
    return resultDictionary

def dcm2nii(resultsDictionary, desc, logName):
    #calls dcm2nii if appropriate
    if(resultsDictionary['Usability'] != 'unusable'):
        print("calling subprocess dcm2nii on %s" % desc)
        cmd='%s/fMRI_dcm2nii.py %s %s "rawEPI.nii.gz" %s "-debug" > %s/%s_%sdcm2niiProcess.log' % (os.path.join(args.usrPath,'utils'), resultsDictionary['filepath'], args.usrPath, resultsDictionary['outpath'], args.usrPath, logName, desc)
        print(cmd+ '\n')
        subprocess.check_output(cmd, shell=True)
    return

def main():
    parseArgs()
    #open/create the log file
    myFile = os.path.join(args.usrPath, 'fMRI_dcm2nii.log')
    outputList = open(myFile,"w+")
    #look through each directory for the appropriate s in DICOM tag(0008,103E)
    #start in SCANS - note, this utility expects a very specific structure underneath SCANS - specifically .../SCANS/#/DICOM/files.dcm
    #enumerate the directories
    directories = os.listdir(args.directory)
    #for each directory, go to the first DICOM file
    APFile = {'filepath':'', 'outpath':os.path.join(args.usrPath, 'epiNifTi', 'orig'), 'modalityFrontEnd':'', 'Usability':'unusable', 'ScanID':'0', 'trms':'0', 'siemens':False, 'old':False}
    PAFile = {'filepath':'', 'outpath':os.path.join(args.usrPath, 'revPeNifTi', 'orig'), 'modalityFrontEnd':'', 'Usability':'unusable', 'ScanID':'0', 'trms':'0', 'siemens':False, 'old':False}    
    
    #modalityFrontEnd = 'modality'
    
    print("A/P file description" + "  ".join(args.APFileDescription))
    if(len(args.PAFileDescription) > 0):
        print("P/A file description" + "  ".join(args.PAFileDescription))
    for dirs in directories:
        #print out some troubleshooting variables
        print("Search directory: %s " % args.directory)
        print("Current directory %s " % dirs)
        testPath = os.path.join(args.directory, dirs, 'resources/DICOM/files/*')
        print("Test directory: %s " % testPath)
        
        #find the first filename, then break
        for filename in glob.glob(testPath):
            firstFile = filename
            break;
        else:
            continue;
        #potential issues - if we need to, exclude file extensions here, have them continue
        print("First file found is %s " % firstFile)
        #read the Series Description
        ds = dicom.read_file(firstFile)
        tagValue = ds[0x0008, 0x103E].value
        logName = ds[0x0010,0x0010].value
        print("Tag value: %s \n" % tagValue)
        
        #find ap and pa directories
        APFile = checkFile(dirs, ds, args.APFileDescription, APFile)
        
        if(len(args.PAFileDescription) > 0):
            PAFile = checkFile(dirs, ds, args.PAFileDescription, PAFile)
        
    print("A/P file Usability: %s   " % APFile['Usability'])
    print("P/A file Usability: %s \n" % PAFile['Usability'])
  
    #call dcm2nii on scans
    dcm2nii(APFile, 'AP', logName)
    dcm2nii(PAFile, 'PA', logName)

    legacyProject = ''
    tr_cut = 0
    if((APFile['Usability'] != 'unusable') and (PAFile['Usability'] != 'unusable')):
        legacyProject = 'H2H2'
        if(APFile['old']):
            #DV25
            tr_cut = 16
        else:
            #DV26 and newer
            tr_cut = 30
    elif((APFile['Usability'] != 'unusable') and (len(args.PAFileDescription) == 0)):
        legacyProject = 'ARC'
        if(APFile['siemens']):
            tr_cut = 0
        else:
            tr_cut = 6       
    else:
        #does not match known run configurations, return with failure
        return 1
    
    #call Resting State processing script
    print("calling subprocess Resting_processing")
    cmd='%s/Resting_State_Processing.sh  %s "%s" %s %d > %s/Resting_State_Processing.log \n' % (os.path.join(args.usrPath,'utils'), args.usrPath, legacyProject, APFile['trms'], tr_cut, args.usrPath)
    #cmd='%s/MPRAGEprocessing.sh %s %s "%s"  > %s%s_MPRAGEprocessing.log' % (os.path.join(args.usrPath,'utils'), args.usrPath, os.path.join(args.usrPath,'utils'), modalityFrontEnd, args.directory, logName)
    print(cmd+ '\n')
    subprocess.check_output(cmd, shell=True)

    #call Resting State processing script
    print("calling subprocess Reho_processing")
    cmd='%s/Reho_Processing.sh  %s "%s" > %s/Reho_Processing.log \n' % (os.path.join(args.usrPath,'utils'), args.usrPath, APFile['modalityFrontEnd'], args.usrPath)
    print(cmd+ '\n')
    subprocess.check_output(cmd, shell=True)

    outputList.close()
    
    return

if(__name__ == "__main__"):
    main()
