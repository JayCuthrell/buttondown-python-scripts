# buttondown-python-scripts
Simple python scripts for using the Buttondown API

Each python script was based on [examples from Buttondown](https://docs.buttondown.email/api-emails-introduction) and enrichment using Google Gemini (with significant errors) and tested in a virtual environment on OS Version: macOS 15.6.1 build 24G90 using omz and Python 3.13.7 with the following pip3 list

```
Package                      Version
---------------------------- -----------
annotated-types              0.7.0
beautifulsoup4               4.13.5
bs4                          0.0.2
cachetools                   5.5.2
certifi                      2025.8.3
charset-normalizer           3.4.3
DateTime                     5.5
feedparser                   6.0.11
google-ai-generativelanguage 0.6.15
google-api-core              2.25.1
google-api-python-client     2.181.0
google-auth                  2.40.3
google-auth-httplib2         0.2.0
google-generativeai          0.8.5
googleapis-common-protos     1.70.0
grpcio                       1.74.0
grpcio-status                1.71.2
httplib2                     0.30.0
idna                         3.10
markdownify                  1.2.0
pip                          25.2
proto-plus                   1.26.1
protobuf                     5.29.5
pyasn1                       0.6.1
pyasn1_modules               0.4.2
pydantic                     2.11.7
pydantic_core                2.33.2
pyparsing                    3.2.3
python-dateutil              2.9.0.post0
python-dotenv                1.1.1
pytz                         2025.2
requests                     2.32.5
rsa                          4.9.1
setuptools                   80.9.0
sgmllib3k                    1.0.0
six                          1.17.0
soupsieve                    2.8
tqdm                         4.67.1
typing_extensions            4.15.0
typing-inspection            0.4.1
uritemplate                  4.2.0
urllib3                      2.5.0
zope.interface               7.2
```

## Start here

If you are comfortable with python and API use, [start here](https://docs.buttondown.email/api-introduction).

If you are not, [start here](https://www.studytonight.com/post/python-virtual-environment-setup-on-mac-osx-easiest-way).

## Scripts

This list will grow as my needs evolve for [Hot Fudge Daily](https://hot.fudge.org) newsletter grow and my API automation comfort increases.

- get_list.py - pulls basic information that is readable in a terminal 
- get_digest.py - pulls recent posts to be piped into a buffer i.e. ```python3 get_digest.py | pbcopy```
- get_models.py - verify your Google Gemini API key is functional
- linkedin_post_generator.py - pull most recent email and apply LinkedIn content strategy prompt using Gemini
- export_for_import.py - prepare a Buttondown email export for use in Eleventy Excellent (11ty starter)
- parsing/*.py - odds and ends for handing rss and extracting elements from HTML

## JupyterLab 

This list will grow as my newsletter analysis skils improve.

- Topics.ipynb - a quick analysis of markdown format blog posts for words and frequency from my blog post [Finding My Nich (2024)](https://fudge.org/archive/finding-my-niche) 
- stay tuned...
