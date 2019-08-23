#! /usr/bin/env python2.7

import os
import argparse
import subprocess
import sys
#import json
import re
import XNATServer
import ClusterMonitor as cm

args = []
exitStatus = 0
DEFAULT_DIRECTORY=os.environ['HOME']

def parseArgs():
    global args
    parser = argparse.ArgumentParser(description='test')
    parser.add_argument('-u', '--User', help='XNAT user login name.', required=True)
    parser.add_argument('-p', '--Password', help='XNAT password.', required=True)
    parser.add_argument('-a', '--Address', help='XNAT address.', default='http://cirxnat1.rcc.mcw.edu/xnat')
    parser.add_argument('-P', '--Project', help='XNAT project.', required=True)
    parser.add_argument('-e', '--Experiment', help='XNAT Experiment.', required=True)
    parser.add_argument('-s', '--Subject', help='XNAT Subject.',required=True)
    parser.add_argument('-fp', '--PrimaryFile', help='Partial description of the NII file to translate to MNI. Script will attempt to find this file part in the XNAT experiment.', action='append', required=True)
    parser.add_argument('-fs', '--SecondaryFile', help='Partial description of additional NII file to translate to MNI. Script will attempt to find this file part in the XNAT experiment.', action='append', default=[])
    parser.add_argument('-m', '--MPRAGE', help='Partial description of the NII nat space MPRAGE file. Script will attempt to find this file part in the XNAT experiment.', action='append', required=True)
    parser.add_argument('-w', '--Warp', help='Partial description of the NII MPRAGE warp to MNI file. Script will attempt to find this file part in the XNAT experiment.', action='append', required=True)
    parser.add_argument('-c', '--Cost', help='Cost function to use for flirt. Must match flirt options.', required=True)
    parser.add_argument('-on', '--OutputName', help='Name token to replace custom portion of filename. Will be Project_Exp_Scan_mni__orig__OutputName__all__0__v#', required=True)
    parser.add_argument('-v', '--Verbose', help='Verbose output.', action="store_true")
    args = parser.parse_args()
    
    #TODO
    #add outfile token - QSMReg2Brain, ASLReg2All, etc
    
    return


def printCheck(outText):
    if(args.Verbose):
        print(outText)
    return

def unzipFile(outFile, inPath, destPath):
    unzipCmd = 'unzip -jo -q %s -d %s \n' % (inPath, destPath)
    outFile.write('    unzip Recon: %s \n' % unzipCmd)
    result = subprocess.check_output(unzipCmd, shell=True)
    outFile.write('   Unzip result: %s\n' % result)
    return

def getAllRecons(server, outFile):
    returnList = []
    reconList = server.getReconstructionFolderNames(args.Subject, args.Experiment)
    for recon in reconList:
        fnames = server.getReconstructionFilenames(args.Subject, args.Experiment, recon)
        #outFile.write('Recon: %s\n' % recon)
        for fname in fnames:
            #outFile.write(' Fname: %s\n' % fname)
            returnList.append({'Folder':recon, 'File':fname})
    return returnList

def downloadCheck(reconNameList, reconDict, server, usrPath, outFile):
    filename = ''
    for x in reconNameList:
        if(x in reconDict['File']):
            outFile.write('  Found: %s\n' % x)
            #get recon
            server.zipReconstructionToFile(args.Subject, args.Experiment, reconDict['Folder'], os.path.join(usrPath, x + '_download.zip'))
            unzipFile(outFile, os.path.join(usrPath, x + '_download.zip'), usrPath)
            filename = reconDict['File']
            break
    return filename

