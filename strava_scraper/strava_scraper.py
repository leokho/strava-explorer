#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests, http, time, traceback, sys, re, os

from time import sleep

from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from pprint import pprint
from fake_useragent import UserAgent

from strava_scraper._utils.tools import *
from strava_scraper._utils.units import *

class StravaScraper(object):
    ua = UserAgent()
    USER_AGENT = str(ua.firefox)
    BASE_HEADERS = {'User-Agent': USER_AGENT}
    CSRF_H = 'x-csrf-token'

    SESSION_COOKIE='_strava4_session'

    BASE_URL = "https://www.strava.com"
    URL_LOGIN = "%s/login" % BASE_URL
    URL_SESSION = "%s/session" % BASE_URL
    URL_DASHBOARD = "%s/dashboard/following/%%d" % BASE_URL
    URL_DASHBOARD_FEED = "%s/dashboard/feed?feed_type=following&athlete_id=%%s&before=%%s&cursor=%%s" % BASE_URL
    URL_SEND_KUDO = "%s/feed/activity/%%s/kudo" % BASE_URL
    URL_PRO_ATHLETE = "%s/pros/%%s?chart_type=miles&interval_type=week&interval=%%s&year_offset=0" % BASE_URL
    URL_NORMAL_ATHLETE = "%s/athletes/%%s?chart_type=miles&interval_type=week&interval=%%s&year_offset=0" % BASE_URL
    URL_SINGLE_ACTIVITY = "%s/activities/%%s" % BASE_URL
    URL_ACTIVITY_STREAM = "%s/activities/%%s/streams" % BASE_URL

    soup = None
    response = None
    csrf_token = None
    feed_cursor = None
    feed_before = None

    athlete_interval = None
    athlete_id = 0

    def __init__(self, cookie_dir, owner_id=None, cert=None, debug=0, request_interval=lambda: 0):
        self.cookies_path = cookie_dir / 'cookies.txt'
        if not self.cookies_path.exists():
            self.cookies_path.parent.mkdir(exist_ok=True, parents=True)
            self.cookies_path.touch()
        self.owner = (owner_id, None)
        self.cert = cert
        self.debug = debug
        self.session = self.__create_session(owner_id == None)
        self.get = lambda url, logged=True, allow_redirects=True, wait_before_request=request_interval: self.__store_response(self.__get(url, logged, allow_redirects, wait_before_request))
        self.post = lambda url, data=None, logged=True, allow_redirects=True, wait_before_request=request_interval: self.__store_response(self.__post(url, data, logged, allow_redirects, wait_before_request))

    def __create_session(self, fresh):
        session = requests.Session()
        cookies = http.cookiejar.MozillaCookieJar(str(self.cookies_path))
        if not fresh:
            try: cookies.load()
            except OSError: pass
        session.cookies = cookies
        return session

    def __get(self, url, logged=True, allow_redirects=True, wait_before_request = lambda: 0):
        self.__debug_request(url)
        sleep(wait_before_request())
        response = self.session.get(url, headers=StravaScraper.BASE_HEADERS, verify=self.cert, allow_redirects=allow_redirects)
        self.__debug_response(response)
        self.__check_response(response, logged)
        return response

    def __post(self, url, data=None, logged=True, allow_redirects=True, wait_before_request = lambda x: 0):
        self.__debug_request(url)
        csrf_header = {}
        if self.csrf_token: csrf_header[StravaScraper.CSRF_H] = self.csrf_token

        headers = {**StravaScraper.BASE_HEADERS, **csrf_header}

        sleep(wait_before_request())
        if data:
            response = self.session.post(url, data=data, headers=headers, verify=self.cert, allow_redirects=allow_redirects)
        else:
            response = self.session.post(url, headers=headers, verify=self.cert, allow_redirects=allow_redirects)
        self.__debug_response(response)
        self.__check_response(response, logged)
        return response

    def __check_response(self, response, logged=False):
        response.raise_for_status()
        if logged and "class='logged-out" in response.text:
            raise NotLogged()
        return response

    def __debug_request(self, url):
        if self.debug > 0:
            print('>>> GET %s' % url)

    def __debug_response(self, response):
        if self.debug > 0:
            print('<<< Status %d' % response.status_code)
            print('<<< Headers')
            pprint(response.headers)
            if self.debug > 1 and 'Content-Type' in response.headers:
                print('<<< Body')
                if response.headers['Content-Type'] == 'text/html':
                    print(response.text)
                elif response.headers['Content-Type'] == 'application/json':
                    pprint(json.loads(response.text))
                else:
                    print(response.text)


    def __store_response(self, response):
        self.response = response
        self.soup = BeautifulSoup(response.text, 'lxml')
        meta = first(self.soup.select('meta[name="csrf-token"]'))
        if meta:
            self.csrf_token = meta.get('content')
        return response

    def __print_traceback(self):
        if self.debug > 0: traceback.print_exc(file=sys.stdout)

    def save_state(self):
        self.session.cookies.save()

    def login(self, email, password, remember_me=True):
        # If the client was logged, we safely logout first
        self.logout()
        self.get(StravaScraper.URL_LOGIN, logged=False)
        soup = BeautifulSoup(self.response.content, 'lxml')
        utf8 = soup.find_all('input',
                             {'name': 'utf8'})[0].get('value').encode('utf-8')
        token = soup.find_all('input',
                              {'name': 'authenticity_token'})[0].get('value')
        login_data = {
            'utf8': utf8,
            'authenticity_token': token,
            'plan': "",
            'email': email,
            'password': password
        }
        if remember_me:
            login_data['remember_me'] = 'on'

        self.post(StravaScraper.URL_SESSION, login_data, logged=False, allow_redirects=False)
        if self.response.status_code == 302 and self.response.headers['Location'] == StravaScraper.URL_LOGIN:
            raise WrongAuth()

        self.load_dashboard()
        try:
            assert("Log Out" in self.response.text)
            profile = first(self.soup.select('div.athlete-profile'))
            self.owner = (
                first(profile.select('a'), tag_get('href', lambda x:x.split('/')[-1])),
                first(profile.select('div.athlete-name'), tag_string())
            )
        except Exception as e:
            self.__print_traceback()
            raise UnexpectedScrapped('Profile information cannot be retrieved', self.soup.text)

    def logout(self):
        self.session.cookies.clear()

    def load_page(self, path='page.html'):
        with open(path, 'r') as file:
            self.soup = BeautifulSoup(file.read(), 'lxml')

    def load_dashboard(self, num=30):
        self.get(StravaScraper.URL_DASHBOARD % (num+1))
        self.__store_feed_params()

    def load_feed_next(self):
        self.get(StravaScraper.URL_DASHBOARD_FEED % (self.owner[0], self.feed_before, self.feed_cursor))
        self.__store_feed_params()

    def load_athlete_activities(self, athlete_id, athlete_type='pro', start_date = None):
        self.athlete_id = athlete_id
        if athlete_type == 'normal':
            self.athlete_url = StravaScraper.URL_NORMAL_ATHLETE
        else:
            self.athlete_url = StravaScraper.URL_PRO_ATHLETE
        self.athlete_interval = AthleteInterval(start_date)
        self.get(self.athlete_url % (self.athlete_id, self.athlete_interval.value))
        return self.athlete_interval.value

    def load_prev_athlete_activities(self, do_not_load = []):
        self.athlete_interval.one_week_back()
        if (self.athlete_interval.value in do_not_load):
            return None
        self.get(self.athlete_url % (self.athlete_id, self.athlete_interval.value))
        return self.athlete_interval.value

    def __store_feed_params(self):
        remove_UTC = lambda x:x.replace(' UTC','')

        cards = list(self.soup.select('div.activity.feed-entry.card'))
        ranks = list(each(cards, tag_get('data-rank')))
        updated = list(each(cards, tag_get('data-updated-at')))
        datetimesUTC = list(each(self.soup.select('div.activity.feed-entry.card time time'), tag_get('datetime')))
        datetimes = list(map(remove_UTC, datetimesUTC))
        entries = list(zip(ranks, updated, datetimes))
        if len(entries) > 0:
            self.feed_cursor = sorted(entries, key=lambda data:data[0])[0][0]
            self.feed_before = sorted(entries, key=lambda data:data[2])[0][1]

    def get_activity_stream(self, activity_id):
        try:
            response = self.__get(StravaScraper.URL_ACTIVITY_STREAM % activity_id)

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401 or status_code == 404:
                return None
            else:
                raise

        return response.text

    def get_activity_details(self, activity_id):
        self.get(StravaScraper.URL_SINGLE_ACTIVITY % activity_id)

        if not activity_id in self.response.url:
            return None, None

        all_items = self.soup.select('strong')

        details = {}

        for item in all_items:
            if 'km' in item.text and not 'km/h' in item.text:
                details['km'] = item.text
                continue
            if 'km/h' in item.text:
                details['speed'] = item.text
                continue
            if ':' in item.text:
                details['moving_time'] = item.text
                continue
            if 'm' in item.text and not 'time' in item.text:
                details['elevation'] = item.text
                continue
            if 'W' in item.text:
                details['weighted_av_power'] = item.text
                continue
            if '%' in item.text:
                details['intensity'] = item.text
                continue
            if 'kJ' in item.text:
                details['total_work'] = item.text
            try:
                details['training_load'] = int(item.text)
            except:
                pass

        title_items = self.soup.select('.title')
        title = title_items[0].text
        if 'Ride' in title:
            details['training_type'] = 'ride'
        elif 'Indoor Cycling' in title:
            details['training_type'] = 'indoor_ride'
        else:
            details['training_type'] = 'other'

        stream = self.get_activity_stream(activity_id)

        return details, stream

    def activities(self):
        for activity in self.soup.select('div.activity, div.group-activity'):
            try:
                if 'group-activity' in activity['class']:
                    yield self._process_group_activity(activity)
                else:
                    yield self._process_activity(activity)
            except Exception as e:
                print(e)
                self.__print_traceback()
                if self.debug > 0:
                    print("Unparsable %s" % activity)

    def _process_activity(self, activity):
        entry = {
            'athlete_name': first(activity.select('a.entry-owner'), tag_string()),
            'kind': first(activity.select('.app-icon.icon-dark.icon-lg'), extract_sport()),
            'time': first(activity.select('time time'), tag_string()),
            'datetime': first(activity.select('.timestamp'), tag_get('datetime', parse_datetime('%Y-%m-%d %H:%M:%S %Z'))),
            'title': first(activity.select('h3 a'), tag_string()),
            'id': first(activity.select('h3 a'), tag_get('href', lambda x: x.split('/')[-1])),
            'distance': find_stat(activity, r'\s*Distance\s*(.+)\s', to_distance),
            'duration': find_stat(activity, r'\s*Time\s*(.+)\s', to_duration),
            'elevation':find_stat(activity, r'\s*Elevation Gain\s*(.+)\s', to_elevation),
            'kudoed': first(activity.select('div.entry-footer div.media-actions button.js-add-kudo')) is None
        }
        return entry

    def _process_group_activity(self, activity):
        entry = {
            'athlete_name': first(activity.select('a.entry-owner'), tag_string()),
            'kind': first(activity.select('.app-icon.icon-dark.icon-md'), extract_sport()),
            'time': first(activity.select('time time'), tag_string()),
            'datetime': first(activity.select('.timestamp'), tag_get('datetime', parse_datetime('%Y-%m-%d %H:%M:%S %Z'))),
            'title': first(activity.select('h4 a'), tag_string()),
            'id': first(activity.select('h4 a'), tag_get('href', lambda x: x.split('/')[-1])),
            'distance': find_stat(activity, r'\s*Distance\s*(.+)\s', to_distance),
            'duration': find_stat(activity, r'\s*Time\s*(.+)\s', to_duration),
            'elevation':find_stat(activity, r'\s*Elevation Gain\s*(.+)\s', to_elevation),
            'kudoed': first(activity.select('div.entry-footer div.media-actions button.js-add-kudo')) is None
        }
        print(entry)
        return entry

    def get_all_activities(self):
        return [activity for activity in self.activities()]

    # Utility functions
