#!/bin/sh
# MPRAGE processing 
################################################################################
## SCRIPT TO PREPROCESS THE ANATOMICAL SCAN MPRAGE
## 
################################################################################

module load fsl/5.0.6
PATH=${FSLDIR}/bin:$PATH
. ${FSLDIR}/etc/fslconf/fsl.sh
module load dcm2nii/122015
module load afni

echo_time() {
    date +"%R $*"
}

echo_time "Current directory: "
pwd

# $1 is user directory, $2 utils directory, $3 is Series number and description (modality)

standard_res=2mm #ASN modified
standard_brain=${FSLDIR}/data/standard/MNI152_T1_${standard_res}_brain.nii.gz
usrPath=$1
utilPath=$2
exptLabel=$3
outputPath=${usrPath}/Outputs/
if [ -d '/rcc/stor1/projects/BIRP/MATLAB/MATLAB_Compiler_Runtime/v84' ]; then
  matlabPath=/rcc/stor1/projects/BIRP/MATLAB/MATLAB_Compiler_Runtime/v84
else
  matlabPath=/data/MATLAB/MATLAB_Compiler_Runtime/v84
fi
# make outputs folders 
mkdir $1/anatOrig
mkdir $1/anatSeg
mkdir $1/anatReg
################################################################################
##---START OF SCRIPT-----------------------------------------------------------#
################################################################################

echo --------------------------------------
echo !!!! PREPROCESSING ANATOMICAL SCAN!!!!
echo --------------------------------------

3dcopy ${outputPath}/MPRAGE.nii.gz ${usrPath}/anatOrig/MPRAGE.nii
${utilPath}/run_asnStrippedSpmRunSeg.sh ${matlabPath} ${usrPath}/anatOrig/MPRAGE.nii ${utilPath}/spm12/tpm/TPM.nii
mv $usrPath/anatOrig/c*MPRAGE.nii $usrPath/anatSeg
mv $usrPath/anatOrig/MPRAGE.nii $usrPath/anatSeg

    3drefit –space ORIG –view orig –newid ${usrPath}/anatSeg/c1MPRAGE.nii
    3drefit –space ORIG –view orig –newid ${usrPath}/anatSeg/c2MPRAGE.nii
    3drefit –space ORIG –view orig –newid ${usrPath}/anatSeg/c3MPRAGE.nii
    3drefit –space ORIG –view orig –newid ${usrPath}/anatSeg/c4MPRAGE.nii
    3drefit –space ORIG –view orig –newid ${usrPath}/anatSeg/c5MPRAGE.nii
    3drefit –space ORIG –view orig –newid ${usrPath}/anatSeg/MPRAGE.nii

        #prepare GM/WM segmentations for AFNI
    3dcopy ${usrPath}/anatSeg/c1MPRAGE.nii ${usrPath}/anatSeg/GMseg.nii.gz
    3dcopy ${usrPath}/anatSeg/c2MPRAGE.nii ${usrPath}/anatSeg/WMseg.nii.gz
    3dcopy ${usrPath}/anatSeg/c3MPRAGE.nii ${usrPath}/anatSeg/CSFseg.nii.gz
    3drefit -view orig -space ORIG ${usrPath}/anatSeg/GMseg.nii.gz
    3drefit -view orig -space ORIG ${usrPath}/anatSeg/WMseg.nii.gz
    3drefit -view orig -space ORIG ${usrPath}/anatSeg/CSFseg.nii.gz


echo --------------------------------------
echo !!!! PREPROCESSING SKULL STRIP!!!!
echo --------------------------------------
 ## 3. skull strip
 echo "skull stripping ${exptLabel} anatomical"
        3dcalc -a ${usrPath}/anatSeg/MPRAGE.nii \
               -b ${usrPath}/anatSeg/c1MPRAGE.nii \
               -c ${usrPath}/anatSeg/c2MPRAGE.nii \
               -expr 'a*step(or(b,c))' -prefix ${usrPath}/anatSeg/MPRAGE_brain.nii.gz


 ## 5. T1->STANDARD
    ## Initial linear registrationc
