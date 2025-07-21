from flask import Flask, request, render_template
import os
import cv2
from paddleocr import PaddleOCR
import numpy as np
import re
import difflib

app = Flask(__name__)   
ocr=PaddleOCR(use_angle_cls=True, lang='en') 

upload_folder = "uploads"
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)


def rotate_if_needed(image):
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE) if image.shape[0] > image.shape[1] else image

#Function to enhance the image quality
def enhance_image(image_path):
    img = rotate_if_needed(cv2.imread(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.0)
    sharp = cv2.addWeighted(enhanced, 2.0, blur, -1.0, 0)
    if sharp.shape[1] < 800:
        sharp = cv2.resize(sharp, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    out_path = os.path.splitext(image_path)[0] + "_enhanced.jpg"
    cv2.imwrite(out_path, sharp)
    return out_path

#def enhance_image(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    if img.shape[1] < 800:
        enhanced = cv2.resize(enhanced, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

    output = image_path.replace('.jpg', '_enhanced.jpg')
    cv2.imwrite(output, enhanced)
    return output

def is_like_address(line):
    words = line.lower().split()
    for word in words:
        ratio = difflib.SequenceMatcher(None, word, "address").ratio()
        if ratio > 0.5:   
            return True
    return False
#Function to render to index page 
@app.route('/')
def index():
    return render_template('aadhar2.html')    


#Used for submitting the image file using POST method
@app.route('/upload', methods=['POST'])
def upload():
    if 'front_image' not in request.files or 'back_image' not in request.files:
        return "No file uploaded"
    front_img = request.files['front_image']
    back_img = request.files['back_image']
    if front_img.filename == '' or back_img.filename == '':
        return "No selected file"

    front_path = os.path.join(upload_folder, front_img.filename)
    front_img.save(front_path)

    back_path = os.path.join(upload_folder, back_img.filename)
    back_img.save(back_path)

    enhanced_front_path = enhance_image(front_path)
    enhanced_back_path = enhance_image(back_path)

    front_result = ocr.ocr(enhanced_front_path, cls=True)
    back_result = ocr.ocr(enhanced_back_path, cls=True)
    
    front_texts = []
    for line in front_result:
        for word in line:
            text = word[1][0]
            front_texts.append(text)

    back_texts = []
    for line in back_result:
        for word in line:
            text = word[1][0]
            back_texts.append(text)

   #Name filtering
    for line in front_texts:
        line_clean=line.strip()
        lower_line=line_clean.lower()
        if any(keyword in lower_line for keyword in ['government','india','male','femake','dob','GOVEHENTOFNDA','gonehnuentofnda']):
            continue
        if not re.search(r'\d',line_clean) and len(line_clean) > 5:
            name = line_clean
            break

    #DOB filtering
    dob=""
    dob_found = False
    for item in front_texts:
        if "dob" in item.lower().replace(".", ""):
            match = re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', item)
            if match:
                dob = match.group()
                dob_found = True
                break
    if not dob_found:
        for item in front_texts:
            match = re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', item)
            if match:
                dob = match.group()
                break
   
    #Gender filtering
    gender=""
    for item in front_texts:
        lower_item=item.lower()
        if "male" in lower_item:
            gender="MALE"
            break
        elif "female" in lower_item:
            gender="FEMALE"
            break


    #Aadhar number filtering
    aadhar_number = ""
    for item in front_texts:
        match = re.search(r'(\d{4}\s?\d{4}\s?\d{4}|\d{12})', item.replace(" ", ""))
        if match:
            aadhar_number=match.group()
            break



    #Address filtering
    address = []
    flag=False
    for item in back_texts:
        lower_item=item.lower()
        if is_like_address(lower_item) or 'ci/o' in lower_item or 'cio' in lower_item or 'care of' in lower_item:
            flag=True
        if flag:
            if 'print_date' in lower_item or 'date of issue' in lower_item or 'issued on' in lower_item or 'print date' in lower_item:
                continue
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{1,2,3,4}', item):
                continue
            if re.search(r'\d{1}[/-]\d{2}[/-]\d{3}', item):
                continue
            if re.search(r'\d{4}\s?\d{4}\s?\d{4}', item):
                continue
            
            if 'Aadhaar-Aam Aadmi ka Adhikar'  in lower_item:
                continue
            address.append(item.strip())    
            if re.search(r"\b\d{6}\b", item):
                break

    address = ' '.join(address)
    if not address:
        address = "Address not found"

    #Output formatting
    return f"""
    <h1><br>Aadhar Card Details</br></h1>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>DOB:</strong> {dob}</p>
    <p><strong>Gender:</strong> {gender}</p>
    <p><strong>Aadhar Number:</strong> {aadhar_number}</p>
    <p><strong></strong> {address}</p>
    <a href="/">Upload another image</a>
    """

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')


