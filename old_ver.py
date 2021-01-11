from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import datetime
import openpyxl as excel
import mysql.connector
import copy
import re
import argparse
import sys
import time

INTERVAL = 120
WAIT = 300
CHAT_TIMEOUT = 7200 # 21600
CURRENT_NUMBER = "+62 852-1076-6438"

def main():
    pic = 1
    if len(sys.argv) not in [3,4,5]:
        print("Usage: python", sys.argv[0], "salesNumbers.txt", "contacts.xlsx")
        sys.exit()

    # Initialise Arguments
    parser = argparse.ArgumentParser(description='PyWhatsapp Guide')
    parser.add_argument(sys.argv[1])
    try:
        parser.add_argument(sys.argv[2])
        parser.add_argument(sys.argv[3])
    except:
        pass
    parser.add_argument('--chrome_driver_path', action='store', type=str, default='C:/bin/chromedriver', help='chromedriver executable path (MAC and Windows path would be different)')
    parser.add_argument('--message', action='store', type=str, default='', help='Enter the msg you want to send')
    parser.add_argument('--remove_cache', action='store', type=str, default='False', help='Remove Cache | Scan QR again or Not')
    args = parser.parse_args()

    global driver, mydb, mycursor
    
    # Read from files
    contactNames = loadExcel(sys.argv[2], 'A')
    contactNumbers = loadExcel(sys.argv[2], 'B')
    
    for i in range(len(contactNames)):
        contactNames[i] = contactNames[i].replace(" ","")
    
    contacts = {}
    for i in range(len(contactNames)):
        contacts[contactNames[i]] = contactNumbers[i]
        
    # Initialise WhatsApp
    driver = whatsapp_login(args.chrome_driver_path)
    clickName(0)
    sendMessage("starting")
    start = input("Press enter to start... type (n) not to use external Sales names (starts slower) ")
    driver.save_screenshot("logged.png")

    salesListNumbers = loadtxt(sys.argv[1])
    salesList = []
    masterList = []

    ignoreList = []
    print("Ignore List -->>", ignoreList)
    
    # Initialise MySql Connection
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "Test2000@@@@",
        database = "mydatabase"
    )
    mycursor = mydb.cursor(buffered=True)

    handler = {}
    timings = {}

    WebDriverWait(driver,WAIT).until(EC.presence_of_element_located((By.CLASS_NAME,"_3Tw1q")))
    # initialise
    for name in salesListNumbers:
        if start != "n":
            salesList = loadtxt(sys.argv[3])
            break
            
        # if gotoSavedContact(name) == -1:
        # driver.get("https://web.whatsapp.com/send?phone={}&text&source&data&app_absent".format(name.replace("+", "").replace("-","").replace(" ","")))
        inputbox = driver.find_elements_by_xpath('//*[@contenteditable="true"]')[0]
        inputbox.send_keys(name)
        inputbox.send_keys(Keys.RETURN)
        
        # sendMessage("Hello! The Corporate WhatsApp Service has been initialised.")
        
        salesList.append(driver.find_element_by_class_name("YEe1t").text)
        
    salesListCount = len(salesList)
    salesListList = []
    tempList = []
    for i in range(salesListCount):
        tempList.append(salesList[i])
        if (i + 1) % 5 == 0 or (i + 1) == salesListCount:
            salesListList.append(copy.deepcopy(tempList))
            tempList = []
            
    # print("Sales List -->>", salesList)
    # print("Sales List -->>", salesListList)
    # print("Sales List Numbers -->>", salesListNumbers)
    masterList = copy.deepcopy(salesList)
    
    while True:
        try:
        
            time.sleep(10)
            numUnread = -1
            
            for k, v in list(timings.items()):
                # print(timings)
                # print(handler)
                if time.perf_counter() - v > CHAT_TIMEOUT:
                    if timings[k] not in masterList:
                        del timings[k]
                        del handler[k]
                        print("deleted")
                        print(handler)
                    

            unread = driver.find_elements_by_class_name("VOr2j")
            print("Number of incoming messages:", len(unread))
            
            try:
                if unread[0].text == "":
                    numUnread = int(input("Enter how many messages to forward: "))
            except:
                pass
            
            gotoUnsavedContact(CURRENT_NUMBER)
            
            now, times = [], []
            
            for i in range(INTERVAL // 60):
                now.append(datetime.datetime.now() - datetime.timedelta(minutes=(INTERVAL // 60 - i - 1)))
            
            x_arg = '//div[contains(@style,"Y(' + str(1*72) + 'px")]//div[@class="_2gsiG"]'
            currenttime = driver.find_element_by_xpath(x_arg).text
            currenttime = twelveToTwentyfour(currenttime)
            
            for i in range(INTERVAL // 60):
                hour, min = str(now[i].hour), str(now[i].minute)
                if len(hour) < 2:
                    hour = "0" + hour
                if len(min) < 2:
                    min = "0" + min
                times.append(hour + ":" + min)
                
                    
            if len(unread) == 0:
                print("Last message:", currenttime)
                print("This program is working as of", times[-1])
                    
                if currenttime in times:
                
                    nameIncoming = getName(1)
                    clickName(1)
                    print("no incoming name:", nameIncoming)

                    if nameIncoming in ignoreList + salesList:
                        gotoSavedContact(CURRENT_NUMBER)
                        continue
                        
                    gotoSavedContact(nameIncoming)
                    newMessageCount, pos = 0, 0
                    
                    while True:
                        try:
                            found = checkMessageInDatabase(nameIncoming, pos, left=False)
                        except:
                            break
                        if found:
                            break
                        newMessageCount += 1
                        pos -= 1
                        print(newMessageCount, pos)
                        
                    if newMessageCount > 0:
                        newMessageCount, pos = 0, 0
                            
                        gotoUnsavedContact(CURRENT_NUMBER)
                        
                        try:
                            sendMessage('[from Program to ' + nameIncoming + ']' + "---" + contacts[nameIncoming.replace(" ","")] + "---")
                        except:
                            sendMessage('[from Program to ' + nameIncoming + ']')
                        for item in salesListList:
                            forwardMessage(False, "Program", nameIncoming, "n/a", 1, item, False)
                            gotoSavedContact(CURRENT_NUMBER)
                            
                        gotoSavedContact(nameIncoming)
                        
                        while True:
                            try:
                                found = checkMessageInDatabase(nameIncoming, pos, left=False)
                            except:
                                break
                            if found:
                                break
                            newMessageCount += 1
                            pos -= 1
                        for item in salesListList:
                            forwardMessage(True, "Program", nameIncoming, "n/a", newMessageCount, item, False)
                            gotoSavedContact(nameIncoming)
                        
                    gotoSavedContact(nameIncoming)
                    newMessageCount, pos = 0, 0
                    
                    while True:
                        try:
                            found = checkMessageInDatabase(nameIncoming, pos, left=True)
                        except:
                            break
                        if found:
                            break
                        newMessageCount += 1
                        pos -= 1
                        
                    if newMessageCount > 0:
                        newMessageCount, pos = 0, 0
                            
                        gotoSavedContact(CURRENT_NUMBER)
                        
                        try:
                            sendMessage('[from ' + nameIncoming + ']' + "---" + contacts[nameIncoming.replace(" ","")] + "---")
                        except:
                            sendMessage('[from ' + nameIncoming + ']')
                        for item in salesListList:
                            forwardMessage(False, nameIncoming, "Program", "n/a", 1, item, False)
                            gotoSavedContact(CURRENT_NUMBER)
                            
                        gotoSavedContact(nameIncoming)
                        
                        while True:
                            try:
                                found = checkMessageInDatabase(nameIncoming, pos, left=False)
                            except:
                                break
                            if found:
                                break
                            newMessageCount += 1
                            pos -= 1
                        for item in salesListList:
                            forwardMessage(True, nameIncoming, "Program", "n/a", newMessageCount, item, True)
                            gotoSavedContact(nameIncoming)
                    gotoSavedContact(CURRENT_NUMBER)
                    
                time.sleep(2)
                continue

            unread = driver.find_elements_by_class_name("VOr2j")
            ele = unread[-1]

            # Determine incoming sender
            i  = 0
            nameIncoming = ''
            while True:
                if i == 30:
                    break
                if getUnread(i) is None:
                    i += 1
                    continue
                print("getUnread:", getUnread(i))
                nameIncoming = getName(i)
                print("nameIncoming:", nameIncoming)
                break

            if nameIncoming in ignoreList:
                gotoSavedContact(nameIncoming)
                continue

            # if nameIncoming in ignoreList:
                # continue
            
            if nameIncoming in salesList:

                tryclick = 0
                success = 1
                while True:
                    try:
                        tryclick += 1
                        if tryclick == 20:
                            success = 0
                            break
                        if numUnread == -1:
                            numUnread = int(ele.text)
                        # gotoUnsavedContact(nameIncoming)
                        ele.click()
                        break
                    except Exception as e:
                        print(e)
                        continue
                if success == 0:
                    continue
                    
                gotoSavedContact(nameIncoming)
                    
                time.sleep(0.2)

                # Check if the last message was a reply
                # reply = driver.find_elements_by_xpath('(//div[@class="_274yw"])[last()]/div/div/div/div/div/div/div[2]')
                # reply = driver.find_elements_by_xpath('(//div[contains(@class, "_2hqOq")])[last()]//div[contains(@class, "j6ajL")]')
                    
                replied = driver.find_elements_by_xpath('(//div[contains(@data-id,"false")])[last()]//div[contains(@class, "_1Dook")]')
                if len(replied) == 0:
                    sendMessage("Message not sent. Please reply to a message!")
                    continue
                
                replied[0].click()
                time.sleep(3)
                
                messages = driver.find_elements_by_xpath('//div[contains(@data-id,"true")]')
                i = -1
                replyText = ""
                for _ in range(len(messages)):
                    print("index", i)
                    # x_arg = '(//div[contains(@data-id,"true")])[last()' + (str(i + 1) if i != -1 else "") + ']//*[@tabindex="0"]'
                    x_arg = '//div[contains(@data-id,"true")][last()' + (str(i + 1) if i != -1 else "") + '][@tabindex="0"]'
                    replyItem = driver.find_elements_by_xpath(x_arg)
                    # replyItem = driver.find_elements_by_xpath('.//*[@tabindex="0"]')
                    print("replyItem:", replyItem)
                    if len(replyItem) != 0:
                        try:
                            replyText = replyItem[0].find_element_by_xpath('.//*[contains(@class,"_1wlJG")]').text
                        except:
                            replyText = "Image/Video/File"
                        print("replyText:", replyText)
                        break
                    i -= 1
                
                while True:
                    print(i)
                    replytowho = messages[i].find_elements_by_xpath('.//*[contains(@class,"_1wlJG")]')
                    if len(replytowho) != 0:
                        if "[from" not in replytowho[0].text:
                            i -= 1
                            continue
                        replyNum = replytowho[0].text
                        break
                    i -= 1
                
                # try:
                    # replyNum = re.search(r"\[(.*?)\]", reply[-1].text).group(0)
                # except:
                    # sendMessage("Message not sent. Please reply again to the *from* message.")
                    # continue

                replyNum = replyNum.replace("[from ", "").replace("]", "").replace(" to ","")
                replyNum = re.sub(r'---[^)]*---', '', replyNum)
                print("replyNum:", replyNum)
                for name in salesList + ["Program"]:
                    if name in replyNum:
                        replyNum = replyNum.replace(name, "")
                # if replyNum == '':
                    # sendMessage("Message not sent. Please reply to the *from* message!")
                    # continue

                print(replyNum)

                if replyNum not in handler or nameIncoming == handler[replyNum] or nameIncoming in masterList:
                    
                    gotoSavedContact(CURRENT_NUMBER)
                    try:
                        sendMessage('[from ' + nameIncoming + ' to ' + replyNum + ']' + "---" + contacts[replyNum.replace(" ","")] + "---")
                    except:
                        sendMessage('[from ' + nameIncoming + ' to ' + replyNum + ']')
                    for item in salesListList:
                        forwardMessage(False, nameIncoming, replyNum, replyText, 1, item, False)
                        gotoSavedContact(CURRENT_NUMBER)

                    updatedUnread = gotoSavedContact(nameIncoming)
                    # print(updatedUnread)
                    if updatedUnread is not None:
                        numUnread += int(updatedUnread)
                        
                    forwardMessage(True, nameIncoming, replyNum, replyText, numUnread, [replyNum], True)
                    gotoUnsavedContact(nameIncoming)
                    for item in salesListList:
                        forwardMessage(False, nameIncoming, replyNum, replyText, numUnread, item, True)
                        gotoUnsavedContact(nameIncoming)
                    if nameIncoming not in masterList:
                        handler[replyNum] = nameIncoming 
                        timings[replyNum] = time.perf_counter()
                    print(handler)
                else:
                    gotoUnsavedContact(nameIncoming)
                    sendMessage("This customer is already being handled by " + handler[replyNum] + "!")
                continue
                
            gotoSavedContact(CURRENT_NUMBER)

            if nameIncoming not in handler:
                try:
                    sendMessage('[from ' + nameIncoming + ']' + "---" + contacts[nameIncoming.replace(" ","")] + "---")
                except:
                    sendMessage('[from ' + nameIncoming + ']')
                for item in salesListList:
                    forwardMessage(False, nameIncoming, "Program", "n/a", 1, item, False)
                    gotoSavedContact(CURRENT_NUMBER)
                
            else:
                for contact in [handler[nameIncoming]] + masterList:
                    gotoSavedContact(contact)
                    try:
                        sendMessage('[from ' + nameIncoming + ']' + "---" + contacts[nameIncoming.replace(" ","")] + "---")
                    except:
                        sendMessage('[from ' + nameIncoming + ']')
                # forwardMessage(False, 1, [handler[nameIncoming]], False)
            
            i = 0
            numUnread = 0
            while True:
                if i == 30:
                    break
                if getName(i) != nameIncoming:
                    i += 1
                    continue
                if getUnread(i) is None:
                    numUnread = 0
                    break
                numUnread = int(getUnread(i))
                clickName(i)
                break
                
            if numUnread == 0:
                gotoUnsavedContact(nameIncoming)
                continue
                            
            if nameIncoming not in handler:
                for item in salesListList:
                    gotoUnsavedContact(nameIncoming)
                    forwardMessage(True, nameIncoming, "Program", "n/a", numUnread, item, True)
            else:
                forwardMessage(False, nameIncoming, "Program", "n/a", numUnread, [handler[nameIncoming]] + masterList, True)

            time.sleep(2)

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            gotoUnsavedContact(CURRENT_NUMBER)
            try:
                driver.find_elements_by_class_name("_2OhFa")[0].click()
            except:
                pass
            print("Failed to send message.")
            print("Error:", e)
            # driver.save_screenshot(str(pic) + ".png")
            # pic = 0
            continue

    driver.close()
    driver.quit()
    

def loadtxt(filename):
    results = []
    with open(filename, "r") as f:
        data = f.read().splitlines()
        for line in data:
            results.append(line)
    return results


def gotoSavedContact(name):  
    i = 0       
    while True:
        if getName(i) != name:
            i += 1
            if i == 200:
                return -1
            continue
        unread = getUnread(i)
        clickName(i)
        break
    return unread
    
def gotoUnsavedContact(nameIncoming):
    inputbox = driver.find_elements_by_xpath('//*[@contenteditable="true"]')[0]
    inputbox.send_keys(nameIncoming)
    inputbox.send_keys(Keys.RETURN)


def sendMessage(message):
    try:
        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,'//*[@id="main"]/footer/div[1]/div[2]/div/div[2]')))
    except:
        print("Couldn't load page.")
        return

    input_boxes = driver.find_elements_by_xpath('//*[@id="main"]/footer/div[1]/div[2]/div/div[2]')
    input_box = input_boxes[0]
    input_box.send_keys(message)
    input_box.send_keys(Keys.RETURN)
    time.sleep(3)


def checkMessageInDatabase(nameIncoming, pos, left):
    now = datetime.datetime.now()
    
    numIndex = str(pos)
    if pos == 0:
        numIndex = ""
    
    if left:
        x_arg = '(//div[contains(@data-id,"false")])[last()' + numIndex + ']//div[@class="_1wlJG"]'
    else:
        x_arg = '(//div[contains(@data-id,"true")])[last()' + numIndex + ']//div[@class="_1wlJG"]'
    
    try:
        msgText = driver.find_element_by_xpath(x_arg).text
    except:
        msgText = "Image/Video/File"
        
    print(x_arg, "msgText length:", msgText)

    if left:
        msgtimeText = driver.find_elements_by_xpath('//div[contains(@data-id,"false")]//*[contains(@class, "_2JNr-")]')[pos - 1].text
    else:
        msgtimeText = driver.find_elements_by_xpath('//div[contains(@data-id,"true")]//*[contains(@class, "_2JNr-")]')[pos - 1].text
        
    hour = msgtimeText[0] + msgtimeText[1]
    minute = msgtimeText[-2] + msgtimeText[-1]
    
    sql = "SELECT * FROM messages WHERE hour = (%s) AND minute = (%s) AND message = (%s);"
    val = [hour, minute, msgText]
    
    mycursor.execute(sql, val)
    
    row = mycursor.fetchone()
    print(val, row)
    return row is not None

def forwardMessage(record, nameIncoming, receiver, messageText, messageNum, numbers, sent):

    albumNum = 0
    albums = driver.find_elements_by_xpath('//div[@class="_3dejV _2XJpe _7M8i6"]')
    # print("albumlen:",len(albums))
    if len(albums):
        albumNum = 3
        #albumNumText = driver.find_elements_by_xpath('//div[@class="_2iyx0"]/span')
        albumNumText = driver.find_elements_by_css_selector('._3ZYWe._2g59E')

        # print("albumnumtextlen:",len(albumNumText))
        if len(albumNumText):
            # print(albumNumText[-1].text)
            albumNum += (int(albumNumText[-1].text.replace('+','')) - 1)
            # print("albumNum:", albumNum)
            
    messageNum -= albumNum

    num = str((-1)*(messageNum - 1)) if messageNum > 1 else ''
    if sent:
        print("take from left")
        x_arg = '(//div[@class="tSmQ1"]/div[contains(@data-id,"false")]/div/div/div/div)[last()]'
    else:
        print("take from right")
        x_arg = '(//div[@class="tSmQ1"]/div[contains(@data-id,"true")]/div/div/div/div)[last()]'

    while True:
        action = ActionChains(driver)
        action.move_to_element(driver.find_element_by_xpath(x_arg)).perform()
        
        time.sleep(0.5)

        driver.find_element_by_xpath('//div[@data-js-context-icon="true"]').click()
        time.sleep(0.5)
    
        try:
            driver.find_element_by_xpath('//*[@title="Forward all"]').click()
        except:
            try:
                driver.find_element_by_xpath('//*[@title="Forward message"]').click()
                break
            except:
                videos = driver.find_elements_by_xpath('//*[contains(@class,"_3i3h7")]')
                print(len(videos))
                if len(videos):
                    videos[-1].click()
                    forwardxpath = '//div[contains(@title, "Forward")]'
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,forwardxpath)))
                    driver.find_element_by_xpath('//div[@title="Close"]').click()
                continue

    print (messageNum)
    if sent:
        msgtime = '(//div[@class="tSmQ1"]/div[contains(@data-id,"false")]/div/div/div/div[2])[last()]'
        # checkbox = driver.find_elements_by_xpath('//div[@class="z_tTQ"]/div[contains(@data-id,"false")]//div[@class="_2XWkx"]')
        checkbox = driver.find_elements_by_css_selector("div.message-in.focusable-list-item")
    else:
        msgtime = '(//div[@class="tSmQ1"]/div[contains(@data-id,"true")]/div/div/div/div[2])[last()]'
        # checkbox = driver.find_elements_by_xpath('//div[@class="z_tTQ"]/div[contains(@data-id,"true")]//div[@class="_2XWkx"]')
        checkbox = driver.find_elements_by_css_selector("div.message-out.focusable-list-item")
    
    if record:
        try:
            recordmessage(nameIncoming, receiver, messageText, sent, -1)
        except:
            pass

    print("checkboxlen:", len(checkbox))
    for i in range(messageNum - 1):
        # time.sleep(0.25)
        num = -1 * (i + 2)
        try:
            checkbox[num].click()
        except:
            break
        
        if record:
            recordmessage(nameIncoming, receiver, messageText, sent, num)
        
    print("click")
    
    try:
        driver.find_element_by_xpath('//button[@title="Forward messages"]').click()
    except:    
        driver.find_element_by_xpath('//button[@title="Forward message"]').click()
    input_box = driver.find_element_by_xpath('//div[@contenteditable="true"][1]')
    for number in numbers:
        input_box.clear()
        input_box.send_keys(number)
        time.sleep(0.5)
        input_box.send_keys(Keys.RETURN)
        time.sleep(0.4)
    driver.find_element_by_xpath('//div[@class="_3FwbN"]/div/div').click()
    time.sleep(3)
    

