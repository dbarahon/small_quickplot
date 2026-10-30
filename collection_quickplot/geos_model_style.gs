* Shared GEOS-style single-panel renderer, based on hcmp/hplt and zcmp/zplt.
* Inputs: FIELD EXPORT GC LEVEL EXPID SEASON MODE OUTPUT
* FIELD must already be a defined 2D GrADS variable at fixed time.
* MODE: map, section, or derived.
function geos_model_style(args)
field = subwrd(args,1)
export = subwrd(args,2)
gc = subwrd(args,3)
level = subwrd(args,4)
expid = subwrd(args,5)
season = subwrd(args,6)
mode = subwrd(args,7)
output = subwrd(args,8)

'run getenv "GEOSUTIL"'
geosutil = result
if (mode = 'derived')
  plotrc = geosutil'/plots/'export'/plot.rc'
  base = ''
  'getresource 'plotrc' CLEVS'
  clevs = result
  'getresource 'plotrc' CCOLS'
  ccols = result
  'getresource 'plotrc' TITLE'
  title = result
  'getresource 'plotrc' CINT'
  cint = result
  'getresource 'plotrc' CBSCALE'
  cbscale = result
  'getresource 'plotrc' CLAB'
  clab = result
else
  plotrc = geosutil'/plots/grads_util/plot.rc'
  base = export'_'gc
  if (mode = 'section')
    'getresource 'plotrc' 'base'_Z_CLEVS'
    clevs = result
    'getresource 'plotrc' 'base'_Z_CCOLS'
    ccols = result
    if (clevs = 'NULL')
      'getresource 'plotrc' 'base'_CLEVS'
      clevs = result
    endif
    if (ccols = 'NULL')
      'getresource 'plotrc' 'base'_CCOLS'
      ccols = result
    endif
  else
    'getresource 'plotrc' 'base'_'level'_CVALS'
    if (result = 'NULL')
      'getresource 'plotrc' 'base'_CVALS'
    endif
    clevs = result
    'getresource 'plotrc' 'base'_'level'_CCOLS'
    if (result = 'NULL')
      'getresource 'plotrc' 'base'_CCOLS'
    endif
    ccols = result
  endif
  'getresource 'plotrc' 'base'_TITLE'
  title = result
  'getresource 'plotrc' 'base'_'level'_CINT'
  if (result = 'NULL')
    'getresource 'plotrc' 'base'_CINT'
  endif
  cint = result
  'getresource 'plotrc' 'base'_'level'_CBSCALE'
  if (result = 'NULL')
    'getresource 'plotrc' 'base'_CBSCALE'
  endif
  cbscale = result
  'getresource 'plotrc' 'base'_'level'_CLAB'
  if (result = 'NULL')
    'getresource 'plotrc' 'base'_CLAB'
  endif
  clab = result
endif
if (title = 'NULL')
  title = export':'gc
endif
* Many collection-specific exports are not in the GEOS plot.rc catalog.
* Use a physically meaningful display multiplier for CCN number fields.
displayfield = field
multiplier = ''
if (mode = 'section' & substr(export,1,3) = 'CCN')
  'define ccn_display = 'field'*1e-10'
  displayfield = 'ccn_display'
  multiplier = '(x10**10)'
  if (clevs = 'NULL')
    clevs = '0.0025 0.005 0.0075 0.01 0.0125 0.015 0.0175 0.02 0.0225 0.025 0.0275 0.03 0.035 0.04 0.05'
  endif
  if (ccols = 'NULL')
    ccols = '0 49 47 45 44 36 34 32 31 21 22 23 24 25 26 27'
  endif
endif
if (cbscale = 'NULL')
  cbscale = 0.8
endif
if (clab = 'NULL')
  clab = 'on'
endif

* Standard GEOS hplt/zplt graphics and portrait geometry.
'clear'
'set display color white'
'set vpage off'
'set parea off'
'set frame on'
'set grid off'
'set xlopts 1 3 .11'
'set ylopts 1 3 .11'
'set grads off'
'rgbset'
'set rgb 84 204 204 204'
'set rgb 85 137 137 137'
'set vpage 0 8.5 0 11'
if (mode = 'section')
  'set parea 1.05 7.5 1.55 9.85'
  'set grid on'
else
  'set parea 1.15 7.35 2.9 8.85'
endif
if (mode = 'section')
  'set mproj off'
  'set zlog off'
  'set gxout shaded'
else
  'set mproj scaled'
  'set gxout shaded'
endif
if (clevs != 'NULL')
  'set clevs 'clevs
endif
if (ccols != 'NULL')
  'set ccols 'ccols
endif
'set clab 'clab
'd 'displayfield
if (clevs != 'NULL')
  'set gxout contour'
  'set ccolor 1'
  'set clevs 'clevs
  'd 'field
  'set gxout shaded'
else
  if (cint != 'NULL')
    'set gxout contour'
    'set ccolor 1'
    'set cint 'cint
    'd 'field
    'set gxout shaded'
  endif
endif
if (mode = 'section')
  'draw ylab Pressure (hPa)'
  'set parea off'
  'cbarn -snum 0.65 -xmid 4.25 -ymid 0.98'
else
  'set parea off'
  'cbarn -snum 'cbscale' -xmid 4.25 -ymid 2.15'
endif

'set vpage off'
'set string 1 c 6'
'set strsiz .13'
if (mode = 'section')
  'draw string 4.25 10.68 'export':'gc'  'title'  'season'  'multiplier
else
  if (level = 'surface' | mode = 'derived')
    'draw string 4.25 10.75 'title
  else
    'draw string 4.25 10.75 'level'-hPa 'title
  endif
endif
'set strsiz .10'
'draw string 4.25 10.42 EXPID: 'expid'  'season'  (Model Only)'
'set string 1 l 4'
'set strsiz .075'
'draw string 0.25 0.23 EXPID: 'expid'  FIELD: 'export':'gc'  SEASON: 'season

filename = output'/'export'_'gc'_'level'_'season'.png'
'printim 'filename' white x1000 y1100'
say 'Finished Creating: 'filename
return
