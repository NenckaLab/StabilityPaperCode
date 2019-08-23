#! /usr/bin/env python2.7

#Load libraries for working with command line arguments
import os
import argparse
import subprocess
import re

#Load the dataset
args = []
index = 1
version = 'v2'

#functions
def parseArgs():
    #parses all of the passed in arguments
    global args
    parser = argparse.ArgumentParser(description='This is a demo script by nixCraft.')
    parser.add_argument('-D', '--directory', help='Scan directory to search for scan description. Subdir should be #/DICOM/files', default='.')
    parser.add_argument('-f', '--InfileDescription', help='Scan description to flag for use.', default = '')
    parser.add_argument('-sf', '--SecondaryFileDescription', help='Other files to be registered.', action='append', default = [])
    parser.add_argument('-up', '--usrPath', help='Folder path for input configuration files.', default='.')
    
    parser.add_argument('-u', '--User', help='XNAT user login name.', required=True)
    parser.add_argument('-p', '--Password', help='XNAT password.', required=True)
    parser.add_argument('-a', '--Address', help='XNAT address.', default='http://cirxnat1.rcc.mcw.edu/xnat')
    parser.add_argument('-P', '--Project', help='XNAT project.', required=True)
    parser.add_argument('-e', '--Experiment', help='XNAT Experiment.', required=True)
    parser.add_argument('-s', '--Subject', help='XNAT Subject.',required=True)
    
    parser.add_argument('-m', '--MPRAGE', help='Partial description of the NII nat space MPRAGE file. Script will attempt to find this file part in the XNAT experiment.', required=True)
    parser.add_argument('-w', '--Warp', help='Partial description of the NII MPRAGE warp to MNI file. Script will attempt to find this file part in the XNAT experiment.', required=True)
    
    args = parser.parse_args()
    return

def fireCmd(cmd):
    print cmd
    subprocess.check_output(cmd, shell=True)
    return

def primaryRegister(usrPath, primaryInName, primaryOutName, mprageName, mprageWarpName ):
    #register the primary file, return the mat file
    matFile = os.path.join(usrPath, 'Reconstructions', primaryOutName.replace('nii.gz','mat').replace('nii', 'mat'))
    primaryOutFile = os.path.join(usrPath, 'Reconstructions', primaryOutName)
    fireCmd("3drefit -deoblique %s\n" % os.path.join(usrPath, primaryInName))
    fireCmd("3dresample -orient RPI -inset %s -preset %s\n" % (os.path.join(usrPath,primaryInName), os.path.join(usrPath, 'resampleout.nii.gz')))
    fireCmd("flirt -ref %s -in %s -out %s -omat %s -cost mutualinfo -dof 6 -interp trilinear -v\n" % (os.path.join(usrPath,mprageName), os.path.join(usrPath, 'resampleout.nii.gz'), os.path.join(usrPath, 'notUsed.nii.gz'), matFile))
    fireCmd("applywarp --ref=%s --in=%s --out=%s --warp=%s --premat=%s -v\n" % ('${FSLDIR}/data/standard/MNI152_T1_2mm.nii.gz', os.path.join(usrPath, 'resampleout.nii.gz'), primaryOutFile, os.path.join(usrPath, mprageWarpName), matFile))        
    return matFile

def secondaryRegister(usrPath, secondaryInName, secondaryOutName, mprageName, mprageWarpName, matFile):
    #register a secondary file using the given mat file
    global index
    secondaryOutFile = os.path.join(usrPath, 'Reconstructions', secondaryOutName)
    resampleFile = os.path.join(usrPath, 'resampleout' + str(index) + '.nii.gz')
    index += 1
    fireCmd("3drefit -deoblique %s\n" % secondaryInName)
    fireCmd("3dresample -orient RPI -inset %s -preset %s\n" % (os.path.join(usrPath, secondaryInName), resampleFile))
    fireCmd("flirt -ref %s -in %s -out %s -applyxfm -init %s -interp trilinear -v\n" % (os.path.join(usrPath,mprageName), resampleFile, os.path.join(usrPath, 'notUsed2.nii.gz'), matFile))
    fireCmd("applywarp --ref=%s --in=%s --out=%s --warp=%s --premat=%s -v\n" % ('${FSLDIR}/data/standard/MNI152_T1_2mm.nii.gz', resampleFile, secondaryOutFile, os.path.join(usrPath, mprageWarpName), matFile))
    return

def getNewBaseName(inputFileName, outputToken):
    #calculate the output name
    #sets up the proper file name for the outputs
    newName = inputFileName.replace(args.Project + '_', '')
    newName = newName.replace(args.Experiment + '_', '')
    
    #try global based on newer standardized naming convention
    fnameEnd = '__nat__orig__[\w\_\.]*'
    newName = re.sub(fnameEnd, '__mni__orig__' + outputToken + '__all__0__' + version + '.nii.gz', newName)
    print newName
    
    #first part of trailing name
    print newName
    newName = newName.replace('__nat__orig__', '__mni__orig__')
    print newName
    #need to handle both naming conventions
    newName = newName.replace('_nat_orig_', '__mni__orig__')
    print newName
    
    #second part of trailing
    #do I need to replace the second orig? I hate the second orig being there, but not sure how we standardize this portion
    fnameEnd = 'orig__all__0__v\d+.nii.gz'
    newName = re.sub(fnameEnd, outputToken + '__all__0__' + version + '.nii.gz', newName)
    print newName
    #again, both naming conventions
    fnameEnd = 'orig_all_0.nii'
    #newName = re.sub(fnameEnd, args.OutputName + '__all__0__v1.nii.gz', newName)
    newName = newName.replace(fnameEnd, outputToken + '__all__0__' + version + '.nii.gz')
    fnameEnd = 'orig_all_O.nii'
    newName = newName.replace(fnameEnd, outputToken + '__all__0__' + version + '.nii.gz')
    print newName
    newName = newName.replace('.gz.gz', '.gz')
    print newName
    return newName

def main():
    parseArgs()

    #open/create the log file
    myFile = os.path.join(args.usrPath, 'ASL.log')
    outputList = open(myFile,"w+")
    
    mat = primaryRegister(args.usrPath, args.InfileDescription, getNewBaseName(args.InfileDescription, 'ASL_M0'), args.MPRAGE, args.Warp )
    
    for x in args.SecondaryFileDescription:
        if('dM' in x):
            secondaryRegister(args.usrPath, x, getNewBaseName(x, 'ASL_dM'), args.MPRAGE, args.Warp, mat)
        elif(('CBF' in x) or ('CerebralBloodFlow' in x) or ('Cerebral_Blood_Flow' in x)):
            secondaryRegister(args.usrPath, x, getNewBaseName(x, 'ASL_CBF'), args.MPRAGE, args.Warp, mat)
        else:
            secondaryRegister(args.usrPath, x, getNewBaseName(x, 'ASL'    ), args.MPRAGE, args.Warp, mat)
        
    outputList.close()
    
    return

if(__name__ == "__main__"):
    main()
