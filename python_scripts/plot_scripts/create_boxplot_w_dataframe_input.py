# Functions for creating factorplots, countplots, simple boxplots and countsplots (simple in the sense
# that they are not factorplots, hence less complex).

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns


def createfactorplot(data_csv,x_label,y_label,hue_label,col_label,plotname,plottitle,setlimaxis):
    sns.set(style="whitegrid", color_codes=True)
    
    snsplot = sns.factorplot(x=x_label, y=y_label, hue=hue_label, col=col_label, data=data_csv, 
                            kind="box", size=4, aspect=.5,legend=False)
    
    snsplot.axes[0][0].legend()
    if setlimaxis == 'True':
        plt.ylim([-0.5,0.5])
        plt.autoscale(False)

    plt.suptitle(plottitle,y=1.08)
    snsplot.savefig(plotname)
    plt.clf()

 
def createfactorplot_countplot(data_csv,x_label,y_label,hue_label,col_label,plotname,plottitle):
    sns.set(style="whitegrid", color_codes=True)
    
    snsplot = sns.factorplot(x=x_label, y=y_label, hue=hue_label, col=col_label, data=data_csv, 
                            kind="count", size=4, aspect=.5,legend=False);
    snsplot.axes[0][0].legend()
    plt.suptitle(plottitle,y=1.08)
    snsplot.savefig(plotname)
    plt.clf()

def create_simpleboxplot(data_csv,x_label,y_label,hue_label,plotname,plottitle):
    sns.set(style="whitegrid", color_codes=True)
    snsplot = sns.boxplot(x=x_label,y=y_label,hue=hue_label,data=data_csv)
    plt.suptitle(plottitle,y=1.08)
    fig = plt.gcf()
    fig.savefig(plotname)
    plt.clf()

def create_simplecountplot(data_csv,x_label,hue_label,plotname,plottitle):
    sns.set(style="whitegrid", color_codes=True)
    sns.countplot(x=x_label,hue=hue_label,data=data_csv)
    plt.suptitle(plottitle,y=1.08)
    fig = plt.gcf()
    fig.savefig(plotname)
    plt.clf()
