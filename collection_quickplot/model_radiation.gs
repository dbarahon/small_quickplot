* Model-only four-panel TOA zonal radiation diagnostic.
* Uses the GEOS OLR/OLC (IRRAD) and RSR/RSC (SOLAR) exports.
* Arguments: EXPID OUTPUT SEASON
function collection_radiation(args)
expid = subwrd(args,1)
output = subwrd(args,2)
season = subwrd(args,3)

'reinit'
'set display color white'
'set grads off'

'run getvar OLR IRRAD'
n1 = subwrd(result,1)
f1 = subwrd(result,2)
s1 = subwrd(result,3)
'run getvar OLC IRRAD'
n2 = subwrd(result,1)
f2 = subwrd(result,2)
s2 = subwrd(result,3)
'run getvar RSR SOLAR'
n3 = subwrd(result,1)
f3 = subwrd(result,2)
s3 = subwrd(result,3)
'run getvar RSC SOLAR'
n4 = subwrd(result,1)
f4 = subwrd(result,2)
s4 = subwrd(result,3)

if (f1 = 'NULL' | f2 = 'NULL' | f3 = 'NULL' | f4 = 'NULL')
  say 'ERROR: TOA radiation diagnostic requires OLR OLC RSR RSC'
  return
endif

'set dfile 'f1
'set lon 0 360'
'set lat -90 90'
'set z 1'
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
  say 'ERROR: invalid dates for TOA radiation diagnostic'
  return
endif

'set dfile 'f1
'set z 1'
'set lon 0 360'
'set lat -90 90'
'define rad1 = ave('n1'*'s1',t='tmin',t='tmax')'
'set dfile 'f2
'set z 1'
'define rad2 = ave('n2'*'s2',t='tmin',t='tmax')'
'set dfile 'f3
'set z 1'
'define rad3 = ave('n3'*'s3',t='tmin',t='tmax')'
'set dfile 'f4
'set z 1'
'define rad4 = ave('n4'*'s4',t='tmin',t='tmax')'

'set t 'tmin
'set lon 0 360'
'define zw1 = ave(rad1,lon=0,lon=360,-b)'
'define zw2 = ave(rad2,lon=0,lon=360,-b)'
'define zw3 = ave(rad3,lon=0,lon=360,-b)'
'define zw4 = ave(rad4,lon=0,lon=360,-b)'
'set lon 0'
'set gxout line'
'set grid on'
'set cmark 0'
'set cthick 5'

* Panel 1: outgoing longwave (all-sky and clear-sky)
'set vpage 0 4.25 5.5 10'
'set ccolor 4'
'set cstyle 1'
'd zw1'
'set ccolor 1'
'set cstyle 3'
'd zw2'
'draw title Outgoing longwave (all/clear)'

* Panel 2: LW cloud radiative effect, clear minus all
'set vpage 4.25 8.5 5.5 10'
'set ccolor 4'
'set cstyle 1'
'd zw2-zw1'
'draw title LW cloud radiative effect'

* Panel 3: net shortwave radiation
'set vpage 0 4.25 1 5.5'
'set ccolor 4'
'set cstyle 1'
'd zw3'
'set ccolor 1'
'set cstyle 3'
'd zw4'
'draw title Net shortwave (all/clear)'

* Panel 4: SW cloud radiative effect, all minus clear
'set vpage 4.25 8.5 1 5.5'
'set ccolor 4'
'set cstyle 1'
'd zw3-zw4'
'draw title SW cloud radiative effect'
'set vpage off'
'draw title 'expid' TOA zonal mean radiation 'season' (W/m2)'
filename = output'/TOA_radz_model_'season'.png'
'printim 'filename' white x1100 y900
say 'Finished Creating: 'filename
return
