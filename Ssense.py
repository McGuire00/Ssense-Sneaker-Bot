import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import json
import sys
import time
import random


# Hard code checkout details at the bottom
# must have Ssense account
# clear cart before running bot otherwise you will get an error
# account may get flagged if ran too many times
# only works with shoes so far
# memberBlockedContactSsense response on checkout means Ssense blocked your account


def clock():
    current = datetime.now()
    clock_format = current.strftime('%I:%M:%S:%f')
    return str(clock_format) + " CST"


sizes = [6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5]

print(clock(), ':: Welcome')
email = input('Enter email associated with Ssense account... ')
password = input('Enter password... ')
product_link = input('Enter link to product... ')
shoe_size = input('Please enter shoe size. For random size just press enter ')
print()

if shoe_size == '':
    random_size = random.choice(sizes)
    shoe_size = random_size
    print(clock(), ':: Selecting random size {}'.format(random_size))


class Ssense:
    def __init__(self):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36'
        }
        self.url = product_link
        self.shoe_size = shoe_size
        self.session = requests.session()
        self.login()      # Must have Ssense account
        self.clear_cart() # Makes sure cart is empty and if not clears it
        self.get_sku()    # gets product sku needed to check inventory and atc
        self.get_sizes()  # checks if selected size is in stock
        self.atc()        # atc
        self.cart()       # gets cart info
        self.checkout()   # checkout

    def get_sku(self):
        headers = {
            'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding':'gzip, deflate, br',
            'accept-language':'en-US,en;q=0.9',
            'cache-control':'max-age=0',
            'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        }
        product_page = self.session.get(self.url, headers=headers)
        self.soup = bs(product_page.content, 'html.parser')

        try:
            # Ex Black NDSTRKT AM 95 Sneakers
            self.product_name = self.soup.find('h2', attrs={'class':'pdp-product-title__name s-text'}).text.strip()
            # Ex 211011M237203 sku for product
            self.product_sku = self.soup.find('div', attrs={'class':'s-column pdp-product-description'}).find_all('p', attrs={'class':'s-text'})[-1].text

        except AttributeError:
            # If you get this error Ssense has detected you are using a script adjust headers
            print(clock(), '::' ,self.soup.find('div', attrs={'class':'content'}).find('p').text.strip())
            sys.exit()

        else:
            print(clock(), ':: Getting product information for {}'.format(self.product_name))

    # gets list of all sizes given
    def get_sizes(self):
        found = 0
        size_list = self.soup.find_all('option')
        sz = []
        sz_sku = []
        for x in size_list[1:]:
            if x.text.strip() not in sz and x not in sz_sku:
                sz.append(x.text.strip())
                sz_sku.append(x['value'])

        sz.pop()  # removes 'SELECT A SIZE' at end of list
        size_run = ["\n".join("{} {}".format(x, y) for x, y in zip(sz, sz_sku))]
        self.sizes = size_run
        for x in size_run:
            for i in x.split('\n'):
                # prints out list of sizes with sku numbers
                if str(self.shoe_size) == i.split(' ')[1]:
                    self.size_sku = i.split(' ')[-1][-15:]  # sku for chosen size ie: 211011M23720301
                    self.shoe_info = i                      # US 8 = IT 41 - Only 1 remaining 8_211011M23720301
                    found += 1
                    print(clock(), ':: {}'.format(self.shoe_info))

        # executes if user selected size was not in size run
        # picks a random size
        if found == 0:
            random_size = random.choice([x for x in sizes if x != shoe_size])
            self.shoe_size = random_size
            print(clock(), ':: The size you selected is not in the size run. Choosing random size {}'.format(self.shoe_size))
            for x in size_run:
                for i in x.split('\n'):
                    # prints out list of sizes with sku numbers
                    if str(self.shoe_size) == i.split(' ')[1]:  # list of size run
                        self.size_sku = i.split(' ')[-1][-15:]  # sku for chosen size ie: 211011M23720301
                        self.shoe_info = i                      # US 8 = IT 41 - Only 1 remaining 8_211011M23720301
                        found += 1
                        print(clock(), ':: {}'.format(self.shoe_info))

    # checks inventory of all sizes
    def inventory(self):
        check_stock = self.session.get('https://www.ssense.com/api/product/inventory/{}.json'.format(self.product_sku), headers=self.headers)
        data = check_stock.json()
        return data  # returns all sizes and if in stock or not

    def atc(self):
        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36',
            'referer':self.url,
            'accept':'application/json',
            'accept-encoding':'gzip, deflate, br',
            'content-type':'application/json'
        }

        data = {
            'serviceType':'product-details',
            'sku':self.product_sku,
            'userId':'null',
        }
        try:
            carted = 0
            while not carted:
                atc_request = self.session.post('https://www.ssense.com/en-us/api/shopping-bag/{}'.format(self.size_sku), data=json.dumps(data), headers=headers)
                response = atc_request.json()
                if 'ProductOutOfStock' in response.values():
                    print(clock(), '::', response['code'])
                    # ROLLING PRINT FOR ATC RETRY
                    # CURRENTLY SET TO RETRY EVERY 5 SECONDS LOWER AT YOUR OWN RISK
                    for i in range(5):
                        sys.stdout.write("\r" + clock() + ' :: Retrying ATC in {} seconds...'.format(str(5 - i)))
                        time.sleep(1)
                    sys.stdout.write('\n')
                else:
                    carted += 1
        except:
            print(clock(), ':: error adding to cart')
            sys.exit()
        else:
            self.total = response['cart'].get('total')
            self.token = response['cart'].get('token')
            print(clock(), ':: cart quanitity = {}'.format(response['cart'].get('quantity')))
            print(clock(), ':: {} size {} has been added to your cart'.format(self.product_name, response['cart']['products'][0].get('size')))

    # Ssense first step of checkout is to login
    def login(self):
        headers = {
            'referer':'https://www.ssense.com/en-us/shopping-bag',
            'accept-encoding':'gzip, deflate, br',
            'content-type':'application/x-www-form-urlencoded; charset=utf-8',
            'accept':'application/json',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36',
            'origin':'https://www.ssense.com'
        }

        # Be careful, account can get banned if ran too many times
        # Login parameters
        info = {
            'email': email,                                # Ssense account email
            'password': password                           # Ssense account password
        }

        try:
            login_account = self.session.post('https://www.ssense.com/en-us/account/login', data=info, headers=headers)
        except:
            print(clock(), ':: Error logging into account. Account details might be wrong')
            sys.exit()
        else:
            self.user_id = login_account.json().get('id')  # might need this
            if info.get('email').lower() == login_account.json().get('email').lower():  # checks if email is in post request
                print(clock(), ':: Logged in')

    def cart(self):
        head = {
            'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36',
            'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding':'gzip, deflate, br',
            'upgrade-insecure-requests': '1'
        }
        cart_page = self.session.get('https://www.ssense.com/en-us/shopping-bag', headers=head)
        soup = bs(cart_page.text, 'html.parser')
        # cart_total = soup.find('span', attrs={'class':'price'})
        # cart_total = soup.find('div', attrs={'class':'s-column cart-items-total-line-item__value'}).find('span', attrs={'class':'s-text'}).text.strip()
        cart_total = soup.find('span', attrs={'class':'price'}).text.strip()
        # .find('span', attrs={'class':'s-text'}).text.strip()
        self.cart_price = cart_total[1:-7]

    # clears cart before running bot
    def clear_cart(self):
        head = {
            'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36',
            'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding':'gzip, deflate, br',
            'upgrade-insecure-requests': '1'
        }
        cart = self.session.get('https://www.ssense.com/en-us/shopping-bag', headers=head)
        soup = bs(cart.content, 'html.parser')
        try:
            table = soup.find('div', attrs={'class': 'table'})
            body = table.find('ul')
        # if nothing is in cart an Attribute 'nonetype' error is raised
        except AttributeError:
            print(clock(), ':: Cart already clear')
            print()
        else:
            cart_items = []
            for x in body.find_all('div', attrs={'class':'span7 shopping-item-description'}):
                # sku for every item in cart
                cart = x.find_all('a')[3].text
                cart_items.append(cart)
            print(clock(), ':: Clearing {} item(s) in your cart'.format(len(cart_items)))
            # loops through items in cart and deletes each item
            for product in cart_items:
                delete = self.session.delete('https://www.ssense.com/en-us/api/shopping-bag/{}'.format(product), headers=head)
            if delete.status_code == 200:
                print(clock(), ':: COMPLETE')
                print()

    def checkout(self):
        print(clock(), ':: Checking out')
        headers = {
            'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36',
            'referer':'https://www.ssense.com/en-us/checkout',
            'origin':'https://www.ssense.com',
            'accept':'application/json',
            'content-type':'application/json'

        }
        # Thought this was needed
        # tax_url = 'https://www.ssense.com/en-us/api/checkout/taxes.json?country_code=US&state_code=TX&sub_total={}&shipping=0&should_check_restriction=false&city=&postal_code=&address=&items={}'.format(self.cart_price, self.size_sku)
        # get_tax = self.session.get(tax_url, headers=headers)
        # tax_total = get_tax.json().get('total')
        start_checkout = self.session.get('https://www.ssense.com/en-us/checkout.json', headers=self.headers)
        csrf_token = start_checkout.json().get('csrf_token')

        # checkout payload adjust here accordingly
        checkout_payload = {
            '_csrf':csrf_token,
            'shippingAddress':{
                "id": self.user_id,
                "firstName": "",                                    # First Name
                "lastName": "",                                     # Last Name
                "company": "",                                      # Leave empty
                "address1": "",                                     # Shipping address
                "countryCode": "US",
                "stateCode": "",                                    # State
                "postCode": "",                                     # Zip Code
                "city": "",                                         # City
                "phone": ""                                         # Phone number
            },
            "shippingMethodId": 7,
            "shippingMethodKeyName": "express",
            "paymentMethod": "credit",
            "skus":[self.size_sku],
            "orderTotal": self.cart_price,
            "creditCardDetails":{
                "tokenizedCardNumber":"",                           # Credit card number
                "tokenizedSecurityCode":"",                         # CVV
                "expiryMonth":"",                                   # EXP month
                "expiryYear":"",                                    # EXP year
                "cardholderName":""
            },
            "billingAddress": {
                "id": self.user_id,
                "firstName": "",                                    # Enter exact same shipping detail from above
                "lastName": "",
                "company": "",
                "address1": "",
                "countryCode": "US",
                "stateCode": "",
                "postCode": "",
                "city": "",
                "phone": "",
                "isSameAsShipping": "true"
            },
            "paymentProcessor": "firstdatapayeezy"
        }

        submit_checkout = self.session.post('https://www.ssense.com/en-us/api/checkout/authorize', data=json.dumps(checkout_payload), headers=headers)
        print(clock(), ':: {}'.format(submit_checkout.json()))


shoe = Ssense()
