import os
import time
from scrapy import Selector
from selenium import webdriver
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twocaptcha import TwoCaptcha
from selenium.webdriver.common.by import By


class ByPassCaptcha():
    def __init__(self):
        self.filepath = r'' #todo put path of script where image will download
        self.solver = TwoCaptcha("095ba510e3c7aa6195507a27f7b0824d")
        self.driver = webdriver.Chrome()
        self.get_captcha_image_url()

    def get_captcha_image_url(self):
        print('get_captcha_image_url')
        self.driver.get("https://www.rdv-prefecture.interieur.gouv.fr/rdvpref/reservation/demarche/4443/cgu")
        time.sleep(5)
        response = Selector(text=self.driver.page_source)
        image_url = response.css('#captchaFR_CaptchaImageDiv img::attr(src)').get()
        print(image_url,'===========')
        self.downloadable_captcha_image(image_url=image_url)

    def downloadable_captcha_image(self,image_url):

        print('downloadable_captcha_image')
        image_data_url = self.driver.execute_script(fr"""
            return fetch('{image_url}')
                .then(response => response.blob())""" + """
                .then(blob => {
                    return new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.onerror = reject;
                        reader.readAsDataURL(blob);
                    });
                })
                .catch(error => console.error(error));
        """)
        print(image_data_url)
        time.sleep(5)
        if image_data_url:
            print("Image data URL retrieved successfully.")
            self.save_image_from_data_url(image_data_url, 'captcha_image.png')
            self.solve_captcha()
        else:
            print("Failed to retrieve the image data URL.")
            self.get_captcha_image_url()

    def solve_captcha(self):
        print('solve_captcha')
        try:
            self.result = self.solver.normal(self.filepath)
            print("Here are the results --->", self.result)
            self.check_data()
        except:
            self.get_captcha_image_url()

    def check_data(self):
        print('check_data')
        self.driver.find_element(By.CSS_SELECTOR, 'input#captchaFormulaireExtInput').send_keys(self.result.get('code', ''))
        time.sleep(5)
        self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        time.sleep(5)
        if 'Aucun créneau disponible' in self.driver.page_source:

            self.driver.close()
        else:
            self.send_email()

    def save_image_from_data_url(self, data_url, output_path):
        print('save_image_from_data_url')
        header, encoded = data_url.split(",", 1)
        data = base64.b64decode(encoded)
        with open(output_path, 'wb') as f:
            f.write(data)

    def send_email(self):
        print('send_email')

        subject = "Slot Available"
        message = "Hello, The Slot Is Available"
        from_email = "" #todo put sender email here
        to_email = "" #todo put receiver email here
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = from_email
        smtp_app_password = "" #todo put receiver email appcode here

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

    def delete_image(self,):
        file_path = self.filepath
        try:
            # Attempt to delete the file
            os.remove(file_path)
            print(f"File '{file_path}' was deleted successfully.")
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' does not exist.")
        except PermissionError:
            print(f"Permission denied: Cannot delete the file '{file_path}'.")
        except Exception as e:
            print(f"An error occurred while trying to delete the file '{file_path}': {e}")


if __name__ == '__main__':
    process = ByPassCaptcha()
