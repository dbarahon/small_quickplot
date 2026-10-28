# Small QuickPlot

Reduce GEOS QuickPlot to a selected 31-task diagnostic profile before submission.

Full instructions are in [README.txt](README.txt). The included `MASTERLIST.small` is specific to JJA 2009; generate a new list for other periods.

```csh
python3 filter_quickplot.py MASTERLIST portrait.list landscape.list MASTERLIST.next
```

The filter submits no jobs. Static selection was verified against 6,422 input commands; HPC plotting has not been tested.