def getNewBaseName(inputFileName):
    #sets up the proper file name for the outputs
    newName = inputFileName.replace(args.Project + '_', '')
    newName = newName.replace(args.Experiment + '_', '')
    
    #try global based on newer standardized naming convention
    fnameEnd = '__nat__orig__[\w\_\.]*'
    newName = re.sub(fnameEnd, '__mni__orig__' + args.OutputName + '__all__0__v1.nii.gz', newName)
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
    newName = re.sub(fnameEnd, args.OutputName + '__all__0__v1.nii.gz', newName)
    print newName
    #again, both naming conventions
    fnameEnd = 'orig_all_0.nii'
    #newName = re.sub(fnameEnd, args.OutputName + '__all__0__v1.nii.gz', newName)
    newName = newName.replace(fnameEnd, args.OutputName + '__all__0__v1.nii.gz')
    fnameEnd = 'orig_all_O.nii'
    newName = newName.replace(fnameEnd, args.OutputName + '__all__0__v1.nii.gz')
    print newName
    newName = newName.replace('.gz.gz', '.gz')
    print newName
    return newName

def createScript(usrPath, primaryName, secondaryName, mprageName, mprageWarpName, pbsFileName):
    
    #Write the pbs driver script
    pbsFile = open(pbsFileName, 'w')
    
    pbsDocHeader="""#!/bin/bash
#PBS -l nodes=1:ppn=1,mem=5000m,walltime=1:00:00
#PBS -M bswearingen@mcw.edu
#PBS -m a
#PBS -j oe
"""

    pbsFile.write(pbsDocHeader)
    #job name
    pbsFile.write("#PBS -N Nat2MNI_CIR1_" + args.Experiment + "\n")
    #load required support files    
    pbsFile.write("\nmodule load python/2.7.11\nmodule load fsl/5.0.9\n. ${FSLDIR}/etc/fslconf/fsl.sh\nmodule load afni/16.2.16\n\n")

    # usage freesurfer_pipeline <input file> <subjects_dir> <subject_name> -- file will be output as <subject_name>.zip in the same directory as this is run from 
    pbsFile.write("cd %s \n" % usrPath) 
    #pbsFile.write("mkdir %s \n" % os.path.join(usrPath, outName))
    pbsFile.write('mkdir %s\n' % os.path.join(usrPath, 'Reconstructions'))
    
    primaryOutName = getNewBaseName(primaryName)
    primaryOutFile = os.path.join(usrPath, 'Reconstructions', primaryOutName)
    #handle both cases
    matFile = os.path.join(usrPath, 'Reconstructions', primaryOutName.replace('nii.gz','mat').replace('nii', 'mat'))
    
    pbsFile.write("3drefit -deoblique %s\n" % os.path.join(usrPath, primaryName))
    pbsFile.write("3dresample -orient RPI -inset %s -preset %s\n" % (os.path.join(usrPath,primaryName), os.path.join(usrPath, 'resampleout.nii.gz')))
    pbsFile.write("flirt -ref %s -in %s -out %s -omat %s -cost %s -dof 6 -interp trilinear -v\n" % (os.path.join(usrPath,mprageName), os.path.join(usrPath, 'resampleout.nii.gz'), os.path.join(usrPath, 'notUsed.nii.gz'), matFile, args.Cost))
    
    if(secondaryName != ''):
        pbsFile.write("3drefit -deoblique %s\n" % secondaryName)
        pbsFile.write("3dresample -orient RPI -inset %s -preset %s\n" % (os.path.join(usrPath,secondaryName), os.path.join(usrPath, 'resampleout2.nii.gz')))
        pbsFile.write("flirt -ref %s -in %s -out %s -applyxfm -init %s -interp trilinear -v\n" % (os.path.join(usrPath,mprageName), os.path.join(usrPath, 'resampleout2.nii.gz'), os.path.join(usrPath, 'notUsed2.nii.gz'), matFile))
        
    pbsFile.write("applywarp --ref=%s --in=%s --out=%s --warp=%s --premat=%s -v\n" % ('${FSLDIR}/data/standard/MNI152_T1_2mm.nii.gz', os.path.join(usrPath, 'resampleout.nii.gz'), primaryOutFile, os.path.join(usrPath, mprageWarpName), matFile))
                  
    if(secondaryName != ''):
        secondaryOutName = getNewBaseName(secondaryName)
        secondaryOutFile = os.path.join(usrPath, 'Reconstructions', secondaryOutName)
        pbsFile.write("applywarp --ref=%s --in=%s --out=%s --warp=%s --premat=%s -v\n" % ('${FSLDIR}/data/standard/MNI152_T1_2mm.nii.gz', os.path.join(usrPath, 'resampleout2.nii.gz'), secondaryOutFile, os.path.join(usrPath, mprageWarpName), matFile))

