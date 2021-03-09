import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import json
import sys


# must have Ssense account
# clear cart before running bot otherwise you will get an error
# account may get flagged if ran too many times
# only works with shoes so far
# memberBlockedContactSsense response on checkout means Ssense blocked your account
# Hard code shipping info and payment info below
# Must hard code account details below
# Make sure you filled out shipping and billing areas below


def clock():
    current = datetime.now()
    clock_format = current.strftime('%I:%M:%S:%f')
    return str(clock_format) + " CST"


print(clock(), ':: Welcome')
product_link = input('Enter link to product...')
shoe_size = input('Please enter shoe size...')



class Ssense:
    def __init__(self):
        self.headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36'
        }
        self.url = product_link
        self.shoe_size = shoe_size
        self.session = requests.session()
        self.get_sku()    # gets product sku needed to check inventory and atc
        self.get_sizes()  # checks if selected size is in stock
        self.atc()        # atc
        self.login()      # Must have Ssense account
        self.cart()       # gets cart info
        self.checkout()   # checkout

    def get_sku(self):
        product_page = self.session.get(self.url, headers=self.headers)
        self.soup = bs(product_page.content, 'html.parser')
        shoe_info = self.soup.find('div', attrs={'class': 'pdp__redesign view'}).find('script')
        info = json.loads(shoe_info.contents[0])

        self.product_name = info.get('name')  # Ex Black NDSTRKT AM 95 Sneakers
        print(clock(), ':: Getting product information for {}'.format(self.product_name))
        self.product_sku = info.get('sku')    # Ex 211011M237203 sku for product

    # gets list of all sizes given
    def get_sizes(self):
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
            atc_request = self.session.post('https://www.ssense.com/en-us/api/shopping-bag/{}'.format(self.size_sku), data=json.dumps(data), headers=headers)
        except:
            print(clock(), ':: error adding to cart. EXITING')
            sys.exit()
        else:
            response = atc_request.json()
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
        # Insert account info here
        info = {
        'email':'',                             # Ssense account email
        'password':''                           # SSense account password
        }
        
        try:
            login_account = self.session.post('https://www.ssense.com/en-us/account/login', data=info, headers=headers)
        except:
            print(clock(), ':: Error logging into account')
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







