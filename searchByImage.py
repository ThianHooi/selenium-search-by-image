from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions as sel_ex
import os
import sys
import time
from time import sleep
import urllib.parse
import urllib.request
from urllib.request import urlopen
from retry import retry
import argparse
import logging
import requests
import shutil
import validators
import uuid
import mimetypes

from pathlib import Path

googleImageURL = "https://www.google.com/imghp?hl=en"
searchByImageIconCss = "div.ZaFQO"
searchInputCss = "input#Ycyxxc"
similarImgButtonCss = "h3.GmE3X"

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger()
retry_logger = None

css_thumbnail = "img.Q4LuWd"
css_large = "img.n3VNCb"
css_load_more = ".mye4qd"
selenium_exceptions = (sel_ex.ElementClickInterceptedException,
                       sel_ex.ElementNotInteractableException, sel_ex.StaleElementReferenceException)


def isURLValid(stringURL):
    valid = validators.url(stringURL)
    return valid


def scroll_to_end(wd):
    wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")


@retry(exceptions=KeyError, tries=6, delay=0.1, backoff=2, logger=retry_logger)
def get_thumbnails(wd, want_more_than=0):
    """
    Get a list of thumbnails.

    Args:
        wd (WebDriver): Selenium Web Driver
        want_more_than (int, optional): The least numbers of images needed. Defaults to 0.

    Raises:
        KeyError: Not enough thumbnails

    Returns:
        [str]: A list of thumbnail elements
    """
    wd.execute_script(
        f"document.querySelector('{css_load_more}').click();")
    thumbnails = wd.find_elements_by_css_selector(css_thumbnail)
    thumbnails_count = len(thumbnails)
    if thumbnails_count <= want_more_than:
        raise KeyError("Not enough thumbnails")
    return thumbnails


def is_image_valid(imageURL, exclude_stock_photos=False):
    """
    Return true or false indicating image url is a valid URL to be downloaded.

    Args:
        imageURL (str): A string from image src
        exclude_stock_photos (bool, optional): 
        A Boolen variable indicating whether to exclude stock photos which might contain watermark.
        Defaults to False.

    Returns:
        Boolean: True or False
    """
    inavalidUrlDomain = [
        'https://encrypted-tbn0.gstatic.com/', 'https://c8.alamy.com/', 'https://media.gettyimages.com/', 'https://thumbs.dreamstime.com/', 'src="https://image.shutterstock.com/']

    if exclude_stock_photos:
        # True if url does not start with these URL domains
        isValid = (list(filter(imageURL.startswith, inavalidUrlDomain)) == [
        ]) and (imageURL.startswith("http"))
    else:
        isValid = imageURL.startswith("http")

    return isValid


@retry(exceptions=KeyError, tries=6, delay=0.1, backoff=2, logger=retry_logger)
def get_image_src(wd, exclude_stock_photos=False):
    """
    Get original image source when the image option is clicked.

    Args:
        wd (Selenium Web Driver): Selenium Web Driver

    Raises:
        KeyError: if no image source is found, raise error

    Returns:
        [str]: A list of image URLs
    """
    actual_images = wd.find_elements_by_css_selector(css_large)
    sources = []
    for img in actual_images:
        src = img.get_attribute("src")

        if is_image_valid(src, exclude_stock_photos=exclude_stock_photos):
            sources.append(src)

    if not len(sources):
        raise KeyError("No source found")

    return sources


@retry(exceptions=selenium_exceptions, tries=6, delay=0.1, backoff=2, logger=retry_logger)
def retry_click(el):
    el.click()


