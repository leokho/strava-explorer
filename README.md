### How to use Scrava Scrapper

## Installing
1. pip3 install pipenv
2. pipenv install

## Configuring
There's no configuration file, but the get_information should be changed:
* login_email - The email you used to register for strava
* login_pass - Your password for strava
* own_id - Your strava ID (needed for cookies)
* athlete_id - The ID of the athlete you want to scrap
* athlete_account_type - Defaults to "pro" - See spreadsheet for the value to use

## Running
1. Make sure you have a valid Strava account and configure the script with it
2. Check the profile of the rider you want to scrap if he has any activities recorded this season
3. Configure the runner for the rider
3. Run pipenv run python3 get_information.py

## Output
The output folder is "activities".
For each rider you will have one json file which will consist of one json item line by line with the summary of each rides.
Besides the summary file, there will be a folder with the stream of data from the training itself. 

## Problems?
leonid.kholkine@uantwerpen.be

