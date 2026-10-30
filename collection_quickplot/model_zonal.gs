* Model-only zonal section or meridional line.
* Arguments: EXPORT GC MODE EXPID OUTPUT SEASON
function collection_zonal(args)
EXPORT = subwrd(args,1)
GC = subwrd(args,2)
mode = subwrd(args,3)
expid = subwrd(args,4)
output = subwrd(args,5)
season = subwrd(args,6)

'reinit'
'set display color white'
'set grads off'
'run getvar 'EXPORT' 'GC
qname = subwrd(result,1)
qfile = subwrd(result,2)
scale = subwrd(result,3)
if (qfile = 'NULL')
  say 'ERROR: model export not found: 'EXPORT':'GC
  return
endif

'set dfile 'qfile
'set lon 0 360'
'set lat -90 90'
if (mode = 'section')
  'set lev 1000 1'
else
  'set z 1'
endif
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
  say 'ERROR: invalid time indices for zonal averaging'
  return
endif
say 'Computing zonal mean for 'EXPORT':'GC' 'mode' time 'tmin' to 'tmax

* First average time with longitude and latitude spanning the full grid.
'define qtmean = ave('qname'*'scale',t='tmin',t='tmax')'
'set t 'tmin
* Longitude average. The -b flag uses bounds for zonal integration.
'define qzonal = ave(qtmean,lon=0,lon=360,-b)'
'set lon 0'
'clear'
'set grads off'
'set grid on'
if (mode = 'section')
  'set gxout shaded'
  'set zlog on'
  'set lev 1000 1'
  'd qzonal'
  'run cbarn'
  'draw title 'expid' 'EXPORT':'GC' zonal mean latitude-pressure 'season
else
  'set gxout line'
  'set ccolor 4'
  'set cthick 5'
  'd qzonal'
  'draw title 'expid' 'EXPORT':'GC' zonal mean latitude profile 'season
endif
filename = output'/'EXPORT'_'GC'_'mode'_'season'.png'
'printim 'filename' white x1000 y850'
say 'Finished Creating: 'filename
return