def get_images(wd, number_of_images=20, exclude_stock_photos=False, out=None):
    """
    1. Get numbers of thumbnails loaded. If not enough, scroll to the bottom.
    2. For each thumbnail, click on the thumbnail element, get the original image
    source URL.
    3. If cannot get the original image URL, get the small thumbnail URL.
    4. Print the URL into file specified.

    Args:
        wd (WebDriver): Selenium Web Driver       
        number_of_images (int, optional): Number of images needed. Defaults to 20.
        out (str, optional): File name to write images URLs. Defaults to None.

    Returns:
        [str]: A list of image URLs
    """
    thumbnails = []
    count = len(thumbnails)

    while count < number_of_images:
        scroll_to_end(wd)
        try:
            thumbnails = get_thumbnails(wd, want_more_than=count)
        except KeyError as e:
            logger.warning("Cannot load enough thumbnails")
            break
        count = len(thumbnails)

    sources = []
    for thumbnail in thumbnails:
        try:
            retry_click(thumbnail)
        except selenium_exceptions as e:
            logger.warning("main image click failed")
            continue

        thumbnail_ori_src = []
        try:
            thumbnail_ori_src = get_image_src(wd)
        except KeyError as e:
            pass

        if not thumbnail_ori_src:
            # if can't get original image src,
            # get the src of the thumbnail from the grid in Google Image
            thumbnail_grid_src = thumbnail.get_attribute("src")
            if not thumbnail_grid_src.startswith("data"):
                logger.warning(
                    "No source found for main image, using thumbnail")
                thumbnail_ori_src = [thumbnail_grid_src]
            else:
                logger.warning(
                    "No source found for main image, thumbnail is a data URL")

        for src in thumbnail_ori_src:
            # avoid duplicate image URL
            if not src in sources:
                sources.append(src)

        if len(sources) >= number_of_images:
            break

    # if output file is specified, write to file,
    # else just print to terminal
    if out and (out != "sys.stdout"):
        sourceFile = open(out, 'w')
        for src in sources:
            print(src, file=sourceFile)
        sourceFile.close()
    elif (out == "sys.stdout"):
        for src in sources:
            print(src, file=sys.stdout)

    return sources


def download_images(image_urls):
    """
    Download all images from a list of image_urls

    Args:
        image_urls ([str]): A list of image URLs
        use_UUID (bool, optional): 
        A boolean indicating whether to download images and name them using UUID.
        If false, will use the file name obtained from URL.
        Defaults to False
        .
    """
    logger.info("Starting to download images")
    downloaded_count = 0

    for image_url in image_urls:
        filename = uuid.uuid1()

        # Open the url image, set stream to True, this will return the stream content.
        r = requests.get(image_url, stream=True, allow_redirects=True)
        extension = mimetypes.guess_extension(
            r.headers.get('content-type', '').split(';')[0])

        # Check if the image was retrieved successfully
        if r.status_code == 200:
            # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
            r.raw.decode_content = True

            data_folder = Path("downloads/")
            savepath = data_folder / f'{str(filename)}{extension or ".jpg"}'

            # Open a local file with wb ( write binary ) permission.
            with open(savepath, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

            logger.info(f'Image sucessfully Downloaded: {str(savepath)}')
            downloaded_count += 1
        else:
            logger.info('Image Couldn\'t be retreived')
    logger.info(f"Downloaded {downloaded_count} images")


def search_by_image(driver, image_url, number_of_images=10, exclude_stock_photos=False, out=None):
    """
    Search Google Image by URL

    Args:
        driver ([WebDriver]): Selenium Web Driver 
        image_url (str): A URL of image used to search for more images
        number_of_images (int, optional): Number of images needed. Defaults to 10.
        out (str, optional): File name to write images URLs. Defaults to None.

    Returns:
        [str]: A list of image URLs
    """
    driver.get(googleImageURL)

    searchIcon = driver.find_element_by_css_selector(searchByImageIconCss)
    searchIcon.click()

    searchBox = driver.find_element_by_css_selector(searchInputCss)
    searchBox.send_keys(image_url)
    searchBox.send_keys(Keys.ENTER)

    try:
        similarImgButton = driver.find_element_by_css_selector(
            similarImgButtonCss)
        similarImgButton.click()
    except selenium_exceptions as e:
        raise e

    sources = get_images(driver, number_of_images=number_of_images,
                         exclude_stock_photos=exclude_stock_photos, out=out)
    return sources


def main():

    parser = argparse.ArgumentParser(
        description='Fetch image URLs and download images from Google Image Search.')

    parser.add_argument('image_url', type=str, help='image search URL')
    parser.add_argument('n', type=int, default=20,
                        help='number of images (approx)')
    parser.add_argument('--output', type=str, default="sys.stdout",
                        help='file to write URLs into')
    parser.add_argument('--exclude_stock', type=str, default=False,
                        help='Boolean to indicate whether to exclude stock photos. Default: False')

    args = parser.parse_args()

    if(isURLValid(args.image_url) is not True):
        raise Exception("URL is not valid")

    opts = Options()
    opts.add_experimental_option('excludeSwitches', ['enable-logging'])

    with webdriver.Chrome(executable_path="./drivers/chromedriver.exe", options=opts) as wd:
        sources = search_by_image(
            driver=wd, image_url=args.image_url, number_of_images=args.n, exclude_stock_photos=args.exclude_stock, out=args.output)

    if (len(sources)):
        download_images(sources)
    else:
        logger.info("No images to download")


main()
