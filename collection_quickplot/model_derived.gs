* Derived 2-D model diagnostics using the formulas in GEOS QuickPlot.
* Arguments: NAME EXPID OUTPUT SEASON
* precip: CN_PRCP + LS_PRCP + AN_PRCP, converted to mm/day
* olrcf:  OLC - OLR
* osrcf:  RSC - RSR
* toacf:  OLC - OLR + OSRCLR - OSR
function model_derived(args)
name = subwrd(args,1)
expid = subwrd(args,2)
output = subwrd(args,3)
season = subwrd(args,4)

'reinit'
'set display color white'
'set grads off'
'set mpdset hires'
'set mproj latlon'
'set map 1 1 4'
'set grid off'
fac = 1
if (name = 'precip')
  e1 = 'CN_PRCP' ; g1 = 'MOIST'
  e2 = 'LS_PRCP' ; g2 = 'MOIST'
  e3 = 'AN_PRCP' ; g3 = 'MOIST'
  n = 3
  fac = 86400
else
  if (name = 'olrcf' | name = 'toacf')
    e1 = 'OLC' ; g1 = 'IRRAD'
    e2 = 'OLR' ; g2 = 'IRRAD'
  else
    e1 = 'RSC' ; g1 = 'SOLAR'
    e2 = 'RSR' ; g2 = 'SOLAR'
  endif
  n = 2
  if (name = 'toacf')
    e3 = 'OSRCLR' ; g3 = 'SOLAR'
    e4 = 'OSR' ; g4 = 'SOLAR'
    n = 4
  endif
endif

j = 1
while (j <= n)
  if (j = 1)
    ex = e1 ; gc = g1
  endif
  if (j = 2)
    ex = e2 ; gc = g2
  endif
  if (j = 3)
    ex = e3 ; gc = g3
  endif
  if (j = 4)
    ex = e4 ; gc = g4
  endif
  'run getvar 'ex' 'gc
  nm.j = subwrd(result,1)
  ff.j = subwrd(result,2)
  sc.j = subwrd(result,3)
  if (ff.j = 'NULL')
    say 'ERROR: missing model input for 'name': 'ex':'gc
    return
  endif
  j = j + 1
endwhile

'set dfile 'ff.1
'set z 1'
'set lon 0 360'
'set lat -90 90'
'setdates'
'run getenv "BEGDATE"'
begdate = result
'run getenv "ENDDATE"'
enddate = result
'set time 'begdate' 'enddate
'getinfo tmin'
tmin = result
'getinfo tmax'
tmax = result
if (tmin < 1 | tmax < tmin)
  say 'ERROR: invalid time window for derived diagnostic'
  return
endif

j = 1
while (j <= n)
  'set dfile 'ff.j
  'set z 1'
  'set lon 0 360'
  'set lat -90 90'
  'define f'j' = ave('nm.j'*'sc.j',t='tmin',t='tmax')'
  j = j + 1
endwhile
'set t 'tmin
if (name = 'precip')
  'define derived = (f1 + f2 + f3)*'fac
endif
if (name = 'olrcf')
  'define derived = f1 - f2'
endif
if (name = 'osrcf')
  'define derived = f1 - f2'
endif
if (name = 'toacf')
  'define derived = f1 - f2 + f3 - f4'
endif
'clear'
'set gxout shaded'
'set parea 0.85 7.65 2.15 8.7'
'd derived'
'run cbarn'
'draw title 'expid' 'name' 'season' mean'
filename = output'/'name'_'season'.png'
'printim 'filename' white x1000 y850'
say 'Finished Creating: 'filename
return
