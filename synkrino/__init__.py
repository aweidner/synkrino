import html
import mimetypes

from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

import smtplib
import ssl
import sys
import filecmp

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

from skimage.measure import compare_ssim
import imutils
import cv2


class Screenshot(QWebEngineView):

    def capture(self, url, output_file):
        self.output_file = output_file
        self.load(QUrl(url))
        self.loadFinished.connect(self.on_loaded)
        # Create hidden view without scrollbars
        self.setAttribute(Qt.WA_DontShowOnScreen)
        self.page().settings().setAttribute(
            QWebEngineSettings.ShowScrollBars, False)
        self.show()

    def on_loaded(self):
        size = self.page().contentsSize().toSize()
        self.resize(size)
        # Wait for resize
        QTimer.singleShot(1000, self.take_screenshot)

    def take_screenshot(self):
        self.grab().save(self.output_file, b'PNG')
        self.app.quit()


def screenshot(website, output):
    app = QApplication(sys.argv)
    s = Screenshot()
    s.app = app
    s.capture(website, output)

    return app.exec_()


def baseline(website, output, crop=[0, -1, 0, -1]):
    screenshot(website, output) 

    base = cv2.imread(output)
    base = base[crop[0]:crop[1], crop[2]:crop[3]]
    cv2.imwrite(output, base)


def compare(website, base_location, crop=[0, -1, 0, -1]):
    output = "/tmp/c.png"
    diff_path = "/tmp/diff.png"

    screenshot(website, output)

    imageA = cv2.imread(output)
    imageA = imageA[crop[0]:crop[1], crop[2]:crop[3]]
    imageB = cv2.imread(base_location)

    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)

    (score, diff) = compare_ssim(grayA, grayB, full=True)
    diff = (diff * 255).astype("uint8")

    if score == 1.0:
        return False, output, None

    thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    for c in cnts:
        # compute the bounding box of the contour and then draw the
        # bounding box on both input images to represent where the two
        # images differ
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(imageA, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.rectangle(imageB, (x, y), (x + w, y + h), (0, 0, 255), 2)

    cv2.imwrite(diff_path, imageA)
    return True, output, diff_path


def email(email, image, from_email, from_email_password):
    title = "Website changed" 
    path = Path(image)
    me = Address("Address", *email.rsplit('@', 1))

    msg = EmailMessage()
    msg['Subject'] = "A watched website has changed" 
    msg['From'] = me
    msg['To'] = [me]
    msg.set_content('[image: {title}]'.format(title=title))  # text/plain
    cid = make_msgid()[1:-1]  # strip <>    
    msg.add_alternative(  # text/html
        '<img src="cid:{cid}" alt="{alt}"/>'
        .format(cid=cid, alt=html.escape(title, quote=True)),
        subtype='html')
    maintype, subtype = mimetypes.guess_type(str(path))[0].split('/', 1)
    msg.get_payload()[1].add_related(  # image/png
        path.read_bytes(), maintype, subtype, cid="<{cid}>".format(cid=cid))

    with smtplib.SMTP('smtp.gmail.com', timeout=10) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(from_email, from_email_password)
        s.send_message(msg)
