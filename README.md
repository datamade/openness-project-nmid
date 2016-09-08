New Mexico Campaign Finance Site
==========

This site brings greater transparency to New Mexico politics by providing an overview of campaign contributions, expenditures, and the people, businesses, and organizations involved.

##Setup
**Install app requirements**

We recommend using [virtualenv](http://virtualenv.readthedocs.org/en/latest/virtualenv.html) and [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) for working in a virtualized development environment. [Read how to set up virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Once you have virtualenvwrapper set up, do this:

```bash
mkvirtualenv nmid -p /path/to/your/python3
git clone https://github.com/datamade/nmid.git
cd nmid
pip install -r requirements.txt
```

Next, change your application settings. Start by copying the example `settings_local_example.py`

```
cp nmid/settings_local_example.py nmid/settings_local.py
```

Then set your database name, user and password.

Next, create a postgres database and run the Django migrations to setup the proper tables.

```
createdb nmid
python manage.py migrate
```

##Data import

To import the New Mexico campaign finance data into your database, run the `import_data` command.

```
python manage.py import_data
```

Then, run the `make_search_index` command.

```
python manage.py make_search_index
```

##Run the code

Run the server with the following:
```bash
workon nmid
python manage.py runserver
```

Then, navigate to: http://localhost:8000/

## Team

* Eric van Zanten - developer
* Derek Eder - developer
* Regina Compton - developer

## Errors / Bugs

If something is not behaving intuitively, it is a bug, and should be reported.
Report it here: https://github.com/datamade/illinois-sunshine/issues
