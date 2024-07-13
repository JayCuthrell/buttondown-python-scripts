# buttondown-python-scripts
Simple python scripts for using the Buttondown API

Each python script was based on [examples from Buttondown](https://docs.buttondown.email/api-emails-introduction) and enrichment using Google Gemini (with significant errors) and tested in a virtual environment on OS Version: macOS 14.5 build 23F79 using omz and Python 3.12.4 with the following pip3 list

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
- python-dotenv      1.0.1
- requests           2.32.3
- setuptools         70.3.0
- urllib3            2.2.2

## Start here

If you are comfortable with python and API use, [start here](https://docs.buttondown.email/api-introduction).

If you are not, [start here](https://www.studytonight.com/post/python-virtual-environment-setup-on-mac-osx-easiest-way).

## Scripts

This list will grow as my needs evolve for [Hot Fudge Daily](https://hot.fudge.org) newsletter grow and my API automation comfort increases.

- get_email_list.py - pulls basic information that is readable in a terminal 
- get_digest_6_days.py - gathers the format in a terminal that can be piped into a buffer i.e. ```python3 get_digest_6_days.py | pbcopy```
