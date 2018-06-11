#!/usr/bin/python

# Example usage of functions createboxplot,createboxplot_countplot, create_simpleboxplot, create_simplecountplot

from create_boxplot_dataframe_input import createboxplot,createboxplot_countplot, create_simpleboxplot, create_simplecountplot
import pandas as pd

path_file = '/scratch/mhansson/csv_files/';

#######################################
#######################################
# Example content csv file:
#
#id,Genotype,SNP,scanner,asymmetry_FU
#1,2,rs3815148,dif,0.02141321
#2,2,rs3815148,dif,-0.064611675
#3,1,rs3815148,dif,0.047854741
#4,2,rs3815148,dif,0.16526637
#6,2,rs3815148,dif,-0.00025044
#12,2,rs3815148,dif,-0.105840817
#13,1,rs3815148,dif,0.221398279
#16,2,rs3815148,dif,-0.162956936
#18,2,rs3815148,dif,-0.119347004
#21,2,rs3815148,dif,0.033643161
#:
#:
#:
#394,1,rs78110303,same,-0.090301847
#397,1,rs78110303,same,0.106707108
#399,2,rs78110303,same,-0.077009825
#400,1,rs78110303,same,-0.091325836
#402,1,rs78110303,same,-0.120842006
#403,0,rs78110303,same,-0.042786666
#406,2,rs78110303,same,-0.155165159
#407,1,rs78110303,same,0.004896565
########################################
########################################

SNP = ['rs12982744','rs3815148','rs78110303','rs8044769'] 
outputdir = '/scratch/mhansson/'

basename = ['atrophy_LEFT','atrophy_RIGHT',
            'asymmetry_baseline','asymmetry_FU',
            'left_vol_baseline','left_vol_FU',
            'right_vol_baseline','right_vol_FU']

modify_axes = ['True','True',
               'True','True',
               'False','False',
               'False','False']


for x in range(0,len(basename)):
     csv_file = path_file +  basename[x] + '_OA.csv'
     df = pd.read_csv(csv_file)
     
    data_same = df[df['scanner'] == 'same']
    createboxplot(data_same,'OA_status',basename[x],'Genotype','SNP',outputdir + basename[x]+'_mensicus_OAstatus_samescanner.png','meniscus same scanner',modify_axes[x])
    createboxplot_countplot(data_same,'OA_status',None,'Genotype','SNP',outputdir + basename[x]+'_countplot_meniscus_OAstatus_samescanner.png',basename[x] + '- meniscus same scanner')
    data_dif = df[df['scanner'] == 'dif']
    createboxplot(data_dif,'OA_status',basename[x],'Genotype','SNP',outputdir + basename[x]+'_meniscus_OAstatus_difscanner.png','meniscus different scanner',modify_axes[x])
    createboxplot_countplot(data_dif,'OA_status',None,'Genotype','SNP',outputdir + basename[x]+'_countplot_meniscus_OAstatus_difscanner.png',basename[x] + '- meniscus different scanner')
      
#########################################################
    

for x in range(0,len(basename)):
    csv_file = path_file +  basename[x] + '.csv'
    print(csv_file)
    df = pd.read_csv(csv_file)
    create_simpleboxplot(df,"SNP",basename[x],'Genotype',outputdir + basename[x]+'_boxplot_meniscus.png',' - meniscus') 
    create_simplecountplot(df,"SNP",'Genotype',outputdir + basename[x]+'_countplot_meniscus.png',' - meniscus')

