# The Openness Project - New Mexico Campaign Finance Site

This site brings greater transparency to New Mexico politics by providing an overview of campaign contributions, expenditures, and the people, businesses, and organizations involved.

## Development

Development requires a local installation of [Docker](https://docs.docker.com/install/)
and [Docker Compose](https://docs.docker.com/compose/install/).

To run the application, first build the app image:

```bash
docker-compose build
```

Next, load in data and build your search index:

```bash
docker-compose run --rm app python make nightly 
docker-compose run --rm app python manage.py make_search_index
```

Finally, run the app:

```bash
docker-compose up
```

The app will be available at http://localhost:8000. The database will be exposed
on port 32001.

## Resetting the database

The data import scripts for this app will automatically recognize if you have data imported, and add or update new data accordingly. However, if you'd like to start over from scratch but don't want to delete your user and page data, you can start by running the `flush_camp_fin` command to flush campaign finance data from the database:

```bash
docker-compose run --rm app python manage.py flush_camp_fin
```

## ETL
The nightly and quarterly ETL scripts are run in a separate repo, through github actions: https://github.com/datamade/nmid-scrapers

## Errors / Bugs

If something is not behaving intuitively, it is a bug, and should be reported.
Report it here: https://github.com/datamade/openness-project-nmid/issues
