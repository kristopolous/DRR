#!/bin/sh

# This script uses pandoc to generate the markdown and the stylesheet for the
# technical article into an about.html file.  It should be run when the markdown
# changes

pandoc about.md -T "About Indycast" -H style.css.html > ../about.html
