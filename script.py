from PyPDF2 import PdfReader, PdfWriter
import fitz
import cv2
from PIL import Image, ImageDraw, ImageOps
import pytesseract
import os
from itertools import combinations
import numpy as np
os.environ['TESSDATA_PREFIX'] = 'tesseract\tessdata'

class Subject:
    def __init__(self, name, points, grade=0):
        self.name = name
        self.points = points
        self.grade = grade

class OmissionCombo:
    def __init__(self, avg, omittedSubjectNames, points, reducedHebrewAvg):
        self.avg = avg
        self.omittedSubjectNames = omittedSubjectNames
        self.points = points
        self.reducedHebrewAvg = reducedHebrewAvg

def add_red_dot(image_path, x1, y1, x2, y2):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    radius = 1
    draw.ellipse([(x1 - radius, y1 - radius), (x1 + radius, y1 + radius)], fill="red")
    draw.ellipse([(x2 - radius, y2 - radius), (x2 + radius, y2 + radius)], fill="red")
    img.save('temp\\red_dot.png')

def remove_first_page(input_pdf, output_pdf):
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page_num in range(1, len(reader.pages)):  
        writer.add_page(reader.pages[page_num])

    with open(output_pdf, "wb") as out_file:
        writer.write(out_file)

def crop(image_path, x1, y1, x2, y2, output_path):
    img = Image.open(image_path)
    crop_box = (x1, y1, x2, y2)
    cropped_img = img.crop(crop_box)
    cropped_img.save(output_path)

