#!/usr/bin/env python3
"""Select 31 diagnostics by mapped command, without submitting any jobs.
Usage: python3 filter_quickplot.py MASTERLIST portrait.list landscape.list OUTPUT
Requires Python 3 standard library only. Output must not already exist.
"""
import sys, re, shlex
from pathlib import Path
PROFILE = [('PORTRAIT', 'grads -p -c run progz U DYN $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run progz T DYN $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run progz Q MOIST $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run progz RH2 MOIST $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run progz OMEGA DYN $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run progz QLTOT AGCM $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run progz QITOT AGCM $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run hcmp2 SLP DYN 1000 $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run hcmp2 U DYN 850 $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run hcmp2 U DYN 200 $EXPID $OUTPUT no_debug $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -NAME osr -EXPID $EXPID -EXPORT RSR:SOLAR -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -NAME osrcf -EXPID $EXPID -EXPORT RSC:SOLAR RSR:SOLAR -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT OLC:IRRAD OLR:IRRAD OSRCLR:SOLAR OSR:SOLAR -NAME toacf -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT OLR:IRRAD -NAME olr -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT OLC:IRRAD OLR:IRRAD -NAME olrcf -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -NAME nettoa -EXPID $EXPID -EXPORT RSR:SOLAR OLR:IRRAD -OBS RSR:SOLAR OLR:IRRAD -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot_2G -NAME TOTEXTTAU -EXPID $EXPID -EXPORT TOTEXTTAU:GOCART -ALT_EXPORT TOTEXTTAU:GOCART2G -MATH LOG -SEASON $SEASON -OUTPUT $OUTPUT -DEBUG no_debug'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT CN_PRCP:MOIST LS_PRCP:MOIST AN_PRCP:MOIST -OBS TPREC:MOIST -NAME precip -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SCALE 86400 -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT CN_PRCP:MOIST AN_PRCP:MOIST -OBS CN_PRCP:MOIST -NAME precipcn -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SCALE 86400 -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT LS_PRCP:MOIST -OBS LS_PRCP:MOIST -NAME precipls -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SCALE 86400 -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT TQL:AGCM -OBS LWP:MOIST -NAME lwp -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT TQV:AGCM -NAME tpw -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT TQI:AGCM -NAME tqi -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT CLDLO:SOLAR -NAME cldlo -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT CLDMD:SOLAR -NAME cldmd -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT CLDHI:SOLAR -NAME cldhi -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -SEASON $SEASON'), ('PORTRAIT', 'grads -p -c run genplot -EXPORT CLDTT:SOLAR -NAME cldtt -EXPID $EXPID -OUTPUT $OUTPUT -DEBUG no_debug -RC ISCCP -SEASON $SEASON'), ('LANDSCAPE', 'grads -l -c run rad $EXPID $OUTPUT no_debug'), ('LANDSCAPE', 'grads -l -c run ps $EXPID $OUTPUT no_debug'), ('LANDSCAPE', 'grads -l -c run pme $EXPID $OUTPUT no_debug'), ('LANDSCAPE', 'grads -l -c run tpw $EXPID $OUTPUT no_debug')]

def signature(s):
    return ' '.join(t.split('/')[-1] if t.startswith('/') else t for t in s.split())

def main():
    if len(sys.argv)!=5:
        raise ValueError(__doc__)
    master,portrait,landscape,out=map(Path,sys.argv[1:])
    audit=Path(str(out)+'.mapping.txt')
    if out.exists() or audit.exists():
        raise ValueError('Output or audit already exists; choose a new output name.')
    available={}
    for kind,path in [('PORTRAIT',portrait),('LANDSCAPE',landscape)]:
        for line in path.read_text().splitlines():
            m=re.match(r'if \( plot == (\S+) \) (.*)',line)
            if m:
                available.setdefault((kind,signature(m[2])),[]).append((m[1],line))
    selected={}
    for key in PROFILE:
        matches=available.get(key,[])
        if len(matches)!=1:
            raise ValueError('Expected exactly one mapping for '+repr(key)+'; found '+str(len(matches)))
        ident,line=matches[0]
        selected[ident]=line
    result=[]; seen=set(); total=0
    for line in master.read_text().splitlines():
        if not line.strip(): continue
        total+=1
        args=shlex.split(line)
        if args.count('-plots')!=1:
            raise ValueError('Expected one -plots argument per command.')
        ident=args[args.index('-plots')+1]
        if ident not in selected: continue
        if ident in seen: raise ValueError('Repeated selected task '+ident+'; filter one diagnostic period at a time.')
        if '-cmpexp_only' in args or '-cmpops_only' in args:
            raise ValueError('Comparison-only options change numbering; not supported by this profile.')
        if args.count('-type')!=1 or args[args.index('-type')+1]!=('P' if ident.startswith('PORTRAIT') else 'L'):
            raise ValueError('Orientation mismatch: '+ident)
        if args.count('-taylor')>1: raise ValueError('Repeated -taylor option')
        if '-taylor' in args: args[args.index('-taylor')+1]='TRUE'
        else: args+=['-taylor','TRUE']
        result.append(' '.join(shlex.quote(a) for a in args))
        seen.add(ident)
    if seen!=set(selected): raise ValueError('Selected tasks missing from MASTERLIST: '+repr(set(selected)-seen))
    with out.open('x') as f: f.write('\n'.join(result)+'\n')
    with audit.open('x') as f: f.write('\n'.join(selected[k] for k in selected)+'\n')
    print(str(total)+' input tasks -> '+str(len(result))+' selected tasks.')
    print('Taylor numbering preserved with -taylor TRUE; no Taylor tasks selected.')
    print('No jobs submitted. Review '+str(audit))

if __name__=='__main__':
    try: main()
    except (ValueError,IndexError,OSError) as e:
        sys.exit('ERROR: '+str(e))
