* GEOS-style model-only map. Avoid hcmp2's verification requirement and
* genplot's OpenGrADS 2.0.1 sdfwrite time-coordinate failure.
* Args: EXPORT GC LEVEL EXPID OUTPUT SEASON
function collection_map(args)
EXPORT = subwrd(args,1)
GC     = subwrd(args,2)
level  = subwrd(args,3)
expid  = subwrd(args,4)
output = subwrd(args,5)
season = subwrd(args,6)

'reinit'
'set display color white'
'set grads off'
'set mpdset hires'
'set mproj scaled'
'set frame on'
'set xlopts 1 3 .11'
'set ylopts 1 3 .11'
'run getvar 'EXPORT' 'GC
qname = subwrd(result,1)
qfile = subwrd(result,2)
scale = subwrd(result,3)
if (qfile = 'NULL')
  say 'ERROR: model export not found: 'EXPORT':'GC
  return
endif
* Only the unit-conversion factor is needed here; layout and colors are
* applied by the shared renderer using GEOS's original plot.rc.
'run getenv "GEOSUTIL"'
geosutil = result
plotrc = geosutil'/plots/grads_util/plot.rc'
if (level != 'surface')
  'getresource 'plotrc' 'EXPORT'_'GC'_'level'_FACTOR'
else
  'getresource 'plotrc' 'EXPORT'_'GC'_FACTOR'
endif
if (result = 'NULL')
  'getresource 'plotrc' 'EXPORT'_'GC'_FACTOR'
endif
fact = result
if (fact = 'NULL')
  fact = 1
endif

'set dfile 'qfile
if (level != 'surface')
  'set lev 'level
endif
'set lon 0 360'
'set lat -90 90'
'setdates'
'run getenv "BEGDATE"'
begdate = result
'run getenv "ENDDATE"'
enddate = result
say 'Model-only 'EXPORT':'GC' at 'level' season='season
say 'Dates: 'begdate' to 'enddate
* GrADS ave() requires numeric t indices, not formatted calendar dates.
* Set the valid time range first, then query its numeric endpoints.
'set time 'begdate' 'enddate
'getinfo tmin'
tmin = result
'getinfo tmax'
tmax = result
say 'Averaging time indices: 'tmin' to 'tmax
if (tmin < 1 | tmax < tmin)
  say 'ERROR: invalid time indices for model averaging'
  return
endif
* Use numeric indices for the time dimension and select a fixed time
* before drawing the time-averaged two-dimensional field.
'define qmean = ave('qname'*'scale'*'fact',t='tmin',t='tmax')'
'set t 'tmin
* Plotting is delegated to the shared GEOS-style renderer.
'run getenv "COLLECTION_QUICKPLOT_DIR"'
styledir = result
'run 'styledir'/geos_model_style.gs qmean 'EXPORT' 'GC' 'level' 'expid' 'season' map 'output
return