def FindYCoordinate(large_image_path, small_image_path):
    large_image = cv2.imread(large_image_path)
    small_image = cv2.imread(small_image_path)
    result = cv2.matchTemplate(large_image, small_image, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    y_coordinate = max_loc[1]
    return y_coordinate

def extract_numbers(image_path):

    pil_img = Image.open(image_path)
    pil_img = pil_img.convert('L')
    pil_img = ImageOps.autocontrast(pil_img, cutoff=1)
    pil_img = pil_img.resize((pil_img.width * 10, pil_img.height * 10))
    img_np = np.array(pil_img)
    _, binary = cv2.threshold(img_np, 150, 255, cv2.THRESH_BINARY_INV)
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(binary, config=custom_config)
    numbers = []
    for line in text.strip().split('\n'):
        clean_line = ''.join(c for c in line if c.isdigit())
        if clean_line:
            numbers.append(clean_line)
    return numbers

def extract_names(image_path):

    pil_img = Image.open(image_path)
    pil_img = pil_img.convert('L')
    pil_img = ImageOps.autocontrast(pil_img, cutoff=1)
    pil_img = pil_img.resize((pil_img.width * 10, pil_img.height * 10))
    text = pytesseract.image_to_string(pil_img, lang="heb")
    words = []
    for line in text.strip().split('\n'):
        clean_line = ''.join(c for c in line)
        if clean_line:
            words.append(clean_line)
    return words

def ConvertFileToData(pdfPath):

    remove_first_page(pdfPath, "temp\\onepagediploma.pdf")
    pdf_document = fitz.open("temp\\onepagediploma.pdf")
    page = pdf_document.load_page(0)
    pix = page.get_pixmap()
    pix.save('temp\\diploma.png')

    crop("temp\\diploma.png", 204, 0, 405, 767, "temp\\raw_names.png")
    large_image_path = 'temp\\raw_names.png'
    small_image_path = 'reference.png'
    bottom_y = FindYCoordinate(large_image_path, small_image_path)
    
    crop("temp\\diploma.png", 204, 80, 405, bottom_y, "temp\\names.png")
    crop("temp\\diploma.png", 188, 80, 214, bottom_y, "temp\\points.png")
    crop("temp\\diploma.png", 58, 80, 78, bottom_y, "temp\\grades.png")

    names = [name[::-1] for name in extract_names('temp\\names.png')]
    points = list(map(int, extract_numbers('temp\\points.png')))
    grades = list(map(int, extract_numbers('temp\\grades.png')))

    subjectsCount = len(grades)
    subjectsArray = []

    for i in range(subjectsCount):
        name = names[i]
        point = points[i]
        grade = grades[i]
        subject = Subject(name, point, grade)
        subjectsArray.append(subject)

    return subjectsArray

def GetPointsSum(subjects):

    pointsSum = 0
    for subject in subjects:
        pointsSum += subject.points
    return pointsSum

def CalcAvg(subjects, Totalpoints):

    avg = 0 

    for subject in subjects:

        if subject.name == 'מתמטיקה' or subject.name[::-1] == 'מתמטיקה':
            avg += (subject.grade + 35) * subject.points
        
        elif (subject.name == 'אנגלית' or subject.name == 'מתמטיקה' or subject.name[::-1] == 'אנגלית' or subject.name[::-1] == 'מתמטיקה') and subject.points == 4 and subject.grade >=60:
            avg += (subject.grade + 12.5) * subject.points

        elif (subject.name in bonus25 or subject.name[::-1] in bonus25) and subject.points == 5 and subject.grade >=60:
            avg += (subject.grade + 25) * subject.points

        elif (subject.name in bonus or subject.name[::-1] in bonus) and subject.points == 4 and subject.grade >= 60:
            avg += (subject.grade + 10) * subject.points

        elif (subject.name in bonus or subject.name[::-1] in bonus) and subject.points == 5 and subject.grade >= 60:
            avg += (subject.grade + 20) * subject.points

        else:
            avg += subject.grade*subject.points
     
    avg = avg/Totalpoints
    return avg

def CalcAvgWithReducedHebrew(subjects, Totalpoints):

    avg = 0 

    for subject in subjects:

        if subject.name == 'מתמטיקה' or subject.name[::-1] == 'מתמטיקה':
            avg += (subject.grade + 35) * subject.points
        
        elif (subject.name == 'אנגלית' or subject.name == 'מתמטיקה' or subject.name[::-1] == 'אנגלית' or subject.name[::-1] == 'מתמטיקה') and subject.points == 4 and subject.grade >=60:
            avg += (subject.grade + 12.5) * subject.points

        elif (subject.name in bonus25 or subject.name[::-1] in bonus25) and subject.points == 5 and subject.grade >=60:
            avg += (subject.grade + 25) * subject.points

        elif (subject.name in bonus or subject.name[::-1] in bonus) and subject.points == 4 and subject.grade >= 60:
            avg += (subject.grade + 10) * subject.points

        elif (subject.name in bonus or subject.name[::-1] in bonus) and subject.points == 5 and subject.grade >= 60:
            avg += (subject.grade + 20) * subject.points

        elif (subject.name == 'עברית' or subject.name[::-1] == 'עברית') and subject.points == 3:
            avg += subject.grade * 2

        else:
            avg += subject.grade*subject.points
     
    avg = avg/(Totalpoints - 1)
    return avg

def CalcAvgWithOmission(subjects, Totalpoints):

    if(Totalpoints <= 20):
        return None   

    else:    

        best_avg = 0
        limit = Totalpoints - 20
        subjectsForOmission = subjects.copy()
        omissionCombos = []
        subjectsForOmission = [s for s in subjectsForOmission if s.points <= limit]
        allOptions = []

        canReduceHebrew = False
        for s in subjects:
            if (s.name == 'עברית' or s.name[::-1] == 'עברית') and s.points == 3:
                canReduceHebrew = True
                break

        for r in range(1, len(subjectsForOmission) + 1):
            for combo in combinations(subjectsForOmission, r):
                if (sum(s.points for s in combo) <= limit) and IsValidCombo(combo, subjects):
                    omissionCombos.append(list(combo))
            
        for combo in omissionCombos:

            omittedSubjectNames = []
            tempSubjects = subjects.copy()
            for subject in combo:
                tempSubjects.remove(subject)
                omittedSubjectNames.append(subject.name)

            postOmissionPoints = GetPointsSum(tempSubjects)
            avg = CalcAvg(tempSubjects, postOmissionPoints)
            best_avg = max(best_avg, avg)
            
            if canReduceHebrew == True:
                decreasedHebrewAvg = CalcAvgWithReducedHebrew(tempSubjects, postOmissionPoints)
                obj = OmissionCombo(avg, omittedSubjectNames, postOmissionPoints, decreasedHebrewAvg)
                allOptions.append(obj)
                best_avg = max(best_avg, decreasedHebrewAvg)
            else:
                obj = OmissionCombo(avg, omittedSubjectNames, postOmissionPoints, None)
                allOptions.append(obj)
                
        return best_avg
        # return allOptions

def IsMandatory(subject):
    if subject.name[::-1] in mandatorySubjects or subject.name in mandatorySubjects:
        return True
    else:
        return False

def IsForeignSubjectWithBadEnglish(subject, subjects):

    english = None
    for s in subjects:
        if s.name == 'אנגלית' or s.name[::-1] == 'אנגלית':
            english = s

    if (subject.name[::-1] in foreignLanguages or subject.name in foreignLanguages) and (english == None or english.point < 4):
        return True
    else:
        return False

def ContainsNonOmittableHistoricSubject(subjects, combo):

    nonHistoricCombo = True
    for s in combo:
        if s.name in historicSubjects or s.name[::-1] in historicSubjects:
            nonHistoricCombo = False
            break

    if nonHistoricCombo == True:
        return False
    
    else:
        # נצא מנקודת הנחה שמקצוע היסטורי אחד לפחות ברמת 2 יח"ל לפחות

        importantHistoricSubjectsInDiploma = [s for s in subjects if (s.name in historicSubjects or s.name[::-1] in historicSubjects) and s.points >= 2]
        importantHistoricSubjectsInCombo = [s for s in combo if (s.name in historicSubjects or s.name[::-1] in historicSubjects) and s.points >= 2]
        maxRemove = len(importantHistoricSubjectsInDiploma) - 1

        if len(importantHistoricSubjectsInCombo) > maxRemove:
            return True
        
        else:
            return False

def IsValidCombo(combo, subjects):

    isValid = True

    if ContainsNonOmittableHistoricSubject(subjects, combo):
        isValid = False

    else:

        for subject in combo:

            if IsMandatory(subject):
                isValid = False
            elif IsForeignSubjectWithBadEnglish(subject, subjects):
                isValid = False

    return isValid

bonus25 = ["אנגלית", "פיזיקה", "כימיה", "ביולוגיה", "ספרות", "היסטוריה", "תנייך"]
bonus = ["""אופטיקה יישומית""",
"""מדע חישובי""",
"""מתמטיקה""",
"""אזרחות""",
"""מדעי הבריאות""",
"""מערכות רפואיות""",
"""ניהול""",
"""מינהל וכלכלה""",
"""אלקטרואופטיקה""",
"""מערכות אלקטרו-אופטיות""",
"""מדעי ההנדסה""",
"""ניהול הייצור""",
"""אלקטרוניקה""",
"""אלקטרוניקה ומחשבים""",
"""אלקטרוניקה כללית ותקשורת""",
"""מערכות אלקט'""",
"""'מערכות אלקט""",
"""מערכות אלקטי""",
"""מערכות אלקטרוניות""",
"""מדעי החברה""",
"""חברה - חוק ומשפט""",
"""ניהול משאבי אנוש""",
"""אמנות""",
"""תולדות האמנות""",
"""אמנות המחול""",
"""מחול""",
"""אמנות שימושית""",
"""מדעי החיים""",
"""ניתוח מערכות וארגון קבצים""",
"""ארגון קבצים""",
"""ניהול התפעול""",
"""ניהול תעשייתי""",
"""ארגון וניהול הייצור""",
"""ביולוגיה""",
"""מיקרוביולוגיה""",
"""מדעי הטכנולוגיה""",
"""ספרות""",
"""ביולוגיה חקלאית""",
"""מדעי החיים וחקלאות""",
"""מוסיקה""",
"""ידיעת המוסיקה""",
"""תורת המוסיקה""",
"""מוסיקה רסיטל""",
"""מוסיקה קומפוזיציה""",
"""מוסיקה וקומפוזיציה""",
"""מוזיקה""",
"""ידיעת המוזיקה""",
"""תורת המוזיקה""",
"""מוזיקה רסיטל""",
"""מוזיקה קומפוזיציה""",
"""מוזיקה וקומפוזיציה""",
"""קומפוזיציה""",
"""עברית""",
"""בקרת מכונות""",
"""מחשבים""",
"""יסודות תורת המחשב""",
"""מחשבים ומערכות""",
"""מדעי המחשב""",
"""מחשוב ובקרה""",
"""עולם הערבים והאיסלאם""",
"""תולדות הערבים והאיסלאם""",
"""בקרת תהליכים""",
"""מערכות בקרת תהליכים""",
"""מחשבת ישראל""",
"""עיבוד נתונים אוטומטי""",
"""גיאוגרפיה""",
"""מטאורולוגיה""",
"""עם ועולם - מפגש בין תרבות ישראל לתרבויות העמים""",
"""עם ועולם, מפגש בין תרבות ישראל לתרבויות העמים""",
"""עם ועולם מפגש בין תרבות ישראל לתרבויות העמים""",
"""גיאולוגיה""",
"""מדעי כדור הארץ""",
"""מיכון חקלאי ומערכות""",
"""הבעה עברית""",
"""הבעה""",
"""מכטרוניקה""",
"""מיכשור ובקרה""",
"""מיכשור""",
"""בקרה ומחשבים""",
"""מיכשור ובקרה בהתיישבות""",
"""פיסיקה""",
"""פיזיקה""",
"""היסטוריה""",
"""היסטוריה + ידע העם והמדינה""",
"""ידע העם והמדינה""",
"""היסטוריה וידע העם והמדינה""",
"""היסטוריה, ידע העם והמדינה""",
"""מערכות ביוטכנולוגיות""",
"""ביוטכנולוגיה""",
"""ישומי ביוטכנולוגיה""",
"""פרקי מכונות וחוזק חומרים""",
"""תכנון פרקי מכונות""",
"""המטוס ומערכותיו""",
"""המסוק ומערכותיו""",
"""מערכות מיכשור ובקרה""",
"""קולנוע""",
"""אמנות הקולנוע""",
"""חינוך גופני""",
"""מכונות חקלאיות וטרקטורים""",
"""קירור ומיזוג אוויר""",
"""חישוב סטאטי וקונסטרוקציות""",
"""מכונות חום ותרמודינמיקה""",
"""שפה זרה""",
"""צרפתית""",
"""רוסית""",
"""ערבית""",
"""חקלאות""",
"""מכניקה""",
"""תורה שבעל פה (תושב"ע)""",
"""תורה שבעל פה (תושב''ע)""",
"""תורה שבעל פה (תושבייע)""",
"""תורה שבעל פה""",
"""תושב"ע""",
"""תושב''ע""",
"""תושבייע""",
"""חשמל""",
"""מערכות חשמל""",
"""תורת החשמל""",
"""מכניקה הנדסית""",
"""תאטרון""",
"""תולדות התאטרון""",
"""ספרות התאטרון""",
"""אמנות התאטרון""",
"""חשבונאות""",
"""מכשירים ופיקוד""",
"""תכנון הנדסי של מבנים""",
"""טכנולוגיה מוכללת""",
"""מנועי מטוסים ותרמודינמיקה""",
"""תכנון ותכנות מערכות""",
"""תכנות יישומים מנהליים – עבודת גמר""",
"""טכנולוגיית הבנייה""",
"""מערכות תקשורת ומיתוג""",
"""בזק טלקומוניקציה""",
"""תלמוד""",
"""כימיה""",
"""מערכות תוכנה וחומרה""",
"""תנ"ך""",
"""תנייך""",
"""תנ''ך""",
"""כימיה טכנולוגית""",
"""מערכות פיקוד""",
"""בקרה ומחשבים""",
"""מערכות בקרה ממוחשבות""",
"""מערכות אלקטרוניות""",
"""תיירות""",
"""תיירות ותפעול""",
"""לימודי הסביבה""",
"""מדעי הסביבה""",
"""מערכות פיקוד ובקרה""",
"""תקשורת""",
"""תקשורת המונים""",
"""תקשורת וחברה""",
"""דיפלומטיה ותקשורת בינלאומית""",
"""לימודי ארץ-ישראל""",
"""לימודי ארץ ישראל""",
"""מערכות תעופה ומנועים""",
"""מערכות תעופה""",
"""תרמודינמיקה""",
"""תרמודינמיקה טכנית""",
"""פילוסופיה""",
"""מורשת דרוזית""",
"""דת נוצרית""",
"""דת האסלאם"""]
mandatorySubjects = [
    "עברית",
    "אנגלית",
    "מתמטיקה",
    "אזרחות"
]
foreignLanguages= [
    "צרפתית",
    "רוסית",
    "ערבית"
]
historicSubjects= [
    "היסטוריה",
    "תולדות עם ישראל",
    "ידע העם והמדינה"
]

subjectsArray = ConvertFileToData('temp\\diploma.pdf')
pointsSum = GetPointsSum(subjectsArray)

omittedAvg = CalcAvgWithOmission(subjectsArray, pointsSum)
regularAvg = CalcAvg(subjectsArray, pointsSum)
reducedAvg = CalcAvgWithReducedHebrew(subjectsArray, pointsSum)

# for i in allOptions:
#     print(i.omittedSubjectNames,i.avg, ' || ', i.reducedHebrewAvg)
# print("original: ",( 2 * (93 + 0) + 2 * (89 + 0) + 2 * (89 + 0) + 2 * (95 + 0) + 2 * (90 + 0) + 5 * (98 + 25) + 5 * (87 + 35) + 5 * (96 + 25) + 5 * (100 + 20) + 5 * (82 + 20) ) / 35)