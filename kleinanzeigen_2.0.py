import asyncio
import json
import os
from datetime import datetime, timedelta
#
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager
#
from telegram import Bot
import time
import threading

# Налаштування для Selenium (безголовний режим)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Вказуємо шлях до ChromeDriver (завантажте його з https://chromedriver.chromium.org/)
service = Service(executable_path="./chromedriver/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

# Запуск браузера через Selenium
# driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Налаштування
TOKEN = "7493276934:AAFUgPhdaQMGElAjZbSeYwvSEsIVvxCBJTE"
CHAT_ID = "780884613"

PRICE_FILTER_MIN = 1500
PRICE_FILTER_MAX = 3500
JSON_FILE = 'cars_data.json'

# Ініціалізація Telegram бота
bot = Bot(token=TOKEN)

# Поточна дата та дата, що дорівнює двом дням тому
two_days_ago = datetime.now() - timedelta(days=2)

# Функція для перетворення дати
def parse_date(date_str):
    if "Gestern" in date_str:
        # Якщо дата містить "Gestern" (вчора)
        return datetime.now() - timedelta(days=1)
    elif "Heute" in date_str:
        # Якщо дата містить "Heute" (сьогодні)
        return datetime.now()
    else:
        # Якщо формат дати стандартний (дд.мм.рррр)
        return datetime.strptime(date_str, "%d.%m.%Y")
    


# Асинхронна функція для відправлення повідомлення в Telegram
async def send_telegram_message(text):
    await bot.send_message(chat_id=CHAT_ID, text=text)

# Функція для збереження даних у JSON-файл
def save_cars_to_json(cars):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(cars, f, ensure_ascii=False, indent=4)

# Функція для завантаження автомобілів із JSON-файлу
def load_cars_from_json():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Функція для отримання останніх доданих автомобілів через Selenium
def get_latest_cars():
    url = "https://www.kleinanzeigen.de/s-autos/kia/hamburg/preis::3500/c216l9409r100+autos.ez_i:2005%2C2009+autos.fuel_s:diesel+autos.marke_s:kia+autos.model_s:sorento"
    driver.get(url)
    time.sleep(3)  # Затримка для завантаження сторінки

    cars = []
    
    # Котнейнер з автомобілями
    container = driver.find_element(By.ID, 'srchrslt-adtable')

    if container is None:
        print('Авто по цим фільтрам відсутні.')
        return
    
    # Наприклад, пошук всіх елементів, що містять дані про авто
    articles = driver.find_elements(By.CLASS_NAME, 'aditem')  # Приклад. Вкажіть правильний селектор
    
    for article in articles:
        # ID
        car_id = article.get_attribute('data-adid')

        # Назва
        title = article.find_element(By.CLASS_NAME, 'ellipsis').text

        # Ціна
        price = article.find_element(By.CLASS_NAME, 'aditem-main--middle--price-shipping--price').text

        # Посилання
        link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')

        # Дата додавання оголошення
        date_element = article.find_element(By.CLASS_NAME, 'aditem-main--top--right')
        date_added = date_element.text if date_element else "Дата не вказана"
        
        date_added = parse_date(date_added).strftime("%d.%m.%Y")

        # Локація
        location = article.find_element(By.CLASS_NAME, 'aditem-main--top--left').text
        
        # Парсинг ціни
        price = int(''.join(filter(str.isdigit, price)))
        
        if parse_date(date_added) >= two_days_ago:
            # Фільтрація по ціні
            if PRICE_FILTER_MIN <= price <= PRICE_FILTER_MAX:
                cars.append({
                    "id": car_id,
                    "title": title,
                    "price": price,
                    "location": location,
                    "link": link,
                    "date": date_added
                })

    return cars

def parseDateSavedCars():
    cars = load_cars_from_json()
    for car in cars.values():
        cars[car['id']]['date'] = parse_date(cars[car['id']]['date']).strftime("%d.%m.%Y")
        
    # print(cars)
    save_cars_to_json(cars)
    
# Асинхронна функція для перевірки нових автомобілів
async def check_for_new_cars_and_send():
    saved_cars = load_cars_from_json()  # Завантажуємо збережені авто
    latest_cars = get_latest_cars()  # Отримуємо останні авто

    cars_for_send = []

    for car in latest_cars:
        entity = car.copy()
        if car['id'] not in saved_cars:
            entity['status'] = 'new'
            cars_for_send.append(entity)
        else:
            if car['price'] != saved_cars[car['id']]['price']:
                entity['status'] = 'updated'
                cars_for_send.append(entity)
            else:
                entity['status'] = 'sent'

    if cars_for_send:
        statuses = { 'updated': 'Ціна змінилась', 'new': 'Новий автомобіль' }

        for car in cars_for_send:
            status = statuses.get(car['status'])
            message = f"\n{status}:\nНазва: {car['title']}\nЦіна: {car['price']} EUR\nДата: {car['date']}\nЛокація: {car['location']}\nПосилання: {car['link']}"
            car['status'] = 'sent'
            saved_cars[car['id']] = car
            print(message)
            # await send_telegram_message(message)
    else:
        print('No new or changed price car')
        
    save_cars_to_json(saved_cars) # Зберігаємо нові дані у файл

    # # Затримка на 30 секунд перед повторним запитом
    # await asyncio.sleep(30)


async def update_cars_database():
    saved_cars = load_cars_from_json()  # Завантажуємо збережені авто
    latest_cars = get_latest_cars()  # Отримуємо останні авто

    for car in latest_cars:
        if car['id'] not in saved_cars:
            car['status'] = 'new'
        else:
            if car['price'] != saved_cars[car['id']]['price']:
                car['status'] = 'update'
            else:
                car['status'] = 'sent'

        saved_cars[car['id']] = car

    save_cars_to_json(saved_cars) # Зберігаємо нові дані у файл
    

async def delete_old_cars():
    saved_cars = load_cars_from_json()  # Завантажуємо збережені авто
    
    if len(saved_cars) == 0:
        return

    # Фільтрація словника для залишення тільки елементів з датами від сьогодні і за 2 дні
    recent_entries = {
        key: value
        for key, value in saved_cars.items()
        if parse_date(value["date"]) >= two_days_ago
    }
    
    save_cars_to_json(recent_entries) # Зберігаємо нові дані у файл

async def send_cars_to_telegram():
    cars = load_cars_from_json()
    statuses = { 'updated': 'Ціна змінилась', 'new': 'Новий автомобіль' }
    for car in cars.values():
        status = statuses.get(car['status'])
        message = f"{status}:\nНазва: {car['title']}\nЦіна: {car['price']} EUR\nДата: {car['date']}\nЛокація: {car['location']}\nПосилання: {car['link']}"
        print(message)
        # await send_telegram_message(message)

# Основна функція для запуску асинхронного циклу
def main():
    # asyncio.run(update_cars_database())
    asyncio.run(delete_old_cars())
    asyncio.run(check_for_new_cars_and_send())
    
def second():
    asyncio.run(delete_old_cars())
    
if __name__ == '__main__':
    while True:
        print('\nRequest')
        main()
        time.sleep(30)
        
    driver.quit()
