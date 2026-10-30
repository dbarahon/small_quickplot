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
if (mode = 'section')
  'set lev 1000 1'
  'run getenv "COLLECTION_QUICKPLOT_DIR"'
  styledir = result
  'run 'styledir'/geos_model_style.gs qzonal 'EXPORT' 'GC' zonal 'expid' 'season' section 'output
else
  * Optional 2D latitude profiles use the GEOS line presentation.
  'clear'
  'set display color white'
  'set vpage off'
  'set parea off'
  'set frame on'
  'set grid on'
  'set xlopts 1 3 .11'
  'set ylopts 1 3 .11'
  'rgbset'
  'set vpage 0 8.5 0 11'
  'set parea 1.5 7.0 4.2 7.0'
  'set gxout line'
  'set ccolor 4'
  'set cthick 5'
  'd qzonal'
  'set vpage off'
  'set string 1 c 6'
  'set strsiz .13'
  'draw string 4.25 10.75 'EXPORT':'GC' Zonal Mean'
  'set strsiz .10'
  'draw string 4.25 10.48 'expid'  'season'  (Model Only)'
  filename = output'/'EXPORT'_'GC'_line_'season'.png'
  'printim 'filename' white x1000 y1100'
  say 'Finished Creating: 'filename
endif
return
