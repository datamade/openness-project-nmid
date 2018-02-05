# Data for the Openness Project

## Where does the data come from?

Data for the Openness Project comes from the **New Mexico Secretary of State**.
They publish this data on their [data portal](https://www.cfis.state.nm.us/media/).

Rather than download data from the data portal, **we request regular data
dumps** directly from the Secretary of State's office. All of the Excel files you see in this
folder represent the latest data dump exactly as we received it. Since
producing these data dumps requires a separate export process, there are occasionally
discrepancies between the data stored here and the data as published on the Secretary of State's 
data portal. We try our best to stay on top of these discrepancies, but if you 
notice one you should feel free to [open an issue!](https://github.com/datamade/openness-project-nmid/issues/new)

Currently, we try to update the data after each filing due date. You can see the
timestamp for the last time we updated data on the footer of the [Openness
Project](https://opennessproject.com/). For the 2018 election season, we're working with the Secretary of
State to get access to data dumps more frequently.

## How do you get the data into the Openness Project?

We take the spreadsheets in this folder and import them directly into the
Openness Project database. If you can read the Python programming language, you
can take a look at [the script that performs this
import](https://github.com/datamade/openness-project-nmid/blob/master/camp_fin/management/commands/import_data.py).

## How are races created?

The Secretary of State doesn't publish data at the level of races (groups of
candidates competing for one office). To get around that limitation, we do
a little bit of inference when we import the data to try to group campaigns
into races. In general, we consider two campaigns to be in the same race if they share:

- The same office they're vying for (e.g. State Representative)
- The same election district
- The same election division
- The same county
- The same election year

Python readers can [read the script that makes these races](https://github.com/datamade/openness-project-nmid/blob/master/camp_fin/management/commands/make_races.py).

This method of inferring races works pretty well, but it's not perfect. If you
notice something wrong, [open up an issue and let us
know](https://github.com/datamade/openness-project-nmid/issues/new).

## Why does data I downloaded from the Openness Project look different from the Secretary of State's portal?

The data we offer for download on [the Openness Project](https://opennessproject.com/downloads/)
is exported from our website's database. It may have different columns from similar data
published on the Secretary of State's data portal since it's undergone a few different
transformations: it gets exported from their database to spreadsheets, which
get imported into our database, which we use to generate spreadsheets for our
users to download.

If you're noticing major discrepancies, feel free to [let us know](https://github.com/datamade/openness-project-nmid/issues/new)
and we'll take a look at it.
