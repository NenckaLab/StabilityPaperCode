#! /usr/bin/env python

import sys
import os
import subprocess
import shutil
#print "\nmodule load python/2.7.11\nmodule load fsl/5.0.6\n. ${FSLDIR}/etc/fslconf/fsl.sh\nmodule load afni\n"

#module load fsl/5.0.6
#PATH=${FSLDIR}/bin:$PATH
#. ${FSLDIR}/etc/fslconf/fsl.sh
#module load dcm2niix/052016
cmd = "\nmodule load python/2.7.11\nmodule load fsl/5.0.6\nmodule load dcm2nii/122015\n. ${FSLDIR}/etc/fslconf/fsl.sh\nmodule load afni\n"
print cmd
output = \
    subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]

#binroot="/rcc/stor1/users"

#afniPath=binroot+"/anencka/linux_openmp_64/"
#mricronPath=binroot+"/anencka/mricron_lx/"

#Get teh arguments
inputDir = sys.argv[1]
print "inputDir: " + inputDir
usrPath = sys.argv[2]
print "\nusrPath: " + usrPath
outputFile = sys.argv[3]
print "\noutputFile: " + outputFile 
outPath = os.path.join(usrPath, 'Outputs')
#outFile.write('   outPath: %s \n' % outPath)
if(not os.path.isdir(outPath)):
    os.makedirs(outPath)

reconPath = os.path.join(usrPath, 'Reconstructions')
#outFile.write('   ReconPath: %s \n' % reconPath)
if(not os.path.isdir(reconPath)):
    os.makedirs(reconPath)


#debugging flag
if "-debug" in sys.argv:
    debugFlag = 1
else: 
    debugFlag = 0
print "debug = " + str(debugFlag)
#Get a useful variablea
origDir = os.getcwd()
if debugFlag:
    print "origDir = " + origDir

#Go to the input directory
#os.chdir(inputDir)

#Get the list of DICOMs
workDir = os.getcwd()
fileList = os.listdir(workDir)
if debugFlag:
    print "workDir = " + workDir
    #print "fileList = " 
    #print fileList

#Find the name of the first DICOM
myContinue=0
while (myContinue>=0 and myContinue<len(fileList)):
    thisFile = fileList[myContinue]
    if ".dcm" in thisFile:
        myContinue=-1
    else:
        myContinue = myContinue+1
    if debugFlag:
        print "myContinue = " + str(myContinue)
myContinue=0
while (myContinue>=0 and myContinue<len(fileList)):
    thisFile = fileList[myContinue]
    if ".ima" in thisFile:
        myContinue=-1
    else:
        myContinue = myContinue+1
    if debugFlag:
        print "myContinue = " + str(myContinue)
if ("ima" not in thisFile) and ('dcm' not in thisFile):
    thisFile = fileList[0]

if debugFlag:
    print "thisFile = " + thisFile

#Run the dcm2nii command
#icmd = mricronPath + "dcm2niix " + workDir + "/" + thisFile
cmd = "dcm2nii -o " + outPath + "  " +  inputDir 
if debugFlag:
    print "Command: "
    print cmd
output = \
    subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]
#output = subprocess.check_output(cmd,shell=True)
if debugFlag:
    print "output: " + output

#Find the output
os.chdir(outPath)
cmd = "ls -rt *.nii.gz"
output = \
    subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]
#output = subprocess.check_output(cmd,shell=True)
outputSplit = output.split()
niftiFile = outputSplit[0]
if debugFlag:
    print "Command " + cmd
    print "Output " + output
    print "niftiFile = " + niftiFile

shutil.move(outPath+"/"+niftiFile, outPath+'/tmp'+outputFile)
#for niftiName in outputSplit[1::1]:
 #   shutil.move(Outputs+"/"+niftiName, outputDir+'/'+niftiName)

# De-oblique it
os.chdir(origDir)
#cmd = afniPath +  "3drefit -deoblique " + outputDir +"/tmp"+outputFile
cmd = "3drefit -deoblique " + outPath +"/tmp"+outputFile
output = \
    subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]
#output = subprocess.check_output(cmd,shell=True)
if debugFlag:
    print "Command " + cmd
    print "Output " + output

#Finally FINALLY move to RPI-
#cmd = afniPath + "3dresample -orient RPI -inset "+outputDir+"/tmp"+outputFile
cmd =  "3dresample -orient RPI -inset "+outPath+"/tmp"+outputFile
cmd = cmd+" -prefix "+outPath+"/"+outputFile
output = \
    subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]
#output = subprocess.check_output(cmd,shell=True)
if debugFlag:
    print "Command " + cmd
    print "Output " + output

#Clean up
cmd = "rm -f " + outPath+'/tmp'+outputFile
output = \
    subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]
