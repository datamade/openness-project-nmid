The Openness Project - New Mexico Campaign Finance Site
==========

This site brings greater transparency to New Mexico politics by providing an overview of campaign contributions, expenditures, and the people, businesses, and organizations involved.

## Setup
**Install app requirements**

We recommend using [virtualenv](http://virtualenv.readthedocs.org/en/latest/virtualenv.html) and [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) for working in a virtualized development environment. [Read how to set up virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Once you have virtualenvwrapper set up, do this:

```bash
mkvirtualenv openness-project-nmid -p /path/to/your/python3
git clone https://github.com/datamade/openness-project-nmid.git
cd openness-project-nmid
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

## Data import

To import the New Mexico campaign finance data into your database, run the `import_data` command:

```
python manage.py import_data
```

The version of the data sent to us by the Secretary of State in April 2018
contains a number of errors - primarily candidates that are assigned to the
wrong race. To fix these errors, run the `edit_data` command:

```
python manage.py edit_data
```

Next, group campaigns into races with the `make_races` command.

```
python manage.py make_races
```

Finally, run the `make_search_index` command to generate the search index.

```
python manage.py make_search_index
```

## Redoing an import

The data import scripts for this app will automatically recognize if you have data imported,
and add or update new data accordingly. However, if you'd like to start over from
scratch but don't want to delete your user and page data, you can start by running the
`flush_camp_fin` command to flush campaign finance data from the database:

```
python manage.py flush_camp_fin
```

## Run the code

Run the server with the following:
```bash
workon openness-project-nmid
python manage.py runserver
```

Then, navigate to: http://localhost:8000/

## Team

* Eric van Zanten - developer
* Derek Eder - developer
* Regina Compton - developer
* Jean Cochrane - developer

## Errors / Bugs

If something is not behaving intuitively, it is a bug, and should be reported.
Report it here: https://github.com/datamade/openness-project-nmid/issues
