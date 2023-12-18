import logging
import os
import time

import requests

TELEGRAM_TOKEN = os.environ["HKADOPT_BOT_TOKEN"]
TG_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
ERROR_CHAT_ID = os.environ["ERROR_CHAT_ID"]


def send_notification(chat_id, inputCandidates):
    for candidate in inputCandidates:
        send_photo(chat_id, candidate)


def send_photo(chat_id, candidate):
    message = f"""編號:    {candidate["id"]}
名稱:    {candidate["name"]}
品種:    {candidate["breed"]}
性別:    {candidate["gender"]}
出生:    {candidate["birthday"]}
中心:    {candidate["location"]}
晶片:    {candidate["microchip_no"]}
{candidate["url"]}
"""
    body = {
        "chat_id": chat_id,
        "caption": message,
        "photo": candidate["photo_url"],
    }
    url = TG_API_URL + "sendPhoto"

    try:
        logging.info(body)
        response = requests.post(url, body)
        response.raise_for_status()
        logging.info(f"Candidate no. {candidate['id']} is sent.")
    except requests.exceptions.RequestException as e:
        logging.error(str(e))
        send_error_message(f"Cannot send Candidate no. {candidate['id']} to HK Adopt bot API.")


def send_error_message(message: str, max_retries: int = 1) -> None:
    body = {"chat_id": ERROR_CHAT_ID, "text": message}
    url = TG_API_URL + "sendMessage"

    retries = 0
    while retries < max_retries:
        try:
            response = requests.post(url, body)
            response.raise_for_status()
            # 20 messages per minute to the same group.
            time.sleep(3)
            break
        except requests.exceptions.RequestException as e:
            logging.error(str(e))
            retries += 1
            if retries >= max_retries:
                logging.error("Failed to send message. Maximum retry count reached.")
                break
            else:
                logging.info(f"Retrying...({retries}/{max_retries})")
            send_error_message("Cannot send message to HK Adopt bot API.", max_retries=3)
