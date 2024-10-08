# buttondown-python-scripts
Simple python scripts for using the Buttondown API

Each python script was based on [examples from Buttondown](https://docs.buttondown.email/api-emails-introduction) and enrichment using Google Gemini (with significant errors) and tested in a virtual environment on OS Version: macOS 14.5 build 23F79 using omz (fa583cfb) and Python 3.12.4 with the following pip3 list

- certifi            2024.7.4
- charset-normalizer 3.3.2
- colored            2.2.4
- data-printer       0.0.8
- dist-info          0.1.1
- idna               3.7
- Jinja2             3.1.4
- MarkupSafe         2.1.5
- pip                24.1.2
- pyproject          1.3.1
- python-dateutil    2.9.0.post0
- python-dotenv      1.0.1
- pytz               2024.1
- requests           2.32.3
- setuptools         70.3.0
- six                1.16.0
- urllib3            2.2.2
- DateTime           5.5
- zope.interface     6.4.post2

## Start here

If you are comfortable with python and API use, [start here](https://docs.buttondown.email/api-introduction).

If you are not, [start here](https://www.studytonight.com/post/python-virtual-environment-setup-on-mac-osx-easiest-way).

## Scripts

This list will grow as my needs evolve for [Hot Fudge Daily](https://hot.fudge.org) newsletter grow and my API automation comfort increases.

- get_list.py - pulls basic information that is readable in a terminal 
- get_digest.py - pulls recent posts to be piped into a buffer i.e. ```python3 get_digest.py | pbcopy```

## JupyterLab 

This list will grow as my newsletter analysis skils improve.

- Topics.ipynb - a quick analysis of markdown format blog posts for words and frequency from my blog post [Finding My Nich (2024)](https://fudge.org/archive/finding-my-niche) 
- stay tuned...
