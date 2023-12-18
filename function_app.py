#!/usr/bin/python
# -*- coding: utf-8 -*-
import concurrent.futures
import datetime
import json
import logging
import os
import time

import azure.functions as func

from scrapper import filter_new_candidate_urls, scrape_candidate_details, scrape_candidate_urls
from telegram_api import send_notification

app = func.FunctionApp()


MAIN_URL = os.environ["MAIN_URL"]
DB_NAME = os.environ["DB_NAME"]
DB_CONTAINER_NAME = os.environ["DB_CONTAINER_NAME"]
HKADOPT_CHAT_ID = os.environ["HKADOPT_CHAT_ID"]
HKADOPT_CAT_CHAT_ID = os.environ["HKADOPT_CAT_CHAT_ID"]

current_datetime = datetime.datetime.now()
past_365_days_datetime = current_datetime - datetime.timedelta(days=365)
past_365_days_ts = int(time.mktime(past_365_days_datetime.timetuple()))

SPECIES_MAP = {"Cat": "96", "Dog": "97"}


@app.schedule(schedule="0 0/30 * * * *", arg_name="timer", run_on_startup=False, use_monitor=False)
@app.cosmos_db_input(
    arg_name="inputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    sql_query=f"SELECT * FROM c WHERE c._ts > {past_365_days_ts}",
    connection="CosmosDbConnectionString",
)
@app.cosmos_db_output(
    arg_name="outputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    connection="CosmosDbConnectionString",
)
def scrape_data_timer_trigger(
    timer: func.TimerRequest, inputCandidates: func.DocumentList, outputCandidates: func.Out[func.Document]
) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if timer.past_due:
        logging.info("The timer is past due!")

    logging.info("Start scrapping data.")
    logging.info(f"{len(inputCandidates)} candidate(s) found in database.")

    species_list = ["Cat", "Dog"]
    new_candidates = []
    try:
        for species in species_list:
            urls = scrape_candidate_urls(f"{MAIN_URL}?sel_specie={SPECIES_MAP[species]}")
            new_urls = filter_new_candidate_urls(inputCandidates, urls)
            with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
                new_candidates += list(executor.map(scrape_candidate_details, new_urls, [species] * len(new_urls)))
    except Exception as e:
        logging.error(f"Error: {str(e)}")

    newdocs = func.DocumentList()
    for new_candidate in new_candidates:
        newdocs.append(func.Document.from_dict(new_candidate.__dict__))
    outputCandidates.set(newdocs)

    logging.info("Python timer trigger function ran at %s", utc_timestamp)


@app.route(route="scrape-data", auth_level=func.AuthLevel.FUNCTION)
@app.cosmos_db_input(
    arg_name="inputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    sql_query=f"SELECT * FROM c WHERE c._ts > {past_365_days_ts}",
    connection="CosmosDbConnectionString",
)
@app.cosmos_db_output(
    arg_name="outputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    connection="CosmosDbConnectionString",
)
def scrape_data_http_trigger(
    req: func.HttpRequest, inputCandidates: func.DocumentList, outputCandidates: func.Out[func.Document]
) -> func.HttpResponse:
    logging.info("Start scrapping data.")
    logging.info(f"{len(inputCandidates)} candidate(s) found in database.")

    species_list = ["Cat", "Dog"]
    new_candidates = []
    try:
        for species in species_list:
            urls = scrape_candidate_urls(f"{MAIN_URL}?sel_specie={SPECIES_MAP[species]}")
            new_urls = filter_new_candidate_urls(inputCandidates, urls)
            with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
                new_candidates += list(executor.map(scrape_candidate_details, new_urls, [species] * len(new_urls)))
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

    newdocs = func.DocumentList()
    for new_candidate in new_candidates:
        newdocs.append(func.Document.from_dict(new_candidate.__dict__))
    outputCandidates.set(newdocs)

    return func.HttpResponse(
        json.dumps([candidate.__dict__ for candidate in new_candidates]),
    )


@app.route(route="get-candidates-from-web", auth_level=func.AuthLevel.ANONYMOUS)
def get_candidates_from_web_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Start getting data from the web.")
    species_list = ["Cat", "Dog"]
    candidates = []
    try:
        for species in species_list:
            urls = scrape_candidate_urls(f"{MAIN_URL}?sel_specie={SPECIES_MAP[species]}")
            with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
                candidates += list(executor.map(scrape_candidate_details, urls, [species] * len(urls)))
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

    return func.HttpResponse(
        json.dumps([candidate.__dict__ for candidate in candidates]),
    )


