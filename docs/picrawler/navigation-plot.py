"""Plot recorded physical trajectories and command-only estimates; observer use.

Requires matplotlib in the analysis environment, not the robot runtime. This
reads saved data only and is not an HTML/browser layout acceptance.
"""
import argparse
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


def plot(directory,output):
    directory=Path(directory)
    report=json.load(open(directory/'results.json'))
    first_seed=min(r['case']['seed'] for r in report['cases'])
    selected=[r for r in report['cases'] if r['case']['seed']==first_seed and r['case']['policy']=='active' and r.get('variant','visual')=='visual']
    fig,axes=plt.subplots(2,3,figsize=(13,8),sharex=True,sharey=True)
    for ax,row in zip(axes.flat,selected):
        path=directory/(row['id']+'.html')
        payload=json.loads(re.search(r'<script id="replay-data" type="application/json">(.*?)</script>',path.read_text(),re.S)[1])
        frames=payload['frames'];meta=payload['metadata'];start=frames[0]['pose'];true=np.array([[f['pose']['x_m'],f['pose']['y_m']] for f in frames])
        estimates=[]
        co,si=np.cos(start['yaw_rad']),np.sin(start['yaw_rad'])
        for frame in frames:
            p=frame.get('navigation',{}).get('estimated_position')
            if p is not None:estimates.append([start['x_m']+co*p[0]-si*p[1],start['y_m']+si*p[0]+co*p[1]])
        for box in meta['world']['obstacles']:
            ax.add_patch(Rectangle((box['x_min'],box['y_min']),box['x_max']-box['x_min'],box['y_max']-box['y_min'],color=np.array(box['color'])/255,alpha=.65))
        ax.axvline(.35,color='#687484',ls=':',lw=1.5,label='Evaluatorziel x=0,35 m')
        ax.plot(true[:,0],true[:,1],color='#007f8b',lw=2,label='MuJoCo-Pose (nur Auswertung)')
        if estimates:
            estimate=np.asarray(estimates);ax.plot(estimate[:,0],estimate[:,1],color='#b87800',lw=1.5,ls='--',label='Befehlsschätzung, keine Odometrie')
        ax.scatter(*true[0],color='#25394a',s=20,zorder=4);ax.scatter(*true[-1],color='#007f8b',s=30,zorder=4)
        ax.set_title(f"{row['case']['family']} / {row['case']['sensors']}\n{row['outcome']}, {row['steps']} Entscheidungen, Kontakte {row['contact_ticks']}",fontsize=10)
        ax.set_xlim(-.8,.7);ax.set_ylim(-.7,.65);ax.set_aspect('equal');ax.grid(alpha=.18);ax.set_xlabel('x [m]');ax.set_ylabel('y [m]')
    handles,labels=axes.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,fontsize=9)
    fig.suptitle('Unabhängige Modellprüfung: tatsächlicher Weg und sensorbeschränkte Bewegungsschätzung',fontsize=13,y=.98)
    fig.text(.5,.935,f'Seed {first_seed} · Punkte aus aufgezeichneten Frames · Schätzung bekommt weder Pose noch Zielgrenze',ha='center',fontsize=9,color='#435367')
    fig.text(.5,.91,'Linien: Körpermitte, keine Beinhülle. Kontakte stammen aus der vollständigen Tickauswertung.',ha='center',fontsize=8,color='#657080')
    fig.subplots_adjust(top=.83,bottom=.12,wspace=.18,hspace=.40);fig.savefig(output,dpi=180);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--output',required=True)
    args=parser.parse_args();plot(args.directory,args.output)