def recordmessage(nameIncoming, receiver, replyText, sent, num):
    current = datetime.datetime.now()
    
    numIndex = str(num + 1)
    if num == -1:
        numIndex = ""
        
    if sent:
        print("take from left")
        x_arg = '(//div[contains(@data-id,"false")])[last()' + numIndex + ']//div[@class="_1wlJG"]'
        try:
            msgtimeText = driver.find_elements_by_xpath('//div[contains(@data-id,"false")]//*[contains(@class, "_2JNr-")]')[num].text
        except:
            msgtimeText = "n/a"
    else:
        print("take from right")
        x_arg = '(//div[contains(@data-id,"true")])[last()' + numIndex + ']//div[@class="_1wlJG"]'
        try:
            msgtimeText = driver.find_elements_by_xpath('//div[contains(@data-id,"true")]//*[contains(@class, "_2JNr-")]')[num].text
        except:
            msgtimeText = "n/a"
    msgtimeText = twelveToTwentyfour(msgtimeText)
    
    try:
        msgText = driver.find_element_by_xpath(x_arg).text
    except:
        msgText = "Image/Video/File"
        
    # msgtimeText = driver.find_elements_by_class_name("_18lLQ")[num].text
        
    print(x_arg, "msgText length:", msgText)
    
    if "[from" not in msgText:
        hour = msgtimeText[0] + msgtimeText[1]
        minute = msgtimeText[-2] + msgtimeText[-1]   
        sql = "INSERT IGNORE INTO messages (date, month, year, sender, recipient, message_replied_to, hour, minute, message, sent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (current.day, current.month, current.year, nameIncoming, receiver, replyText, hour, minute, msgText, sent)
        mycursor.execute(sql, val)
        mydb.commit()
        print("mysql entry:", val, "recorded.")