@app.schedule(schedule="0 10/30 * * * *", arg_name="timer", run_on_startup=False, use_monitor=False)
@app.cosmos_db_input(
    arg_name="inputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    sql_query="SELECT TOP 15 * FROM c WHERE (c.is_notified_all = false OR NOT IS_DEFINED(c.is_notified_all))",
    connection="CosmosDbConnectionString",
)
@app.cosmos_db_output(
    arg_name="outputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    connection="CosmosDbConnectionString",
)
def notify_new_candidates_timer_trigger(
    timer: func.TimerRequest, inputCandidates: func.DocumentList, outputCandidates: func.Out[func.Document]
) -> func.HttpResponse:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if timer.past_due:
        logging.info("The timer is past due!")

    logging.info("Start notify new candidates.")
    logging.info(f"{len(inputCandidates)} candidate(s) found that is not notified in database.")

    send_notification(HKADOPT_CHAT_ID, inputCandidates)

    for candidate in inputCandidates:
        candidate["is_notified_all"] = True

    outputCandidates.set(inputCandidates)

    logging.info("Python timer trigger function ran at %s", utc_timestamp)


@app.route(route="notify-new-candidates-http-trigger", auth_level=func.AuthLevel.FUNCTION)
@app.cosmos_db_input(
    arg_name="inputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    sql_query="SELECT TOP 15 * FROM c WHERE (c.is_notified_all = false OR NOT IS_DEFINED(c.is_notified_all))",
    connection="CosmosDbConnectionString",
)
@app.cosmos_db_output(
    arg_name="outputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    connection="CosmosDbConnectionString",
)
def notify_new_candidates_http_trigger(
    req: func.HttpRequest, inputCandidates: func.DocumentList, outputCandidates: func.Out[func.Document]
) -> func.HttpResponse:
    logging.info("Start notify new candidates.")
    logging.info(f"{len(inputCandidates)} candidate(s) found that is not notified in database.")

    send_notification(HKADOPT_CHAT_ID, inputCandidates)

    for candidate in inputCandidates:
        candidate["is_notified_all"] = True

    outputCandidates.set(inputCandidates)

    return func.HttpResponse(json.dumps([json.loads(candidate.to_json()) for candidate in inputCandidates]))


@app.schedule(schedule="0 5/30 * * * *", arg_name="timer", run_on_startup=False, use_monitor=False)
@app.cosmos_db_input(
    arg_name="inputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    sql_query="SELECT TOP 15 * FROM c WHERE c.species = 'Cat' AND (c.is_notified_cat = false OR NOT IS_DEFINED(c.is_notified_cat))",
    connection="CosmosDbConnectionString",
)
@app.cosmos_db_output(
    arg_name="outputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    connection="CosmosDbConnectionString",
)
def notify_new_candidates_cat_timer_trigger(
    timer: func.TimerRequest, inputCandidates: func.DocumentList, outputCandidates: func.Out[func.Document]
) -> func.HttpResponse:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

    if timer.past_due:
        logging.info("The timer is past due!")

    logging.info("Start notify new candidates (Cat Only).")
    logging.info(f"{len(inputCandidates)} candidate(s) found that is not notified in database.")

    send_notification(HKADOPT_CAT_CHAT_ID, inputCandidates)

    for candidate in inputCandidates:
        candidate["is_notified_cat"] = True

    outputCandidates.set(inputCandidates)

    logging.info("Python timer trigger function ran at %s", utc_timestamp)


@app.route(route="notify-new-candidates-cat-http-trigger", auth_level=func.AuthLevel.FUNCTION)
@app.cosmos_db_input(
    arg_name="inputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    sql_query="SELECT TOP 15 * FROM c WHERE c.species = 'Cat' AND (c.is_notified_cat = false OR NOT IS_DEFINED(c.is_notified_cat))",
    connection="CosmosDbConnectionString",
)
@app.cosmos_db_output(
    arg_name="outputCandidates",
    database_name=DB_NAME,
    container_name=DB_CONTAINER_NAME,
    connection="CosmosDbConnectionString",
)
def notify_new_candidates_cat_http_trigger(
    req: func.HttpRequest, inputCandidates: func.DocumentList, outputCandidates: func.Out[func.Document]
) -> func.HttpResponse:
    logging.info("Start notify new candidates (Cat Only).")
    logging.info(f"{len(inputCandidates)} candidate(s) found that is not notified in database.")

    send_notification(HKADOPT_CAT_CHAT_ID, inputCandidates)

    for candidate in inputCandidates:
        candidate["is_notified_cat"] = True

    outputCandidates.set(inputCandidates)

    return func.HttpResponse(json.dumps([json.loads(candidate.to_json()) for candidate in inputCandidates]))
