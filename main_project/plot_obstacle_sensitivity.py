"""Summarize tested settings without treating a range as a confidence interval."""
import hashlib
import json
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY


def main():
    folder=DIRECTORY/'obstacle_sensitivity'
    report=json.loads((folder/'results.json').read_text())
    source=DIRECTORY/'fixed_boundary_scenario.json'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=report['source_sha256']:
        raise ValueError('Sensitivity source has changed; rerun the experiment')
    nominal=json.loads(source.read_text());groups=defaultdict(lambda:defaultdict(list))
    for row in report['comparisons']:
        key=(row['earlier'],row['later'])
        for name in ('paired_range_m','independent_range_m'):
            if row['complete'] and row[name] is not None:groups[key][name].extend(row[name])
    for experiment in nominal['experiments']:
        for row in experiment['comparisons']:
            if row['status']=='distance_comparison_computed':
                groups[(row['earlier_date'],row['later_date'])]['nominal'].append(row['distance_change_m'])
    fig,ax=plt.subplots(figsize=(11,6),layout='constrained');labels=[]
    styles=[('nominal',-.2,'#355f9d','Original settings'),('paired_range_m',0,'#168575','Same boundary offset on both dates'),('independent_range_m',.2,'#c66b18','Offsets can differ between dates')]
    for i,(key,values) in enumerate(sorted(groups.items())):
        labels.append(' → '.join(key))
        for name,shift,color,label in styles:
            numbers=values[name]
            if numbers:
                ax.plot([min(numbers),max(numbers)],[i+shift]*2,color=color,lw=5,solid_capstyle='round',label=label if i==0 else None)
    ax.axvline(0,color='#333',lw=1,ls='--');ax.set_yticks(range(len(labels)),labels)
    ax.set(xlabel='Later minus earlier model route length (m)',title='Candidate-boundary sensitivity across tested grid/policy settings\n±40 / ±80 m mask changes; ranges are NOT confidence intervals')
    ax.legend(loc='upper left',fontsize=8);ax.grid(axis='x',alpha=.2);ax.invert_yaxis()
    fig.savefig(folder/'comparison.png',dpi=160);plt.close(fig)
    print('Saved',folder/'comparison.png')

if __name__=='__main__':main()