def getName(pos):
    x_arg = '//div[contains(@style,"Y(' + str(pos*72) + 'px")]//div[@class="_3Tw1q"]'
    print("TEST", x_arg)
    try:
        incoming = driver.find_element_by_xpath(x_arg)
    except:
        return None
    # print(incoming.text)
    return incoming.text


def clickName(pos):
    x_arg = '//div[contains(@style,"Y(' + str(pos*72) + 'px")]//div[@class="_3Tw1q"]'
    try:
        incoming = driver.find_element_by_xpath(x_arg)
    except:
        return None
    i = 0
    while True:
        try:
            incoming.click()
            break
        except:
            i += 1
            if i == 20:
                break


def getUnread(pos):

    x_arg = '//div[contains(@style,"Y(' + str(pos*72) + 'px")]//*[@class="VOr2j"]'
    try:
        bubble = driver.find_element_by_xpath(x_arg)
    except:
        return None
    # print(bubble.text)
    return bubble.text
    
    
def loadExcel(fileName, col):
    lst = []
    file = excel.load_workbook(fileName)
    sheet = file.active
    firstCol = sheet[col]
    for cell in range(len(firstCol)):
        contact = str(firstCol[cell].value)
        # contact = "\"" + contact + "\""
        lst.append(contact)
    
    # print("Contacts list --> ", lst)
    return lst
    

