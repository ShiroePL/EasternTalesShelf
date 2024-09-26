import scrapy
from app.functions.sqlalchemy_fns import save_manga_details

class MangaUpdatesSpider(scrapy.Spider):
    name = "mangaupdates"

    def __init__(self, start_url, *args, **kwargs):
        super(MangaUpdatesSpider, self).__init__(*args, **kwargs)
        self.start_urls = [start_url]
        self.anilist_id = kwargs.get('anilist_id')

    def parse(self, response):
        # Extract the "Status in Country of Origin" including multiple lines (handling <br> tags)
        status_elements = response.xpath("//div[b[contains(., 'Status')]]/following-sibling::div[1]//text()").getall()
        status = '\n'.join([line.strip() for line in status_elements if line.strip()])

        # Stop at specific known boundaries to avoid extra data
        if "Completely Scanlated?" in status:
            status = status.split("Completely Scanlated?")[0].strip()

        # Extract the other fields (licensed, completely scanlated, last updated)
        licensed = response.xpath("//div[b[contains(., 'Licensed (in English)')]]/following-sibling::div/text()").get()
        completely_scanlated = response.xpath("//div[b[contains(., 'Completely Scanlated?')]]/following-sibling::div/text()").get()
        last_updated = response.xpath("//div[b[contains(., 'Last Updated')]]/following-sibling::div/text()").get()

        # Clean and structure the data
        details = {
            'status_in_country_of_origin': status.strip() if status else None,
            'licensed_in_english': licensed.strip() if licensed else None,
            'completely_scanlated': completely_scanlated.strip() if completely_scanlated else None,
            'last_updated': last_updated.strip() if last_updated else None,
        }

        # Log the details
        self.log(f"Scraped Manga Details: {details}")

        # Save the scraped data
        
        save_manga_details(details, anilist_id=self.anilist_id)
