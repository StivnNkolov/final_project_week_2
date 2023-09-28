class Book:
    """
    Class for storing data about each book.
    """

    def __init__(self, title, price, rating, availability, description):
        self.title = title
        self.price = price
        self.rating = rating
        self.availability = availability
        self.description = description

        self.rating_converter_mapper = {
            'One': 1,
            'Two': 2,
            'Three': 3,
            'Four': 4,
            'Five': 5,
        }

    def __str__(self):
        return f"Title: {self.title}\n" \
               f"Price: {self.price}\n" \
               f"Rating: {self.rating}\n" \
               f"Description: {self.description}"