def safe_text_get (l, idx, default=None):
  try:
    return l[idx].text
  except IndexError:
    return default

def tag_string(mapper=identity):
    return lambda tag: mapper(tag.string.replace('\n',''))
def tag_get(attr, mapper=identity):
    return lambda tag: mapper(tag.get(attr))
def parse_datetime(pattern):
    return lambda value: datetime.strptime(value, pattern)
def has_class(tag, predicate):
    return any_match(tag.get('class'), predicate)
def extract_sport():
    class_sports = {
    'run':'Run',
    'ride':'Bike',
    'ski':'Ski',
    'swim':'Swim',
    'walk':'Walk',
    '':'Sport' # Must defined at last position
    }
    return lambda tag: first([ v
        for k,v in class_sports.items()
        if has_class(tag, lambda cls: contains(k, cls)) ])

def to_distance(value):
    m = re.search(r'\s*(.+)\s+(km|m)\s*', value)
    if m:
        # remove thousand separator
        num = float(re.sub(r'[^\d\.]', '', m.group(1)))
        if m.group(2) == 'km':
            num = num * 1000
        return Distance(num)
    return UNIT_EMPTY

def to_elevation(value):
    m = re.search(r'\s*(.+)\s+(km|m)\s*', value)
    if m:
        # remove thousand separator
        num = float(re.sub(r'[^\d\.]', '', m.group(1)))
        if m.group(2) == 'km':
            num = num * 1000
        return Elevation(num)
    return UNIT_EMPTY