# #     #Recon Upload
    pbsFile.write('%s/bin/ReconstructionUpload.py -d %s -da %s -dP %s -ds %s -de %s -du %s -dp %s \n' % \
                   (DEFAULT_DIRECTORY, os.path.join(usrPath, 'Reconstructions'), args.Address, args.Project, args.Subject, args.Experiment, args.User, args.Password))
    pbsFile.close()
    return

def main():
    global exitStatus
    parseArgs()  
    
    server = XNATServer.XNATProject(args.Address, args.Project, args.User, args.Password)
    
    #set up the required folder structure
    usrPath=os.path.join(DEFAULT_DIRECTORY, args.Experiment + '_n2s')
    logPath=os.path.join(DEFAULT_DIRECTORY, 'logs')
    if(not os.path.isdir(usrPath)):
        os.makedirs(usrPath)
    if(not os.path.isdir(logPath)):
        os.makedirs(logPath)
    outFile = open(os.path.join(logPath, args.Experiment + '_NAT2MNIFile.txt'), 'a+')
    #print a bunch of variables for troubleshooting purposes
    for a in vars(args):
        outFile.write('%s: %s\n' % (a, vars(args)[a]))
    if(len(args.SecondaryFile) > 0):
        outFile.write('args.SecondaryFile: %s \n' % args.SecondaryFile)
    
    pbsFileName = os.path.join(usrPath, 'pbsParallelSubmitNAT2MNI_CIR1.sh')
    
    
    ########################### FIND AND DOWNLOAD THE CORRECT RECONSTRUCTION
    #find reconstruction
    primaryName = ''
    secondaryName = ''
    mprageName = ''
    mprageWarpName = ''
    
    reconList = getAllRecons(server, outFile)
    for x in reconList:
        outFile.write("Recon Found on Server: {%s,%s} \n" % (x['Folder'], x['File']))            
            
    for r in reconList:  
        #if we haven't found the recon yet, check the list against this reconstruction      
        if(primaryName == ''):
            primaryName = downloadCheck(args.PrimaryFile, r, server, usrPath, outFile)
        if(secondaryName == ''):
            secondaryName = downloadCheck(args.SecondaryFile, r, server, usrPath, outFile)   
        if(mprageName == ''):
            mprageName = downloadCheck(args.MPRAGE, r, server, usrPath, outFile)
        if(mprageWarpName == ''):
            mprageWarpName = downloadCheck(args.Warp, r, server, usrPath, outFile)
    
    #exit if the file is not found    
    if(primaryName=='' or mprageName=='' or mprageWarpName==''):
        outFile.write("File not found. primary %s : mprage %s : warp %s" % (primaryName, mprageName, mprageWarpName))
        exitStatus=2
        return
    
    ########################################################
    #Create Script
    #createScript(usrPath, utilPath, primaryName, secondaryName, mprageName, mprageWarpName, 'tempOutName', pbsFileName, args.Experiment)
    createScript(usrPath, primaryName, secondaryName, mprageName, mprageWarpName, pbsFileName)
    ######################################################    
    #execute script
    outFile.write('pbsFileName: %s \n' % pbsFileName)
    os.chdir(usrPath)
    jobID = subprocess.check_output('qsub %s' % (pbsFileName), shell=True)
    outFile.write('JobID: %s' % jobID)
    
    ####################################################### Monitor
    if(args.SecondaryFile != []):
        count = 3
    else:
        count = 2
    resultsSuccess = cm.monitorCluster(outFile, usrPath, count, jobID)
    
    ###################################################### Finalize
    os.chdir(DEFAULT_DIRECTORY)   
    exitStatus = cm.cleanup(resultsSuccess, outFile, usrPath)
    outFile.close()
    return

if(__name__ == "__main__"):
    main()
    sys.exit(exitStatus)
