#!/bin/zsh
rm -rf my_env
python3 -m venv my_env
source my_env/bin/activate
pip3 install -U pip
pip3 install -U bs4
pip3 install -U setuptools
pip3 install -U requests
pip3 install -U python-dateutil
pip3 install -U datetime
pip3 install -U python-dotenv
pip3 install -U urllib3
pip3 install -U feedparser 
pip3 install -U python-frontmatter
pip3 install -U markdown
pip3 install -U markdownify
pip3 install -U pillow
pip3 install -U google-generativeai
pip3 list