def twelveToTwentyfour(currenttime):
    if "AM" in currenttime:
        if len(currenttime) == 7:
            currenttime = "0" + currenttime[0:4]
        else:
            currenttime = currenttime[0:5]
    elif "PM" in currenttime:
        if len(currenttime) == 7:
            currenttime = str(int(currenttime[0]) + 12) + currenttime[1:4]
        else:
            currenttime = str(int(currenttime[0:2]) + 12) + currenttime[2:5]
    if currenttime[0:2] == "12":
        currenttime = "00" + currenttime[2:8]
    if currenttime[0:2] == "24":
        currenttime = "12" + currenttime[2:8]
    
    return currenttime
    


def whatsapp_login(chrome_path):

    chrome_options = Options()
    chrome_options.add_argument("--user-data-dir=./User_Data_touress")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3641.0 Safari/537.36")
    
    driver = webdriver.Chrome(executable_path=chrome_path,options=chrome_options)
    
    # driver = ChromeRemote()
    print(driver.current_url)
    driver.save_screenshot("test.png")
    
    driver.get("https://web.whatsapp.com")
    time.sleep(2)
    driver.save_screenshot("login.png")

    try:
        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.CLASS_NAME,'_1MZWu')))
    except:
        print("Unable to login.")
        exit()

    
    print("QR scanned")

    return driver


if __name__ == "__main__":
    main()