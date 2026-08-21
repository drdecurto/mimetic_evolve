#!/usr/bin/env python3
from __future__ import annotations
import argparse, io, zipfile
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from scipy import linalg as la

PREFIX='mimetic_operator_discovery_results_v11/operators/'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output',type=Path,default=None)
    a=ap.parse_args(); root=a.repo_root.resolve()
    out=(a.output or root/'paper'/'scientific_reports'/'figure1_reference_spectra.png').resolve()
    run=root/'runs'/'v11_original_results.zip'
    fig,axes=plt.subplots(2,2,figsize=(14,10))
    with zipfile.ZipFile(run) as z:
        for ax,k in zip(axes.flat,(2,4,6,8)):
            with np.load(io.BytesIO(z.read(PREFIX+f'reference_mole_k{k}_m200.npz')),allow_pickle=False) as d:
                eig=la.eigvals((d['D']@d['G'])[1:-1,1:-1])
            ax.scatter(eig.real,eig.imag,s=16)
            ax.axhline(0,linewidth=1)
            ax.set_title(f'MOLE/Corbino-Castillo, order k={k}',fontsize=13)
            ax.set_xlabel(r'Re($\lambda$)'); ax.set_ylabel(r'Im($\lambda$)')
            ax.grid(True,alpha=.7)
            if k in (2,4):
                lim=max(0.05,float(np.max(np.abs(eig.imag)))*1.1)
                ax.set_ylim(-lim,lim)
    fig.suptitle('Dirichlet spectra at m=200',fontsize=15)
    fig.tight_layout(rect=(0,0,1,.97))
    out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out,dpi=150,bbox_inches='tight')
    plt.close(fig)
    print(out)
if __name__=='__main__': main()
