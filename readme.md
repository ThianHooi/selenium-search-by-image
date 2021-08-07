# Selenium Search By Image

This repo is specifically written to utilise Google's search by image function and download visually similar images. 
This repo might be useful in collecting images that are visually similar to an image URL. 

---
## Usage

1. Activate the virtual environment
   * `seleniumVenv\Scripts\activate` in Windows
   * `source seleniumVenv/bin/activate` in Linux
2. Download the required packages ```pip install -r requirements.txt```
3. Make sure you have the correct version of Selenium in `drivers` folder. For more information, refer to [Selenium Official Doc](https://selenium-python.readthedocs.io/installation.html).
4. Start using!

### Example
```sh
python searchByImage.py "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Giraffe_Mikumi_National_Park.jpg/800px-Giraffe_Mikumi_National_Park.jpg" 5
```

Show help: 
```
$ python searchByImage.py -h
usage: searchByImage.py [-h] [--output OUTPUT] [--exclude_stock EXCLUDE_STOCK] image_url n

Fetch image URLs from Google Image Search.

positional arguments:
  image_url             image search URL
  n                     number of images (approx)

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT       file to write URLs into
  --exclude_stock EXCLUDE_STOCK
                        Boolean to indicate whether to exclude stock photos. Default: False
```

In order to output the downloaded image URLs into a text file, we can do so:
```sh
python searchByImage.py "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Giraffe_Mikumi_National_Park.jpg/800px-Giraffe_Mikumi_National_Park.jpg" 5 --output giraffe.txt
```

Sometimes Google image will show images from stock websites and they might have watermarks. In order to avoid downloading images from certain stock websites, you can include the `--exclude_stock` argument. Example:

```sh
python searchByImage.py "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Giraffe_Mikumi_National_Park.jpg/800px-Giraffe_Mikumi_National_Park.jpg" 5 --exclude_stock
```

