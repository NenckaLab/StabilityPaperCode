#! /usr/bin/env python2.7

#v2 - added logic to reorient images to std orientation before warping to standard space

#Load libraries for working with command line arguments
import os
import argparse
import subprocess 
import shutil
import re

#Load the dataset
args = []

#functions
def parseArgs():
    #parses all of the passed in arguments
    global args
    parser = argparse.ArgumentParser(description='This is a demo script by nixCraft.')
    parser.add_argument('-D', '--directory', help='Scan directory to search for scan description. Subdir should be #/DICOM/files', default='.')
    parser.add_argument('-f', '--file', help='DTI nifti file name', required=True)
    parser.add_argument('-c', '--configs', help='configuration files', default='.')
    args = parser.parse_args()
    return

def fireStrCmd(strCmd):
    print '\n\n'
    print strCmd
    result = subprocess.check_output(strCmd, shell=True)
    print result
    print 'complete\n\n'
    return result

def correctOrientation(infile, outfile):
    fireStrCmd("3drefit -deoblique %s\n" % infile)
    fireStrCmd("3dresample -orient RPI -inset %s -preset %s\n" % (infile, outfile))
    return

def argsDir(filename):
    #returns the filename as a fqn in the args.directory path
    return os.path.join(args.directory, filename)

def main():
    parseArgs()

    #templog = ' >> ' + args.configs + '/temp.log'
    #some commonly used terms
    reconPath = os.path.join(args.directory, 'Reconstructions')
    template = '${FSLDIR}/data/standard/FMRIB58_FA_1mm.nii.gz'
    cnf = '${FSLDIR}/etc/flirtsch/FA_2_FMRIB58_1mm.cnf'
    matFile = argsDir('FA2FMRIB58.mat')
    warpFile = argsDir('warp_FA2standard.nii.gz')

    #need regular expression capabilities to handle different versions
    fnameEnd = 'nat__other__FINAL_DTI_PREPROCESS__all__0__v\d+.nii.gz'
    
    #create mask
    fireStrCmd('bet ' + argsDir(args.file) + ' ' + argsDir('DTI.nii.gz') + ' -m -n -f 0.3' + ' -v ')

    # generate FA and MD maps
    fireStrCmd('dtifit --save_tensor -k %s -o %s -m %s -r %s -b %s -w' % (argsDir(args.file), argsDir('DTI'), argsDir('DTI_mask.nii.gz'), os.path.join(args.configs, 'bvecs.txt'), os.path.join(args.configs, 'bvals.txt')))
    
    #move all to standard orientation
    correctOrientation(argsDir('DTI_FA.nii.gz'), argsDir('DTI_FAre.nii.gz'))
    correctOrientation(argsDir('DTI_MD.nii.gz'), argsDir('DTI_MDre.nii.gz'))
    correctOrientation(argsDir('DTI_MO.nii.gz'), argsDir('DTI_MOre.nii.gz'))

    # FA to FMRIB58 to FA template
    fireStrCmd('flirt -ref %s -in %s -omat %s -v' % (template, argsDir('DTI_FAre.nii.gz'), matFile))
    fireStrCmd('fnirt --config=%s --in=%s --aff=%s --cout=%s --iout=%s -v' % (cnf, argsDir('DTI_FAre.nii.gz'), matFile, warpFile, argsDir('FA2standard.nii.gz')))
    fireStrCmd('applywarp --ref=%s --in=%s --out=%s --warp=%s -v' % (template, argsDir('DTI_MDre.nii.gz'), argsDir('MD2standard.nii.gz'), warpFile))
    fireStrCmd('applywarp --ref=%s --in=%s --out=%s --warp=%s -v' % (template, argsDir('DTI_MOre.nii.gz'), argsDir('MO2standard.nii.gz'), warpFile))

    print ('OUT PATH: %s\n' % args.directory)
    print ('FILE: %s\n' % args.file) 
    print ('DWI_FILE: %s\n' % argsDir(args.file))
    
    # move outputs to Reconstruction folder for upload
    shutil.copy(argsDir('DTI_mask.nii.gz'),         os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI__mask__0__v3.nii.gz', args.file))) #dwiFname.replace(fnameEnd,'nat_result_DTI_mask_0_v1.nii.gz')))
    shutil.copy(argsDir('DTI_FA.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_FA__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_MD.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_MD__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('FA2standard.nii.gz'),      os.path.join(reconPath, re.sub(fnameEnd, 'mni__result__DTI_FA__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('MD2standard.nii.gz'),      os.path.join(reconPath, re.sub(fnameEnd, 'mni__result__DTI_MD__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('FA2FMRIB58.mat'),          os.path.join(reconPath, re.sub(fnameEnd, 'nat__reg__DTI_FA2standard__all__0__v3.mat', args.file)))
    shutil.copy(argsDir('warp_FA2standard.nii.gz'), os.path.join(reconPath, re.sub(fnameEnd, 'mni__result__DTI_FA_warp__all__0__v3.nii.gz', args.file)))
    
    
    shutil.copy(argsDir('DTI_MO.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_MO__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_S0.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_S0__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_L1.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_L1__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_L2.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_L2__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_L3.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_L3__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_V1.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_V1__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_V2.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_V2__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('DTI_V3.nii.gz'),           os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_V3__all__0__v3.nii.gz', args.file)))
    shutil.copy(argsDir('MO2standard.nii.gz'),      os.path.join(reconPath, re.sub(fnameEnd, 'mni__result__DTI_MO__all__0__v3.nii.gz', args.file)))
    
    
    shutil.copy(argsDir('DTI_tensor.nii.gz'),       os.path.join(reconPath, re.sub(fnameEnd, 'nat__result__DTI_tensor__all__0__v3.nii.gz', args.file)))
    
    
    


    return

if(__name__ == "__main__"):
    main()

