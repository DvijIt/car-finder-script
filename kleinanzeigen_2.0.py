import asyncio
import json
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Bot
import time

# Налаштування
TOKEN = "7493276934:AAFUgPhdaQMGElAjZbSeYwvSEsIVvxCBJTE"
CHAT_ID = "780884613"

PRICE_FILTER_MIN = 1500
PRICE_FILTER_MAX = 3500
JSON_FILE = 'cars_data.json'

# Змінні для відстеження
last_car_id = None
last_sent_time = None
last_price = None

# Ініціалізація Telegram бота
bot = Bot(token=TOKEN)

# Запуск браузера через Selenium
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Асинхронна функція для відправлення повідомлення в Telegram
async def send_telegram_message(text):
    await bot.send_message(chat_id=CHAT_ID, text=text)

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

        date_added.replace("heute", "Сьогодні")

        # Локація
        location = article.find_element(By.CLASS_NAME, 'aditem-main--top--left').text
        
        # Парсинг ціни
        price = int(''.join(filter(str.isdigit, price)))

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

# Асинхронна функція для перевірки нових автомобілів
async def check_for_new_cars():
    global last_car_id, last_sent_time, last_price

    # Завантажуємо попередні автомобілі з JSON
    saved_cars = load_cars_from_json()

    while True:
        cars = get_latest_cars()
        if cars:
            for car in cars:
                car_id = car.get("id")
                car_price = car.get("price")
                car_title = car.get("title")
                car_location = car.get("location")
                car_link = car.get("link")
                car_date = car.get("date")

                # Перевірка, чи це новий автомобіль або змінилася ціна
                if car_id not in saved_cars or car_price != saved_cars[car_id]["price"]:
                    saved_cars[car_id] = car  # Оновлюємо запис автомобіля в JSON-даних
                    save_cars_to_json(saved_cars)  # Зберігаємо у файл

                    # Перевірка на час останньої відправки повідомлення
                    if last_sent_time is None or datetime.now() - last_sent_time > timedelta(days=1):
                        last_sent_time = datetime.now()
                        message = f"Новий автомобіль:\n\nНазва: {car_title}\nЦіна: {car_price} EUR\nДата: {car_date}\nЛокація: {car_location}\nПосилання: {car_link}"
                        await send_telegram_message(message)
                        print("Відправлено новий автомобіль у Telegram:", message)

        # Затримка на 30 секунд перед повторним запитом
        await asyncio.sleep(30)

# Основна функція для запуску асинхронного циклу
def main():
    asyncio.run(check_for_new_cars())

if __name__ == '__main__':
    main()

# Після завершення обов'язково закрийте браузер
driver.quit()
