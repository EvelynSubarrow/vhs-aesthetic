# aesthetic.py
This applies an approximation of composite video artifacts to still images, shifting the chroma upwards
(to emulate an overly broad carrier), introducing noise, and overlaying luma ghosting.

## Usage
`aesthetic.py [-h] [-t TEXT] [-s TEXT_SIZE] file outfile`

* `-t TEXT, --text TEXT` Text to overlay onto image, details below
* `-s TEXT_SIZE, --text-size TEXT_SIZE` Size of text, in pixels (also affects positioning)

### Text formatting
Text coordinates reference character cells, and start at 0,0 (in the left top). Text can be positioned by comma delimited
number pairs in square brackets, conforming to the following:

* If unadorned, the coordinate is absolute
* If prefixed by a sign (`-` or `+`), the coordinate is an offset relative to the previous corresponding co-ordinate.
* If expressed as a fraction (`0.nn` or `.n`), the coordinate is a proportion of the corresponding cell dimension.

To hopefully make this a little less confusing, assuming cell dimensions of 10x10, `[2,3]Hello[+2,+1]World[0.6,0.3]foo[0.1,+2]bar` would yield:
```


Hello
  World

  foo

 bar



```
## Licence
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode)

## Dependencies
* [Pillow](https://pypi.org/project/Pillow/)
* [numpy](https://pypi.org/project/numpy/)
