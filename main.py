from argparse import Namespace

from module.modules.argument_parser import ArgumentParser
from module.modules.book_scraper import BookScraper

if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arguments = arg_parser.return_parsed_arguments()
    book_scraper = BookScraper(arguments)
    scraped_books = book_scraper.scrape_books()
    book_scraper.print_books_info(scraped_books)

