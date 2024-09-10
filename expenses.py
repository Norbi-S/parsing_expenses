from argparse import ArgumentParser
from pdf2image import convert_from_path
import cv2
import numpy as np
import pytesseract
import re
import pprint

parser = ArgumentParser()
parser.add_argument("filename", help="The name of the expenses file")
args = parser.parse_args()

filename = args.filename

pages = convert_from_path(filename)


def deskew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    return rotated


def extract_text_from_image(image):
    text = pytesseract.image_to_string(image)
    return text


extracted_text = []

for page in pages:
    preprocessed_image = deskew(np.array(page))
    text = extract_text_from_image(preprocessed_image)
    extracted_text.append(text.split("\n"))

# flattening list python way
extracted_text = [x for xs in extracted_text for x in xs]


def extract_expense(text_line):
    # tries to parse an expense line assuming it has this format
    # (date, expense description, price)
    # returns parsed data
    pattern = r"(\d\d\-\d\d\-\d\d) (.+) (\d+\.\d\d)"
    res = re.search(pattern, text_line)

    if res is None:
        return None

    return res.group(1), res.group(2), float(res.group(3))


expenses = {}
for line in extracted_text:
    ex = extract_expense(line)
    if ex is None:
        continue
    date, expense, price = ex
    if expense not in expenses:
        expenses[expense] = {"payments": [], "total": 0.0}

    expenses[expense]["payments"].append((date, price))
    expenses[expense]["total"] += price

total = sum([e["total"] for e in expenses.values()])

pprint.pp(expenses)
print("\nTotal (you should totally verify this!): ", total, "\n")
