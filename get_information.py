import pathlib
from strava_scraper.strava_scraper import StravaScraper, NotLogged
from writers.orwell import Orwell
from writers.rowling import Rowling
from writers.tolkin import Tolkin
from random import randint
import json

## TODO: Move to configuration file ##
################ CONFIGURATION #####################
login_email = ''
login_pass = ''
own_id = ''
athlete_id = ''
athlete_account_type = ''
################ END CONFIGURATION #####################

number_of_weeks = 52
# None = Will start at current data and go back recursively
start_date = None
sleep_between_requests = lambda: randint(2,17)

cookies_path = pathlib.Path.cwd() / 'cookies'
cache_path = pathlib.Path.cwd() / 'cache'
activities_path = pathlib.Path.cwd() / 'activities'

activities_read_cache = Orwell(cache_path / (athlete_id + '_activities_read.txt'))
weeks_read_cache = Orwell(cache_path / (athlete_id + '_weeks_read.txt'))

activity_writer = Tolkin(activities_path / (athlete_id + '.json'))
activity_stream_writer = Rowling(activities_path / athlete_id)

strava = StravaScraper(cookies_path, owner_id = own_id, debug = 1, request_interval = sleep_between_requests)

def get_activity_details(strava_activity_id, timestamp):
    activity_details, stream = strava.get_activity_details(strava_activity_id)

    if not activity_details:
        return

    activity_details['timestamp'] = timestamp
    activity_details['id'] = strava_activity_id

    if stream:
        activity_stream_writer.write_to_file(timestamp + '_' + strava_activity_id, stream)

    activity_writer.add_json(activity_details)


def process_activities(activities):
    for activity in activities:
        strava_activity_id = activity['id']
        timestamp = activity['datetime'].strftime("%Y%m%d%H%M%S")
        internal_activity_id = timestamp + "_" + strava_activity_id

        if activity['kind'] == 'Bike' and \
           not internal_activity_id in activities_read_cache:
            get_activity_details(strava_activity_id, timestamp)
            activities_read_cache.add(internal_activity_id)


def get_weekly_activities():
    # Doing it lazy:
    # Will load first week in any case, just to check if we need to login

    try:
        current_week = strava.load_athlete_activities(athlete_id, athlete_account_type, start_date)
    except NotLogged:
        print("User not logged in - Logging in...")
        strava.login(login_email, login_pass)
        strava.save_state()
        current_week = strava.load_athlete_activities(athlete_id, athlete_account_type, start_date)

    yield current_week, strava.get_all_activities()

    for i in range(number_of_weeks-1):
        current_week = strava.load_prev_athlete_activities(weeks_read_cache.cache)
        if current_week:
            yield current_week, strava.get_all_activities()


def main():
    for current_week, activities in get_weekly_activities():
        process_activities(activities)
        weeks_read_cache.add(current_week)

main()
