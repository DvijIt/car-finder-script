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

# Асинхронна функція для перевірки нових автомобілів
async def check_for_new_cars():
    saved_cars = load_cars_from_json()  # Завантажуємо збережені авто
    latest_cars = get_latest_cars()  # Отримуємо останні авто

    # Фільтрація нових автомобілів
    new_cars = [car for car in latest_cars if car['id'] not in saved_cars]
    # or car['price'] != saved_cars[car['id']]['price']
    if new_cars:
        print("Знайдено нові автомобілі:")
        for car in new_cars:
            # Зробити перегляд по латест карс
            status = 'Ціна змінилась' # if car['price'] != saved_cars[car['id']]['price'] else "Новий автомобіль"

            saved_cars[car['id']] = car
            print(f"Назва: {car['title']}, Ціна: {car['price']}, Дата: {car['date']}, Посилання: {car['link']}")

            # Можна додати логіку для відправлення в Telegram або інші дії
            message = f"{status}:\n\nНазва: {car['title']}\nЦіна: {car['price']} EUR\nДата: {car['date']}\nЛокація: {car['location']}\nПосилання: {car['link']}"
            await send_telegram_message(message)
        
        save_cars_to_json(saved_cars)  # Зберігаємо нові дані у файл
    else:
        print("Немає нових автомобілів")

    # while True:
    #     cars = get_latest_cars()
    #     if cars:
    #         for car in cars:
    #             car_id = car.get("id")
    #             car_price = car.get("price")
    #             car_title = car.get("title")
    #             car_location = car.get("location")
    #             car_link = car.get("link")
    #             car_date = car.get("date")

    #             # Перевірка, чи це новий автомобіль або змінилася ціна
    #             if car_id not in saved_cars or car_price != saved_cars[car_id]["price"]:
    #                 saved_cars[car_id] = car  # Оновлюємо запис автомобіля в JSON-даних
    #                 save_cars_to_json(saved_cars)  # Зберігаємо у файл

    #                 # Перевірка на час останньої відправки повідомлення
    #                 if last_sent_time is None or datetime.now() - last_sent_time > timedelta(days=1):
    #                     last_sent_time = datetime.now()
    #                     message = f"Новий автомобіль:\n\nНазва: {car_title}\nЦіна: {car_price} EUR\nДата: {car_date}\nЛокація: {car_location}\nПосилання: {car_link}"
    #                     await send_telegram_message(message)
    #                     print("Відправлено новий автомобіль у Telegram:", message)

    #     # Затримка на 30 секунд перед повторним запитом
    #     await asyncio.sleep(30)

# Основна функція для запуску асинхронного циклу
def main():
    asyncio.run(check_for_new_cars())

if __name__ == '__main__':
    main()
    # Після завершення обов'язково закрийте браузер
    driver.quit()

