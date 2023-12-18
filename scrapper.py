import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup


def get_a_page(url: str):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(str(e))
        raise e


def scrape_candidate_urls(url: str):
    logging.info(f"Now scraping for URL: {url}")

    html_content = get_a_page(url)
    soup = BeautifulSoup(html_content, "html.parser")

    candidate_cells = soup.select(".lightblue-box .row .col-xl-2 a")
    urls = [a["href"] for a in candidate_cells]

    next_page_element = soup.select_one(".next.page-numbers")
    if next_page_element is not None:
        urls += scrape_candidate_urls(next_page_element["href"])

    logging.info(f"{len(urls)} candidate(s) found on the web site.")
    return urls


def scrape_candidate_details(url: str, species: str):
    logging.info(f"Now scraping for candidate: {url}")

    html_content = get_a_page(url)
    soup = BeautifulSoup(html_content, "html.parser")
    candidate = Candidate()

    candidate.name = soup.select_one(".info-box .col-lg-4:nth-child(2)").text.strip()
    candidate.id = soup.select_one(".info-box .col-lg-4:nth-child(3)").text.strip().split(".")[1]
    candidate.species = species
    candidate.url = url
    candidate.photo_url = soup.select_one(".img-fluid").get("src").strip()
    candidate.breed = soup.select_one(".info-box .box-body .col-lg-4:nth-child(1)").text.split("\n")[1].strip()
    candidate.gender = soup.select_one(".info-box .box-body .col-lg-4:nth-child(2)").text.split("\n")[1].strip()
    candidate.birthday = soup.select_one(".info-box .box-body .col-lg-4:nth-child(3)").text.split("\n")[1].strip()
    candidate.microchip_no = soup.select_one(".info-box .box-body .col-lg-4:nth-child(4)").text.split("\n")[1].strip()
    candidate.location = soup.select_one(".info-box .box-body .col-lg-4:nth-child(6)").text.split("\n")[1].strip()

    return candidate


def filter_new_candidate_urls(candidates_in_db, urls):
    db_dicts = [doc.to_dict() for doc in candidates_in_db]
    filtered_urls = [url for url in urls if all(candidate["url"] != url for candidate in db_dicts)]

    logging.info(f"{len(filtered_urls)} NEW candidate(s) found.")

    return filtered_urls


@dataclass
class Candidate:
    id: Optional[str] = field(default=None)
    species: Optional[str] = field(default=None)
    url: Optional[str] = field(default=None)
    photo_url: Optional[str] = field(default=None)
    name: Optional[str] = field(default=None)
    gender: Optional[str] = field(default=None)
    birthday: Optional[str] = field(default=None)
    location: Optional[str] = field(default=None)
    breed: Optional[str] = field(default=None)
    microchip_no: Optional[str] = field(default=None)
    is_notified_cat: bool = field(default=False)
    is_notified_all: bool = field(default=False)