echo --------------------------------------
echo !!!! PREPROCESSING T1 TO STANDARD!!!!
echo --------------------------------------

    anat_reg_dir=$usrPath/anatReg

       cp ${usrPath}/anatSeg/MPRAGE_brain.nii.gz ${usrPath}/anatReg/MPRAGE_brain.nii.gz
        #cp ${anat_dir}/${anat}_RPI.nii.gz ${anat_reg_dir}/highres_head.nii.gz
        cp ${standard_brain} ${anat_reg_dir}/standard.nii.gz

    echo "${subject}: Registering highres to standard "
    echo "(INITIAL LINEAR REGISTRATION)"
    #if [ -f ${anat_reg_dir}/highres2standard.nii.gz ]; then
    #    echo "Linear highres to standard already complete, skipping"
    #else
        flirt \
        -ref ${standard_brain} \
        -in ${usrPath}/anatSeg/MPRAGE_brain.nii.gz \
        -out ${usrPath}/anatReg/MPRAGE2standard \
        -omat ${usrPath}/anatReg/MPRAGE2standard.mat \
        -cost corratio -searchcost corratio -dof 12 \
        -interp trilinear
        ## Create mat file for conversion from standard to high res
        convert_xfm -inverse \
            -omat ${usrPath}/anatReg/standard2MPRAGE.mat \
            ${usrPath}/anatReg/MPRAGE2standard.mat
    #fi

    #if [ -f ${anat_reg_dir}/highres2standard_NL.nii.gz ]; then
        #    echo "Nonlinear highres to standard already complete, skipping"
    #else
cp ${outputPath}/MPRAGE.nii.gz ${usrPath}/anatOrig
        echo "${subject}: Registering highres to standard "
        echo "(NONLINEAR REGISTRATION)"
        fnirt --in=${usrPath}/anatOrig/MPRAGE.nii.gz \
                --aff=${usrPath}/anatReg/MPRAGE2standard.mat \
                --cout=${usrPath}/anatReg/MPRAGE2standard_warp \
                --iout=${usrPath}/anatReg/MPRAGE2standard_NL \
                --jout=${usrPath}/anatReg/MPRAGE2standard_jac \
                --ref=${standard_brain} \
                --refmask=${FSLDIR}/data/standard/MNI152_T1_${standard_res}_brain_mask_dil.nii.gz \
            --warpres=10,10,10

    ## rename outputs for XNAT reconstruction upload 
echo --------------------------------------
echo !!!! PREPARING RESULTS for XNAT UPLOAD!!!!
echo --------------------------------------
#__nat__reg__MPRAGE_seg8__all__0__v1.mat
cp ${usrPath}/anatOrig/MPRAGE_seg8.mat ${usrPath}/Reconstructions/$3__nat__reg__MPRAGE_seg8__all__0__v2.mat
#__nat__result__MPRAGE__all__0__v1.nii.gz
cp ${usrPath}/anatOrig/MPRAGE.nii.gz ${usrPath}/Reconstructions/$3__nat__result__MPRAGE__all__0__v2.nii.gz
#__nat__result__reg_jacobian__all__0__v1.nii.gz
cp ${usrPath}/anatReg/MPRAGE2standard_jac.nii.gz ${usrPath}/Reconstructions/$3__nat__result__reg_jacobian__all__0__v2.nii.gz
#__mni__result__MPRAGE__all__0__v1.nii.gz
cp ${usrPath}/anatReg/MPRAGE2standard_NL.nii.gz ${usrPath}/Reconstructions/$3__mni__result__MPRAGE__all__0__v2.nii.gz
#__nat__reg__MPRAGE2Standard__all__0__v1.mat
cp ${usrPath}/anatReg/MPRAGE2standard.mat ${usrPath}/Reconstructions/$3__nat__reg__MPRAGE2Standard__all__0__v2.mat
#__mni__result__MPRAGE__brain__0__v1.nii.gz
cp ${usrPath}/anatReg/MPRAGE2standard.nii.gz  ${usrPath}/Reconstructions/$3__mni__result__MPRAGE__brain__0__v2.nii.gz
#__mni__result__MPRAGE_warp__all__0__v1.nii.gz
cp ${usrPath}/anatReg/MPRAGE2standard_warp.nii.gz ${usrPath}/Reconstructions/$3__mni__result__MPRAGE_warp__all__0__v2.nii.gz
#__nat__result__WM__mask__WM__0__v1.nii.gz
cp ${usrPath}/anatSeg/WMseg.nii.gz ${usrPath}/Reconstructions/$3__nat__result__WM__mask__WM__0__v2.nii.gz
#__nat__result__GM__mask__GM__0__v1.nii.gz
cp ${usrPath}/anatSeg/GMseg.nii.gz ${usrPath}/Reconstructions/$3__nat__result__GM__mask__GM__0__v2.nii.gz
#__nat__result__CSF__mask__CSF__0__v1.nii.gz
cp ${usrPath}/anatSeg/CSFseg.nii.gz ${usrPath}/Reconstructions/$3__nat__result__CSF__mask__CSF__0__v2.nii.gz
#__nat__result__MPRAGE__brain__0__v1.nii.gz
cp ${usrPath}/anatSeg/MPRAGE_brain.nii.gz ${usrPath}/Reconstructions/$3__nat__result__MPRAGE__brain__0__v2.nii.gz


        echo --------------------------------------------
        echo !!!! DONE: PREPROCESSING ANATOMICAL SCAN!!!!
        echo --------------------------------------------



#cd ${cwd}
