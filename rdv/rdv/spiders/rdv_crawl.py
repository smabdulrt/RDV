import base64
import pickle
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapy import Spider, Request, Selector, signals
from scrapy.utils.response import open_in_browser
from selenium import webdriver
from selenium.webdriver.common.by import By
from twocaptcha import TwoCaptcha


class RdvCrawlSpider(Spider):
    name = "rdv_crawl"
    is_cookies = True
    got_data = False

    def __init__(self):
        self.filepath = r''  # todo put path of script where image will download
        self.solver = TwoCaptcha("095ba510e3c7aa6195507a27f7b0824d")
        if not self.is_cookies:
            # options = webdriver.ChromeOptions()
            # options.add_argument("--headless=new")
            # self.driver = webdriver.Chrome(options=options)
            remote_url = "http://localhost:4444/wd/hub"

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            self.driver = webdriver.Remote(command_executor=remote_url,
                                      options=chrome_options)
            self.get_captcha_image_url()

    def get_captcha_image_url(self):
        print('get_captcha_image_url')
        self.driver.get("https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4443/cgu")
        time.sleep(5)
        # response = Selector(text=self.driver.page_source)
        # image_url = response.css('#captchaFR_CaptchaImageDiv img::attr(src)').get()
        # print(image_url,'===========')
        self.downloadable_captcha_image()

    def downloadable_captcha_image(self):

        print('downloadable_captcha_image')
        try:
            image = WebDriverWait(self.driver, 100).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#captchaFR_CaptchaImageDiv img')))
            time.sleep(5)
            image_data_url = self.driver.execute_script("""
                                var canvas = document.createElement('canvas');
                                canvas.width = arguments[0].width;
                                canvas.height = arguments[0].height;
                                var context = canvas.getContext('2d');
                                context.drawImage(arguments[0], 0, 0);
                                return canvas.toDataURL();
                            """, image)
            # image_data_url = self.driver.execute_script("""
            #     // Find the image element
            #     var image = document.querySelector('#captchaFR_CaptchaImageDiv img');
            #
            #     // Get the image data URL
            #     var canvas = document.createElement('canvas');
            #     canvas.width = image.width;
            #     canvas.height = image.height;
            #     var context = canvas.getContext('2d');
            #     context.drawImage(image, 0, 0);
            #     return canvas.toDataURL();
            # """)
            print(image_data_url)
            time.sleep(5)
            if image_data_url:
                print("Image data URL retrieved successfully.")
                self.save_image_from_data_url(image_data_url, 'captcha_image.png')
                self.solve_captcha()
            else:
                print("Failed to retrieve the image data URL.")
                self.get_captcha_image_url()
        except:
            self.get_captcha_image_url()


    def solve_captcha(self):
        print('solve_captcha')
        try:
            self.result = self.solver.normal("captcha_image.png")
            print("Here are the results --->", self.result)
            self.check_data()
        except:
            self.get_captcha_image_url()

    def check_data(self):
        print('check_data')
        self.driver.find_element(By.CSS_SELECTOR, 'input#captchaFormulaireExtInput').send_keys(self.result.get('code', ''))
        time.sleep(5)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(10)
        pickle.dump(self.driver.get_cookies(), open("cookies.pkl", "wb"))
        self.driver.close()

    def save_image_from_data_url(self, image_data_url, output_path):
        print('save_image_from_data_url')
        image_data = base64.b64decode(image_data_url.split(',')[1])

        with open(output_path, 'wb') as f:
            f.write(image_data)

    def start_requests(self):
        url = "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4443/creneau/"

        cookies = pickle.load(open("cookies.pkl", "rb"))
        cookies_str = ''
        for cookie in cookies:
            cookies_str += f"{cookie['name']}={cookie['value']}; "
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'cookie': f'{cookies_str}',
            'priority': 'u=0, i',
            'referer': 'https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4443/cgu',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        yield Request(url=url, callback=self.parse, headers=headers, cookies=cookies)

    def parse(self, response, **kwargs):
        if "error" in response.url:
            print("Cookies Expired!!!!")
            self.is_cookies = False

            remote_url = "http://localhost:4444/wd/hub"

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            self.driver = webdriver.Remote(command_executor=remote_url,
                                      options=chrome_options)
            self.get_captcha_image_url()
        else:
            self.got_data = True
            if 'Aucun créneau disponible' in response.text:
                print("no Slot FOund")
            else:
                self.send_email()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(RdvCrawlSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_idle, signal=signals.spider_idle)
        return spider

    def spider_idle(self, spider):
        if not self.got_data:
            url = "https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4443/creneau/"
            cookies = pickle.load(open("cookies.pkl", "rb"))
            cookies_str = ''
            for cookie in cookies:
                cookies_str += f"{cookie['name']}={cookie['value']}; "
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'cookie': f'{cookies_str}',
                'priority': 'u=0, i',
                'referer': 'https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4443/cgu',
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            yield Request(url=url, callback=self.parse, headers=headers, cookies=cookies, dont_filter=True)

    def send_email(self):
        print('send_email')

        subject = "Slot Available"
        message = "Hello, The Slot Is Available"
        from_email = ""  # todo put sender email here
        to_email = ""  # todo put receiver email here
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = from_email
        smtp_app_password = ""  # todo put receiver email appcode here

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        try:
            # Set up the SMTP server
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Enable security
                server.login(smtp_user, smtp_app_password)  # Log in to the SMTP server using the App Password
                text = msg.as_string()  # Convert the message to a string
                server.sendmail(from_email, to_email, text)  # Send the email
                print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
        pass