def to_duration(value):
    units = {
        'h': lambda s: int(s) * 60 * 60,
        'm': lambda s: int(s) * 60,
        's': lambda s: int(s),
    }
    m = re.search(r'\s*(\d+)([hms])\s+(\d+)([hms])\s*', value)
    if m:
        (s1, t1, s2, t2) = m.groups()
        return Duration(units[t1](s1) + units[t2](s2))

    return UNIT_EMPTY

def find_stat(activity, pattern, formatter=identity):
    for stat in activity.select('div.media-body ul.list-stats .stat'):
        m = re.search(pattern, stat.text)
        if m: return formatter(m.group(1))
    return UNIT_EMPTY


class AthleteInterval():
    def __init__ (self, start_date = None):
        if start_date:
            self.current_date = start_date
        else:
            self.current_date = date.today()

        self._update_values()

    def one_week_back(self):
        one_week_delta = timedelta(days=7)
        self.current_date = self.current_date - one_week_delta
        self._update_values()

    def _update_values(self):
        self.year, self.week_num, _ = self.current_date.isocalendar()
        week_num_str = str(self.week_num)
        if len(week_num_str) == 1:
            week_num_str = '0' + week_num_str
        self.value = str(self.year) +  week_num_str

class NotLogged(Exception):
    pass

class WrongAuth(Exception):
    pass

class RestrictedAccess(Exception):
    pass

class UnexpectedScrapped(Exception):
    def __init__(self, message, content):
        self.message = message
        self.content = content
