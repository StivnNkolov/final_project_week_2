import sys
from operator import attrgetter

import requests
from bs4 import BeautifulSoup

from module.modules.book import Book
import json


class BookScraper:
    """
    Main class for making requests to the server, scraping and parsing data.
    """

    def __init__(self, arguments):

        self.books_to_extract_count = None
        self.filtering_params = {}
        self.sorting_params = []
        self.title = None
        self.titles_to_search_for = []
        self.working_url = 'https://books.toscrape.com/'
        self.urls_to_scrape_from = [self.working_url]
        self.books_info = []

        self.__init_attributes(arguments)

        self.filter_options_mapper = {
            'available': lambda book: int(''.join([el for el in book.availability if el.isdigit()])),
            'rating': lambda book: book.rating_converter_mapper[book.rating],
            'price': lambda book: float(book.price.replace('£', ''))
        }

        self.filter_operators_mapper = {
            '<': lambda book_rating, value_to_compare: book_rating < value_to_compare,
            '>': lambda book_rating, value_to_compare: book_rating > value_to_compare,
            '=': lambda book_rating, value_to_compare: book_rating == value_to_compare,
            '!=': lambda book_rating, value_to_compare: book_rating != value_to_compare,
            '<=': lambda book_rating, value_to_compare: book_rating <= value_to_compare,
            '>=': lambda book_rating, value_to_compare: book_rating >= value_to_compare,
        }

    def scrape_books(self):
        """
        Taking care for extracting books from all the urls that are passed by the user arguments.
        """
        for url in self.urls_to_scrape_from:
            self.__scrape_books_info(self.books_to_extract_count, url)

        self.__sort_books()
        self.save_books_to_json(self.books_info)
        return self.books_info

    def __sort_books(self):
        """
        Sorting the result list with books by different criteria and reverse order.
        It starts to loop from the least significant sorting criteria, so that we can keep
        the reverse order.
        """
        for sort_param_index in range(len(self.sorting_params) - 1, -1, -1):
            sort_by, sorting = self.sorting_params[sort_param_index]
            reverse_order = True if sorting == 'descending' else False
            self.books_info = sorted(self.books_info, key=attrgetter(sort_by), reverse=reverse_order)

    def __is_book_good_for_scraping(self, book):
        """
        Apply all the different parameters that need to be taken in consideration when scraping book.
        :param book: The book that we are testing
        :return: Boolean
        """

        if self.titles_to_search_for:
            if book.title not in self.titles_to_search_for:
                return False

        if not self.filtering_params:
            return True

        if self.filtering_params.get('filtering'):
            for cur_filter in self.filtering_params['filtering']:
                filter_by = self.filter_options_mapper[cur_filter['filter_choice']](book)
                if not self.filter_operators_mapper[cur_filter['filter_operator']](filter_by,
                                                                                   int(cur_filter['filter_value'])):
                    return False
        if self.filtering_params.get('description'):
            for cur_keyword in self.filtering_params['description']:
                if cur_keyword not in book.description:
                    return False

        return True

    def __scrape_books_info(self, number_of_books, url_to_extract_from):
        """
        Taking care for scraping N number of books.

        :param number_of_books: Number of books
        :param url_to_extract_from: Current starting point url to extract from.
        :return: List of book dictionaries
        """

        response = requests.get(url_to_extract_from)
        document_parser = BeautifulSoup(response.text, 'html.parser')

        if response.status_code != 200:
            print(f'Server status code {response.status_code}')
            return sys.exit(1)

        books_to_extract = number_of_books
        checked_books_per_page = 0
        checked_books = 0

        number_of_books_for_url = int(document_parser.select('form strong')[0].text)

        while True:
            books_article_tags = document_parser.find_all('article', class_='product_pod')
            number_of_books_on_page = len(books_article_tags)

            for book in books_article_tags:
                checked_books += 1
                checked_books_per_page += 1

                book_href_url = book.h3.a['href'].replace('../../../', '')
                book_url = self.working_url + book_href_url if 'catalogue/' in book_href_url \
                    else self.working_url + 'catalogue/' + book_href_url

                book = self.__extract_book_info(book_url)

                if self.__is_book_good_for_scraping(book):
                    self.books_info.append(book)
                    books_to_extract -= 1

                if books_to_extract == 0:
                    return self.books_info

                if checked_books_per_page == number_of_books_on_page:
                    pager_tag = document_parser.find('ul', class_='pager')

                    try:
                        next_page_url_href = pager_tag.find('li', class_='next').findNext().get(
                            'href').replace('catalogue/', '')
                    except AttributeError:
                        return self.books_info

                    if url_to_extract_from == self.working_url:
                        next_page_url = url_to_extract_from if 'catalogue/' in next_page_url_href \
                            else 'http://books.toscrape.com/catalogue/'
                    else:
                        next_page_url = url_to_extract_from

                    next_page_link = next_page_url + next_page_url_href
                    current_response = requests.get(next_page_link)
                    document_parser = BeautifulSoup(current_response.text, 'html.parser')
                    checked_books_per_page = 0
                    break

            if checked_books == number_of_books_for_url:
                return self.books_info

    @staticmethod
    def __extract_book_info(book_url):
        """
        Gathers data for single book.
        :param book_url: The url for the detail page of the book
        :return: Instance of class Book

        """
        response = requests.get(book_url)
        document_parser = BeautifulSoup(response.text, 'html.parser')

        if response.status_code != 200:
            print(f'Server status code {response.status_code}')
            return None

        book_title = document_parser.h1.string
        book_price = document_parser.select_one('p.price_color').get_text().lstrip("Â")
        book_rating = document_parser.select_one('p.star-rating')['class'][1]
        book_availability = document_parser.select_one('p.instock.availability').get_text(strip=True)
        book_description = document_parser.find('div', class_='sub-header').findNextSibling().text

        temp_book = Book(book_title, book_price, book_rating, book_availability, book_description)

        return temp_book

    def __init_attributes(self, arguments):
        """
        Parsing arguments passed by argument_parser and setting class attrs.
        :param arguments: Arguments passed by the user
        :return: None
        """
        self.books_to_extract_count = arguments.books_count
        self.sorting_params = arguments.sorting_params

        if arguments.filtering_params:
            self.filtering_params['filtering'] = arguments.filtering_params
        if arguments.description:
            self.filtering_params['description'] = arguments.description

        if arguments.genres:
            self.__extract_genres_urls_from_page(arguments.genres)

        if arguments.title:
            print(arguments.title[0])
            self.titles_to_search_for.append(arguments.title[0])
            print(self.titles_to_search_for)
            self.books_to_extract_count = 1
        elif arguments.wanted:
            self.__extract_titles_from_json(arguments.wanted)

    def __extract_titles_from_json(self, file_name):
        """
        Taking book's titles from passed json file and assigning it to titles_to_search_for
        :param file_name: The name of the file passed by the user.
        :return: None
        """
        try:
            with open(file_name, 'r') as file:
                data = json.load(file)
            book_titles = data.get('book_titles', [])
            self.titles_to_search_for = book_titles
            self.books_to_extract_count = len(self.titles_to_search_for)
        except FileNotFoundError:
            print(f"File {file_name} is not found!")

    def __extract_genres_urls_from_page(self, genres):
        """
        Taking the urls of the genres that are passed by the user and parsing them.
        :param genres: List of genres passed by the user.
        Return: None
        """
        response = requests.get(self.working_url)
        document_parser = BeautifulSoup(response.text, 'html.parser')

        if response.status_code != 200:
            print(f'Server status code {response.status_code}')
            return sys.exit(1)

        genres_div_tag = document_parser.find('div', class_='side_categories')
        genres_li_tags = genres_div_tag.select('ul li a')
        self.urls_to_scrape_from.clear()
        for genre in genres_li_tags:
            genre_name = genre.text.strip()
            if genre_name in genres:
                self.urls_to_scrape_from.append(self.working_url + genre.get('href').replace('index.html', ''))
            if len(self.urls_to_scrape_from) == len(genres):
                break

    @staticmethod
    def save_books_to_json(books, file_name='data.json'):

        book_list = []
        for book in books:
            book_dict = {
                'title': book.title,
                'price': book.price,
                'rating': book.rating,
                'availability': book.availability,
                'description': book.description
            }
            book_list.append(book_dict)

        with open(file_name, 'w') as json_file:
            json.dump(book_list, json_file, indent=4)

    @staticmethod
    def print_books_info(books):
        """
        Used for debugging/printing result to the console.
        """
        for i in range(len(books)):
            print(f'Book {i + 1}:')
            print(f'Title: {books[i].title}')
            print(f'Price: {books[i].price}')
            print(f'Rating: {books[i].rating}')
            print(f'Availability: {books[i].availability}')
            print(f'Description: {books[i].description}')
            print()
