import argparse
from bs4 import BeautifulSoup
import requests
import sys


class ArgumentParser:
    """
    Taking care for creating argument parser object, handling passed arguments
    and returning them in the needed format for later use.
    """
    sort_by_choices = ['rating', 'available', 'title', 'price']
    sorting_choices = ['ascending', 'descending']

    filter_choices = ['available', 'rating', 'price']
    filter_operators = ['<', '>', '=', '<=', '>=', '!=']

    page_url = 'https://books.toscrape.com/'

    genres_choices = []

    def __init__(self):
        """
        Mutually exclusive arguments are:
            -b (count of books to found)
            -t (search for book by title, only one)
            -w (search for book from list of book titles)
        """

        self.__parser = argparse.ArgumentParser(description='''
        This is tool to scrape books from http://books.toscrape.com/index.html.
        You have different options for filtering and manipulating the books.
        For more info type main.py -h
        ''')

        self.__mutually_exclusive_args_group = self.__parser.add_mutually_exclusive_group()
        self.__create_arguments()
        self.__extract_genres_from_page()

    def return_parsed_arguments(self):
        args = self.__parser.parse_args()
        for el in args.__dict__:
            if args.__dict__[el]:
                return args
        raise self.__parser.error('You must use at least one flag')

    @staticmethod
    def _custom_positive_int(argument):
        """
        Parsing and validating number of books to be scraped.
        :param argument: Single argument that we are taking from the command line
        :return: int
        """
        try:
            value = int(argument)
        except ValueError:
            raise argparse.ArgumentTypeError(f'Expected integer, got {argument!r}')

        if value <= 0:
            raise argparse.ArgumentTypeError(f'Books count must be integer number bigger than zero, got {value!r}')
        return value

    @staticmethod
    def _custom_sorting_list(argument):
        """
        Parsing and validating argument. Creating dict from it.
        Working with multiple sorting parameters.
        :param argument: Single argument that we are taking from the command line
        :return: list
        """

        try:
            value = str(argument)
        except ValueError:
            raise argparse.ArgumentTypeError(f'Expected string, got {argument!r}')
        argument_split = value.split(', ')

        extracted_sorting_options = [el.split(' ') for el in argument_split]

        if any(len(el) != 2 for el in extracted_sorting_options):
            raise argparse.ArgumentTypeError(
                f'You must provide sort-by criteria {ArgumentParser.sort_by_choices} and way of sorting {ArgumentParser.sorting_choices} (one or more separated by comma), got {argument}')

        result_list = []

        for sort_option_index in range(len(extracted_sorting_options)):
            sort_by, sorting = extracted_sorting_options[sort_option_index]

            if sort_by not in ArgumentParser.sort_by_choices:
                raise argparse.ArgumentTypeError(
                    f'Sort by must be between {ArgumentParser.sort_by_choices}, got {sort_by!r}')
            if sorting not in ArgumentParser.sorting_choices:
                raise argparse.ArgumentTypeError(
                    f'Sorting choices must be between {ArgumentParser.sorting_choices}, got {sorting!r}')
            result_list.append((sort_by, sorting))

        return result_list

    @staticmethod
    def _custom_filtering_list(argument):
        """
        Parsing and validating argument. Creating dict from it.
        :param argument: Single argument that we are taking from the command line
        :return: list of dictionaries that contain the info for every filter.
        """
        try:
            value = str(argument)
        except ValueError:
            raise argparse.ArgumentTypeError(f'Expected string, got {argument!r}')

        first_filters_split = value.split(', ')
        result = []
        for cur_filter in first_filters_split:
            split_data = cur_filter.split(' ')

            if len(split_data) != 3:
                raise argparse.ArgumentTypeError(
                    f'''One filter must consist of 3 elements:
                     filter choice {ArgumentParser.filter_choices},
                     filter operator {ArgumentParser.filter_operators},
                     number by your choice, separated by space.
                     Format: <choice> <operator> <value>
                    ''')

            filter_choice, filter_operator, filter_value = split_data

            if filter_choice not in ArgumentParser.filter_choices:
                raise argparse.ArgumentTypeError(
                    f'Filter choice must be between {ArgumentParser.filter_choices}, got {filter_choice}')
            if filter_operator not in ArgumentParser.filter_operators:
                raise argparse.ArgumentTypeError(
                    f'Filter operator must be between {ArgumentParser.filter_operators}, got {filter_operator}')

            try:
                price = int(filter_value)
            except ValueError:
                raise argparse.ArgumentTypeError(f'Filter value must be integer, got {filter_value!r}')

            if price < 0:
                raise argparse.ArgumentTypeError(f'Filter value must be zero or bigger, got {filter_value}')

            result.append({'filter_choice': filter_choice,
                           'filter_operator': filter_operator,
                           'filter_value': filter_value,
                           })
        return result

    def __create_arguments(self):
        """
        Template code from argparse library to create and set the arguments that are taken from the command line.
        :return: None
        """
        self.__mutually_exclusive_args_group.add_argument(
            '-b',
            '-books',
            type=self._custom_positive_int,
            dest='books_count',
            default=-1,
            help='Get given number of books'
        )

        self.__parser.add_argument(
            '-g',
            '--genres',
            type=str,
            nargs='+',
            choices=ArgumentParser.genres_choices,
            default=[],
            help='Search only in given genres'
        )

        self.__parser.add_argument(
            '-s',
            '--sorting',
            type=self._custom_sorting_list,
            dest='sorting_params',
            default=[('title', 'ascending')],
            help='Sort the books by some stats'
        )

        self.__parser.add_argument(
            '-f',
            '--filters',
            type=self._custom_filtering_list,
            dest='filtering_params',
            default=[],
            help='Filter books by given filters'
        )

        self.__parser.add_argument(
            '-d',
            '--description',
            type=str,
            nargs='+',
            default=[],
            help='Search books by given keywords found in the description'
        )

        self.__mutually_exclusive_args_group.add_argument(
            '-t',
            '--title',
            type=str,
            nargs=1,
            help='Search for a book by its name'
        )

        self.__mutually_exclusive_args_group.add_argument(
            '-w',
            '--wanted',
            type=str,
            nargs=1,
            help='Search books from JSON with titles.'
        )

    @classmethod
    def __extract_genres_from_page(cls):
        """
        Dynamically taking all genres from the actual webpage.
        Called internally, when we create instance of the class.
        Return: None
        """
        response = requests.get(ArgumentParser.page_url)
        document_parser = BeautifulSoup(response.text, 'html.parser')

        if response.status_code != 200:
            print(f'Server status code {response.status_code}')
            return sys.exit(1)

        genres_div_tag = document_parser.find('div', class_='side_categories')
        genres_names = genres_div_tag.select('ul li a')

        for genre in genres_names:
            cls.genres_choices.append(genre.text.strip())
