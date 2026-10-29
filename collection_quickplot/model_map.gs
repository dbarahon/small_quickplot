* Standalone model-only map. Avoid hcmp2's verification requirement and
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
'set lon 0 360'
'set lat -90 90'

'run getvar 'EXPORT' 'GC
qname = subwrd(result,1)
qfile = subwrd(result,2)
scale = subwrd(result,3)
if (qfile = 'NULL')
  say 'ERROR: model export not found: 'EXPORT':'GC
  return
endif
'set dfile 'qfile
'set lev 'level
'set lon 0 360'
'set lat -90 90'
'setdates'
'run getenv "BEGDATE"'
begdate = result
'run getenv "ENDDATE"'
enddate = result
say 'Model-only 'EXPORT':'GC' at 'level' season='season
say 'Dates: 'begdate' to 'enddate
* Use seasonal's existing mean handling without NetCDF serialization.
'seasonal 'qname'*'scale' mod'
qseason = 'mod'season
* seasonal defines modjja/modann/etc using lower-case suffixes.
'lowercase 'qseason
qseason = result
'set gxout shaded'
'clear'
'd 'qseason
if (subwrd(result,1) = 'Syntax')
  say 'ERROR: unable to display 'qseason
  return
endif
'draw title 'expid' 'EXPORT':'GC' 'level' 'season
filename = output'/'EXPORT'_'GC'_'level'_'season'.png'
'printim 'filename' white'
say 'Finished Creating: 'filename
return
