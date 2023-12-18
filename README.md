# HK Adopt Bot

This repository contains Python code for a scheduled Azure Function that scrapes data an adoption website and notifies users about new candidates available for adoption. The code utilizes Azure Functions, Azure Cosmos DB, and the Telegram Bot API.

## Prerequisites

Before running the code, make sure you have the following:

- Python 3.x installed
- Azure Functions Core Tools installed
- Azure Cosmos DB account and connection string
- Telegram bot token

## Installation

1. Clone this repository:

   ```
   git clone <this repo>
   ```

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set up the following environment variables:
   - `HKADOPT_CHAT_ID`: The Telegram chat ID to receive notifications for all candidates.
   - `HKADOPT_CAT_CHAT_ID`: The Telegram chat ID to receive notifications for cat candidates only.
   - `BOT_TESTING_CHAT_ID`: The Telegram chat ID for testing purposes.
   - `HKADOPT_BOT_TOKEN`: The Telegram bot token.
   - `ERROR_CHAT_ID`: The Telegram chat ID to receive error notifications.

## Usage

The code consists of several Azure Functions triggered by timers and HTTP requests. Here is an overview of each function:

### `scrape_data_timer_trigger`

- Trigger: Scheduled timer
- Input: Azure Cosmos DB documents (candidates) created or updated in the last 365 days
- Output: Azure Cosmos DB documents (new candidates)
- Description: This function scrapes candidate data from the adoption website and filters out any candidates that already exist in the database. The new candidates are then stored in Azure Cosmos DB.

### `get_candidates_from_web_trigger`

- Trigger: HTTP request
- Description: This function allows you to manually initiate the scraping process and retrieve the candidate data from the adoption website. It returns the data as a JSON response.

### `notify_new_candidates_timer_trigger`

- Trigger: Scheduled timer
- Input: Azure Cosmos DB documents (candidates) that haven't been notified
- Output: Azure Cosmos DB documents (candidates) marked as notified
- Description: This function sends notifications to the specified Telegram chat ID(s) for new candidates that haven't been notified yet. It uses the Telegram Bot API to send messages and photos.

### `notify_new_candidates_cat_timer_trigger`

- Trigger: Scheduled timer
- Input: Azure Cosmos DB documents (cat candidates) that haven't been notified
- Output: Azure Cosmos DB documents (cat candidates) marked as notified
- Description: This function is similar to `notify_new_candidates_timer_trigger`, but it specifically handles cat candidates.

To deploy and run the Azure Functions, refer to the Azure Functions documentation for your preferred deployment method (Azure Portal, Azure CLI, Visual Studio Code, etc.).

## License

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

This code is provided as-is without any warranty. Use it at your own risk.
