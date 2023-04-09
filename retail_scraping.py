from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import pandas as pd
import time
import os
import re
from geopy.geocoders import Nominatim

FAIL_COUNT = 0

def findGeocode(city):
    # try and catch is used to overcome
    # the exception thrown by geolocator
    # using geocodertimedout  
    try:     
        # Specify the user_agent as your
        # app name it should not be none
        geolocator = Nominatim(user_agent="app_name") 
        loc = geolocator.geocode(city)
        return loc
    except GeocoderTimedOut:
        FAIL_COUNT += 1
        if FAIL_COUNT == 5:
            return None
        return findGeocode(city)

def scrape_locations():
    # Install chrome driver
    s=Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s)
    driver.maximize_window()
    addresses = []
    # Connect to URL
    store_URL = "https://www.lifestylestores.com/in/en/"
    driver.get(store_URL)
    # Wait for content to load
    time.sleep(5)
    # Search for store-locator hyperlink
    store_selector = driver.find_elements(By.CLASS_NAME, 'desk-top-storelocator')
    if store_selector:
        store_selector[0].click()
        # Wait for content to load
        time.sleep(5)
        # Search for scrollable list of all locations
        elements = driver.find_elements(By.CLASS_NAME, 'store-list-item')
        for e in elements:
            addr = e.find_element(By.TAG_NAME, 'address')
            addresses.append(addr.text)
    
    # last_height = driver.execute_script('return document.body.scrollHeight')
    time.sleep(5)

    footer = driver.find_elements(By.CLASS_NAME, 'list-unstyled')
    for foot in footer:
        ymsCompo = foot.find_elements(By.CLASS_NAME, 'yCmsComponent')
        for comp in ymsCompo:
            # print(comp)
            img_tag_data = comp.find_element(By.TAG_NAME, 'a')
            image_url = img_tag_data.get_attribute("href")
            image_title = img_tag_data.get_attribute("title")
            if image_title == 'Contact us':
                print(image_title, '->', image_url)
                # img_tag_data.click()
                break

    driver.get(image_url)
    time.sleep(5)
    detail = driver.find_element(By.ID, 'contact-info-box-05')
    timing = detail.find_element(By.ID, 'contact-section-info-03')
    # print(timing.text)
    var1 = timing.text
    contact = detail.find_element(By.CLASS_NAME, 'tel-link')
    var2 = contact.text
    # print(contact.text)
    # print(detail.get_attribute('innerHTML'))



    driver.quit()
    with open("store_locations.txt", "w") as f:
        for i in addresses:
            f.write(i+"\n")
    return var1, var2

def clean_address(address):
    if "Bhubneshwar" in address:
        address = address.replace("Bhubneshwar", "Bhubaneswar")
    if "Dist -" in address:
        address = address.replace("Dist -", "").strip()
    if "Ground and First Floor" in address:
        address = address.replace("Ground and First Floor", "")
    if "Upper Ground" in address:
        address = address.replace("Upper Ground", "")
    if "No 2 Survey NO 152-4 " in address:
        address = address.replace("No 2 Survey NO 152-4 ", "")
    if "1st 2nd & 3rd Floors Survey No 51-1A1A1" in address:
        address = address.replace("1st 2nd & 3rd Floors Survey No 51-1A1A1", "")
    if "D21 " in address:
        address = address.replace("D21 ", "")
    if " UG & FF- T.S No. 210 - R.S. 335" in address:
        address = address.replace(" UG & FF- T.S No. 210 - R.S. 335", "")
    if "D No. 10-28-1" in address:
        address = address.replace("D No. 10-28-1", "")
    if "NH 16 " in address:
        address = address.replace("NH 16 ", "")
    if "Opposite Lodhipur Fire Station." in address:
        address = address.replace("Opposite Lodhipur Fire Station.", "")
    if "R- " in address:
        address = address.replace("R- ", "")
    return address

def search_geocode(all_locations):
    for loc in all_locations:
        location = findGeocode(loc)
        if location is None:
            print("Not found.. ", loc)
            continue
        else:
            print("Saved.. ", loc)
            break
    if not location is None:
        lat = location.latitude
        long = location.longitude
    else:
        lat = -999
        long = -999
    return lat, long

def removeStoreName(locat_specific):
    ser = re.search("^lifestyle\sst", locat_specific, re.IGNORECASE)
    if ser:
        locat_specific = " ".join(locat_specific.split(" ")[2:])
    elif re.search("^lifestyle", locat_specific, re.IGNORECASE):
        locat_specific = " ".join(locat_specific.split(" ")[1:])
    return locat_specific


def fetch_geolocation(addresses):
    location_lat_long = []
    for location_ori in addresses:
        # almost all addresses are appended with "lifestyle stores", "lifestyle str", etc which is not useful
        # to search the geocodes hence, can be discarded
        location_ori = removeStoreName(location_ori)
        locat = location_ori.strip()
        # cleaning of addresses based on manual inspection
        locat = clean_address(locat)
        print(location_ori.strip(), '->', locat)

        # extracting generic search keys from address to fetch geocodes (city, state, country)
        loc_city = ",".join(locat.split(",")[-2:]).strip()
        loc_city_2 = ",".join(locat.split(",")[-3:]).strip()

        # extracting specific location from address
        locat_specific = locat.split(",")[0]

        # fixing spelling mistakes
        if "mal" in locat_specific.lower().split(" "):
            locat_specific = locat_specific.lower().replace("mal", "mall")
        
        final_location = locat_specific+", "+loc_city
        all_locations = [final_location, loc_city_2, loc_city]
        lat, long = search_geocode(all_locations)
        location_lat_long.append([location_ori, lat, long])
    return location_lat_long

def main():
    timing, contact = scrape_locations() 
    with open("store_locations.txt") as f:
        addresses = f.readlines()
    
    location_lat_long = fetch_geolocation(addresses)
    df = pd.DataFrame(location_lat_long, columns=['Location', 'Lat', 'Long'])
    df.loc[:, 'Store Name'] = 'Lifestyle Stores'
    df.loc[:, 'Timing'] = timing
    df.loc[:, 'Contact Number'] = contact
    df = df[['Store Name', 'Location', 'Lat', 'Long', 'Timing', 'Contact Number']]
    print(df.head())
    df.to_csv("Lifestyle_Stores.csv", index=False)

    

if __name__ == "__main__":
    main()