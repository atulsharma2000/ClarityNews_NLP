import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector


class IndianExpressScraper:
    def __init__(self, driver, db_config):
        """
        Initialize the scraper with a Selenium WebDriver instance and database configuration.
        :param driver: Selenium WebDriver instance
        :param db_config: Dictionary containing database connection details
        """
        self.driver = driver
        self.db_config = db_config

    def scrape_indian_express(self):
        """
        Scrapes the main Indian Express page for top news.
        :return: List of detailed news items with title, link, and content
        """
        self.driver.get("https://indianexpress.com/")
        time.sleep(5)
        news_list = []

        try:
            # Locate the "right-part" section containing news headlines
            right_part = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "right-part"))
            )
            top_news = right_part.find_element(By.CLASS_NAME, "top-news")
            top_news_items = top_news.find_elements(By.TAG_NAME, "li")

            for item in top_news_items:
                try:
                    # Extract headline and link
                    headline = item.find_element(By.TAG_NAME, "h3").find_element(By.TAG_NAME, "a")
                    title = headline.text.strip()
                    link = headline.get_attribute("href")

                    if title and link:
                        news_list.append({"title": title, "link": link})
                except Exception as e:
                    print(f"Error processing a news item: {e}")

        except Exception as e:
            print(f"Error during scrape_indian_express: {e}")

        return self.scrape_inside_links(news_list)

    def scrape_inside_links(self, news_list):
        """
        Visits each news link and scrapes detailed content.
        :param news_list: List of news items with titles and links
        :return: List of detailed news items with title, link, and content
        """
        detailed_news_list = []

        for news in news_list:
            try:
                # Navigate to the news link
                self.driver.get(news["link"])
                time.sleep(5)

                # Extract main content of the news
                heading = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                ).text

                subheading = self.driver.find_elements(By.TAG_NAME, "h2")[0].text
                content = self.driver.find_element(By.ID, "pcl-full-content").text

                detailed_news_list.append({
                    "title": news["title"],
                    "link": news["link"],
                    "content": content,
                })

            except Exception as e:
                print(f"Error scraping link {news['link']}: {e}")

        return detailed_news_list

    def scrape_latest_news(self):
        """
        Scrapes the "Latest News" section of the Indian Express website.
        :return: List of detailed news items with title, link, and content
        """
        self.driver.get("https://indianexpress.com/")
        time.sleep(5)
        news_list = []

        try:
            # Locate the "right-part" section for latest news
            latest_news_section = self.driver.find_elements(By.CLASS_NAME, "right-part")[1]
            latest_news_items = latest_news_section.find_elements(By.TAG_NAME, "li")

            for item in latest_news_items:
                try:
                    # Extract headline and link
                    headline = item.find_element(By.TAG_NAME, "h3").find_element(By.TAG_NAME, "a")
                    title = headline.text.strip()
                    link = headline.get_attribute("href")

                    if title and link:
                        news_list.append({"title": title, "link": link})
                except Exception as e:
                    print(f"Error processing a news item: {e}")

        except Exception as e:
            print(f"Error during scrape_latest_news: {e}")

        return self.scrape_inside_links(news_list)

    def scrape_top_news(self):
        """
        Scrapes the "Top News" section from the Indian Express website.
        :return: List of detailed news items with title, link, and content
        """
        self.driver.get("https://indianexpress.com/")
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "left-part"))
        )
        news_list = []

        try:
            # Locate the "left-part" section containing top news
            left_part_sections = self.driver.find_elements(By.CLASS_NAME, "left-part")

            if len(left_part_sections) < 2:
                print("Left part not found or does not have enough sections.")
                return news_list

            articles = left_part_sections[1].find_elements(By.TAG_NAME, "div")

            for article in articles:
                try:
                    # Extract headline and link
                    inner_divs = article.find_elements(By.TAG_NAME, "div")

                    if len(inner_divs) < 2:
                        continue

                    headline = inner_divs[1].find_element(By.TAG_NAME, "h3").find_element(By.TAG_NAME, "a")
                    title = headline.text.strip()
                    link = headline.get_attribute("href")

                    if title and link:
                        news_list.append({"title": title, "link": link})
                except Exception as e:
                    print(f"Error processing article: {e}")

        except Exception as e:
            print(f"Error during scrape_top_news: {e}")

        return self.scrape_inside_links(news_list)

    def save_news_to_file(self, file_path="../data/indian_express_all_news.json"):
        """
        Scrapes all news sections and saves them to a JSON file.
        :param file_path: Path to the JSON file where news will be saved
        """
        # Check if file already exists to append data
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                all_news = json.load(file)
        else:
            all_news = []

        # Scrape news from all sections
        all_news.extend(self.scrape_indian_express())
        all_news.extend(self.scrape_latest_news())
        all_news.extend(self.scrape_top_news())

        # Remove duplicates by using a dictionary keyed by link
        unique_news = {news['link']: news for news in all_news}.values()

        # Save unique news to the JSON file
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(list(unique_news), file, ensure_ascii=False, indent=4)

        self.store_news_in_db(unique_news)
        print(f"Scraped and saved {len(unique_news)} articles to '{file_path}'.")

    def store_news_in_db(self, news_list):
        """
        Stores the scraped news into a MySQL database.
        :param news_list: List of news items with title, link, and content
        """
        # Connect to the database
        connection = mysql.connector.connect(**self.db_config)
        cursor = connection.cursor()

        for news in news_list:
            try:
                # Insert news data into the database
                cursor.execute(
                    "INSERT INTO news (title, link, content) VALUES (%s, %s, %s)",
                    (news['title'], news['link'], news['content']),
                )
                connection.commit()
                print(f"Inserted: {news['title']}")
            except mysql.connector.Error as err:
                print(f"Error inserting data: {err}")

        cursor.close()
        connection.close()


def main():
    """
    Main function to initialize the scraper and start the scraping process.
    """
    # Database configuration
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "manager",
        "database": "news_db",
    }

    # Initialize the Selenium WebDriver
    driver = webdriver.Firefox()

    try:
        # Create an instance of the scraper and start scraping
        scraper = IndianExpressScraper(driver, db_config)
        scraper.save_news_to_file()
    finally:
        # Ensure the driver is closed properly
        driver.quit()


if __name__ == "__main__":
    main()
