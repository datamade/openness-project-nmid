New Mexico Campaign Finance Site
==========

This site brings greater transparency to New Mexico politics by providing an overview of campaign contributions, expenditures, and the people, businesses, and organizations involved.

##Setup
**Install app requirements**

We recommend using [virtualenv](http://virtualenv.readthedocs.org/en/latest/virtualenv.html) and [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) for working in a virtualized development environment. [Read how to set up virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Once you have virtualenvwrapper set up, do this:

```bash
mkvirtualenv nmid
git clone https://github.com/datamade/nmid.git
cd nmid
pip install -r requirements.txt
```

You can return to your virtualenv when needed:

```bash
workon nmid
```

##Run the code

Run the server with the following:
```bash
python runserver.py
```

Then, navigate to: http://localhost:5000/

## Team

* Eric van Zanten - developer
* Derek Eder - developer
* Regina Compton - developer

## Errors / Bugs

If something is not behaving intuitively, it is a bug, and should be reported.
Report it here: https://github.com/datamade/illinois-sunshine/issues