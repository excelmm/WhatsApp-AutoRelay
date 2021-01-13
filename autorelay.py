from pymongo.mongo_client import MongoClient
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from time import sleep
import datetime
import openpyxl as excel
import re
import sys

CURRENT_NUMBER = "+62 812-9749-9150" # Insert your number here
DATADIR = "test" # To indicate which datadir WhatsApp uses
IGNORE_LIST = ["tpyramid", "uea", "universe"] + [CURRENT_NUMBER] # Contacts to ignore

INTERVAL = 7 # Seconds per cycle
WAIT = 300 # Wait for elements to show
NAME_BLOCKS_TO_SCAN = 10 # How many name blocks to scan per loop
MESSAGE_BLOCKS_TO_SCAN = 30 # How many message blocks to scan per chat
MESSAGE_LENGTH_LIMIT = 500 # How many characters to limit when entering message in database

# File Reader object
class FileReader:

    def readTxt(filename):
        results = []
        with open(filename, "r") as f:
            data = f.read().splitlines()
            for line in data:
                results.append(line)
        return results
    
    def readExcel(filename, column):
        lst = []
        file = excel.load_workbook(filename)
        sheet = file.active
        firstCol = sheet[column]
        for cell in range(len(firstCol)):
            contact = str(firstCol[cell].value)
            # contact = "\"" + contact + "\""
            lst.append(contact)
        
        return lst

# Name Block object
class NameBlock:

    def __init__(self, element):
        self.element = element
        self.name = self.element.find_element_by_xpath(".//*[contains(@class, '1hI5g')]").text
        self.time = self.element.find_element_by_xpath(".//*[contains(@class, '_2gsiG')]").text
        self.unreadBubble = self.element.find_elements_by_xpath(".//*[contains(@class, 'VOr2j')]")
        self.unread = True if len(self.unreadBubble) > 0 else False
        if self.unread: self.numUnreadMessages = (int(self.unreadBubble[0].text) if self.unreadBubble[0].text != "" else 2)
        else: self.numUnreadMessages = 0

# Message Block object
class MessagesBlock:

    name = None
    element = None
    time = None
    hour = None
    minute = None
    state = None
    text = None
    repliedMessage = None
    repliedTo = None
    

    def __init__(self, name, element):
        self.name = name
        self.element = element
        self.timeElements = element.find_elements_by_xpath('.//*[contains(@class, "_2JNr-")]')

        # If it is indeed a message block (it will have a time element)
        if len(self.timeElements):
            self.time = twelveToTwentyfour(self.timeElements[0].text)
            self.hour = int(self.time[:2])
            self.minute = int(self.time[3:])

            # Check if message is incoming or outgoing
            self.state = "incoming" if len(driver.find_elements_by_xpath('//*[contains(@class,"in")][@tabindex="0"]')) else "outgoing"

            # Check if the message has text
            self.textExists = True if len(element.find_elements_by_xpath('.//*[contains(@class, "_1wlJG")]')) else False
            self.text = element.find_element_by_xpath('.//*[contains(@class, "_1wlJG")]').text if self.textExists else "Image/Video/File"

            # Check if replied message exists
            self.repliedMessageExists = True if len(element.find_elements_by_xpath('.//*[contains(@class, "i8New")]')) else False
            self.repliedMessageIsText = True if len(element.find_elements_by_xpath('.//*[contains(@class, "_1Dook")]')) else False
            if self.repliedMessageExists: 
                self.repliedMessage = element.find_element_by_xpath('.//*[contains(@class, "i8New")]').text if self.repliedMessageIsText else "Image/Video/File"
                self.repliedTo = self.repliedMessage.split('\n')[0]
                self.repliedMessage = ''.join(self.repliedMessage.split('\n')[1:])
            else: 
                self.repliedMessage = None
                self.repliedTo = None

    def printMessage(self):
        print("name: " + self.name)
        print("time: " + self.time)
        print("text: " + self.text)
        print("state: " + self.state)
        if self.repliedMessage: print("repliedMessage: " + self.repliedMessage)
        if self.repliedTo: print("Replied to: " + self.repliedTo)
        print()


# Main function
def main():

    if len(sys.argv) == 1: sys.exit("Please enter arguments")

    # Setup driver and contacts
    global driver, collection, salesNames, contacts, salesDict
    driver = setupDriver()
    collection = setupMongoDB()
    salesNames, salesNumbers, contacts, salesDict = setupContacts(sys.argv[1], sys.argv[2], sys.argv[3])
    
    # Start program (wait for blue double tick before starting)
    sendMessage(CURRENT_NUMBER, "starting")
    try: firstLoopMessages = int(input("Enter how many messages to get on first loop (also starts the program): "))
    except: firstLoopMessages = NAME_BLOCKS_TO_SCAN
    firstLoop = True
    unreadNameBlocks = {}
    namesToRemove = []

    # Loop to keep program on
    while True:
        try:
            for i in namesToRemove: unreadNameBlocks.pop(i)
            namesToRemove = []
            goToContact(CURRENT_NUMBER)
            if not firstLoop: sleep(INTERVAL)

            # Get a large number of unread name blocks at first loop (perhaps after the program has not been running)
            newUnreadNameBlocks = getAllUnreadNameBlocks(NAME_BLOCKS_TO_SCAN) if not firstLoop else getAllUnreadNameBlocks(firstLoopMessages)
            unreadNameBlocks.update(newUnreadNameBlocks)
            firstLoop = False

            if len(unreadNameBlocks) == 0:
                print("dsf")
                nameBlocks = getAllNameBlocks(NAME_BLOCKS_TO_SCAN) if firstLoop else getAllNameBlocks(2)
                for name in nameBlocks:
                    unreadMessages = []
                    for messageBlock in getAllMessagesBlocks(name, 5):
                        if firstLoop: recordMessage(name, messageBlock)
                        if not messageInDatabase(name, messageBlock): unreadMessages.append(messageBlock)
                    numIncoming = len([i for i in unreadMessages if i.state == 'incoming'])
                    numOutgoing = len(unreadMessages) - numIncoming
                    forwardProgramDetected(name, numIncoming, True, salesNames)
                    forwardProgramDetected(name, numOutgoing, False, salesNames)

                continue

            for name, nameBlock in unreadNameBlocks.items():

                namesToRemove.append(name)

                # Get number of unread messages
                numUnread = nameBlock.numUnreadMessages
                if not numUnread: continue

                if any(name in i for i in salesNames): # If incoming name found in salesList
                    forwardSales(name, numUnread, True, salesNames)
                else:
                    forwardCustomer(name, numUnread, True, salesNames)
                    
        except (KeyboardInterrupt, SystemExit):
            raise 
        except Exception as e:
            raise
            print(e)
            continue

    
    driver.close()

# Send a message by typing
def sendMessage(name, message):
    goToContact(name)
    
    try: WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,"//footer//*[@contenteditable='true']")))
    except: return

    input_box = driver.find_element_by_xpath("//footer//*[@contenteditable='true']")
    input_box.send_keys(message)
    input_box.send_keys(Keys.RETURN)
    sleep(1)

# Forward messages from sales team
def forwardSales(name, numUnread, fromLeft, numberSet):

    for index in reversed(range(numUnread)):

        goToContact(name)

        # Check if sales team replied properly
        replied_x_arg = '(//*[contains(@class,"in")][last()' + (str(-1 * (index)) if index != 0 else "") + '])//div[contains(@class, "_1Dook")]'
        
        # replied = driver.find_elements_by_xpath('(//div[contains(@data-id,"false")])[last()]//div[contains(@class, "_1Dook")]')
        replied = driver.find_elements_by_xpath(replied_x_arg)
        if len(replied) == 0:
            sendMessage(name, "Message not sent. Please reply to a message!")
            return
        
        replied[-1].click()
        sleep(2)
        messages = driver.find_elements_by_xpath('//div[contains(@data-id,"true")]')

        # Find the replied to message
        i = -1
        replyText = ""
        replyToWho = ""

        for _ in range(len(messages)):

            # Try to locate the chatbox that has a different color (meaning it was the one that is highlighted when reply message is clicked)
            x_arg = '//div[contains(@data-id,"true")][@tabindex="0"][last()' + (str(i + 1) if i != -1 else "") + ']'
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH,x_arg)))
            replyItem = driver.find_elements_by_xpath(x_arg)

            # When located
            if len(replyItem) != 0:

                # If reply was correct
                try:
                    pattern = re.compile(r"\[(?:.*to|from) (.*)\]")
                    replyToWho = pattern.match(replyItem[0].find_element_by_xpath('.//*[contains(@class,"_1wlJG")]').text).group(1)
                except: 
                    sendMessage(name, "Message not sent. Please reply to the from message!")
                    return
                break
            i -= 1

        # print(replyText := messages[i + 1].find_element_by_xpath('.//*[contains(@class,"_1wlJG")]').text)
    
        # To reset mysterious WhatsApp message targeting bug
        index = index - 1 if index == 0 else index

        recipientMessage = "[from " + name + " to " + replyToWho + "]"
        recipientMessage += "---" + contacts[replyToWho] + "---" if replyToWho in contacts else ""
        recipientMessage += " Replying to:"
        sendMessage(CURRENT_NUMBER, recipientMessage)
        for numbers in numberSet:
            forwardMessage(CURRENT_NUMBER, 1, 0, False, numbers)
            try: forwardMessage(replyToWho, 1, 0, True, numbers)
            except:
                sendMessage(CURRENT_NUMBER, "*Couldn't find replied to message.*")
                forwardMessage(CURRENT_NUMBER, 1, 0, False, numbers)
            forwardMessage(name, 1, index + 1, fromLeft, [replyToWho])
            forwardMessage(name, 1, index + 1, fromLeft, numbers)
        
# Forward messages from customer
def forwardCustomer(name, numUnread, fromLeft, numberSet):
    
    recipientMessage = "[from " + name + "]"
    recipientMessage += "---" + contacts[name] + "---" if name in contacts else ""
    sendMessage(CURRENT_NUMBER, recipientMessage)
    for numbers in numberSet:
        forwardMessage(CURRENT_NUMBER, 1, 0, False, numbers)
        forwardMessage(name, numUnread, 0, fromLeft, numbers)
       
# Forward messages from customer
def forwardProgramDetected(name, numUnread, fromLeft, numberSet):
    
    if fromLeft:
        if any(name in i for i in salesNames): # If incoming name found in salesList
            forwardSales(name, numUnread, True, numberSet)
        else:
            forwardCustomer(name, numUnread, True, numberSet)
    else:
        recipientMessage = "[from Program to " + name + "]"
        recipientMessage += "---" + contacts[name] + "---" if name in contacts else ""
        sendMessage(CURRENT_NUMBER, recipientMessage)
        for numbers in numberSet:
            forwardMessage(CURRENT_NUMBER, 1, 0, False, numbers)
            forwardMessage(name, numUnread, 0, False, numbers)

# Forward messages
def forwardMessage(name, numUnread, beginningIndex, fromLeft, numbers):

    goToContact(name)

    numUnreadString = str((-1) * (numUnread - 1)) if numUnread > 1 else ""
    if fromLeft:
        print("Taking message from left...")
        x_arg = '(//div[@class="tSmQ1"]/div[contains(@class, "in")]/div/div/div/div)[last()' + (str(-1 * beginningIndex) if beginningIndex else "") + ']'
    else:
        print("Taking from right...")
        x_arg = '(//div[@class="tSmQ1"]/div[contains(@class, "out")]/div/div/div/div)[last()' + (str(-1 * beginningIndex) if beginningIndex else "") + ']'
    print("forward x_arg: " + x_arg)

    while True:
        action = ActionChains(driver)
        action.move_to_element(driver.find_element_by_xpath(x_arg)).perform()
        
        sleep(0.25)

        driver.find_element_by_xpath('//div[@data-js-context-icon="true"]').click()
        sleep(0.25)
    
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

    checkboxCSSSelector = "div.message-" + ("in" if fromLeft else "out") + ".focusable-list-item"
    checkbox = [element.find_element_by_xpath(".//*[@class='_2K7JO']") for element in driver.find_elements_by_css_selector(checkboxCSSSelector)]

    for i in range(numUnread - 1):
        num = -1 * (i + 2) - beginningIndex
        try: checkbox[num].click()
        except: break
    
    try: driver.find_element_by_xpath('//button[@title="Forward messages"]').click()
    except:  driver.find_element_by_xpath('//button[@title="Forward message"]').click()
    input_box = driver.find_element_by_xpath('//div[@contenteditable="true"][1]')
    for number in numbers:
        number = salesDict[number] if number in salesDict else number
        input_box.clear()
        input_box.send_keys(number)
        sleep(0.5)
        input_box.send_keys(Keys.RETURN)
        sleep(0.4)
    driver.find_element_by_xpath('//div[@class="_3FwbN"]/div/div').click()
    sleep(1)

# Records a message in the MongoDB cluster
def recordMessage(name, messageBlock):
    current = datetime.datetime.now()

    message = {
        "from": name,
        "to": messageBlock.repliedTo,
        "replyingToMessage": messageBlock.repliedMessage,
        "state": messageBlock.state,
        "content": messageBlock.text,
        "hour": messageBlock.hour,
        "minute": messageBlock.minute,
        "day": current.day,
        "month": current.month,
        "year": current.year
    }
    
    print(message)
    if not messageInDatabase(name, messageBlock): 
        collection.insert_one(message)
        print("entry recorded.\n")
    else:
        print("message already exists.\n")

# Finds a message in database
def messageInDatabase(name, messageBlock):
    message = {
        "from": name,
        "to": messageBlock.repliedTo,
        "replyingToMessage": messageBlock.repliedMessage,
        "state": messageBlock.state,
        "content": messageBlock.text,
        "hour": messageBlock.hour,
        "minute": messageBlock.minute
    }

    print(collection.count_documents(message))
    return bool(collection.count_documents(message))

# Gets all message blocks from a chat
def getAllMessagesBlocks(name, blocks):
    result = []
    goToContact(name)

    try: WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,"//footer//*[@contenteditable='true']")))
    except: return

    input_box = driver.find_element_by_xpath("//footer//*[@contenteditable='true']")
    current_element = input_box
    for i in range(blocks):
        if not i: current_element.send_keys(Keys.TAB)
        else: current_element.send_keys(Keys.ARROW_UP)
        current_element = driver.switch_to_active_element()
        result.append(MessagesBlock(name, current_element))
    
    return result

# Gets all name blocks, based on how many blocks are checked
def getAllNameBlocks(blocks):
    nameSelector = driver.find_element_by_xpath("//*[@contenteditable='true']")
    nameSelector.click()

    nameBlocks = {}
    next_element = nameSelector
    for _ in range(blocks):
        next_element.send_keys(Keys.ARROW_DOWN)
        next_element = driver.switch_to_active_element()

        try: nameBlock = NameBlock(next_element)
        except NoSuchElementException: continue
        
        # Ignore these contacts
        if any(i in nameBlock.name.lower() for i in IGNORE_LIST): continue

        nameBlocks[nameBlock.name] = nameBlock
    return nameBlocks

# Gets all unread name blocks, based on how many blocks that are checked
def getAllUnreadNameBlocks(blocks):
    nameSelector = driver.find_element_by_xpath("//*[@contenteditable='true']")
    nameSelector.click()

    nameBlocks = {}
    next_element = nameSelector
    for _ in range(blocks):
        next_element.send_keys(Keys.ARROW_DOWN)
        next_element = driver.switch_to_active_element()

        try: nameBlock = NameBlock(next_element)
        except NoSuchElementException: continue
        
        # Ignore these contacts
        if any(i in nameBlock.name.lower() for i in IGNORE_LIST): continue

        if nameBlock.unread:
            nameBlocks[nameBlock.name] = nameBlock
            print(nameBlock.name)
    return nameBlocks

# Go to unsaved contact (through the search phone number button)
def goToContact(number):
    nameSelector = driver.find_element_by_xpath("//*[@contenteditable='true']")
    nameSelector.send_keys(number)
    sleep(1)
    nameSelector.send_keys(Keys.ENTER)

# Converts 12-hour time to 24-hour time
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

# Sets up the driver for use
def setupDriver():

    options = Options()
    options.add_argument("--chrome_driver_path='C:/bin/chromedriver.exe'") # Change accordingly
    options.add_argument("--user-data-dir=./User_Data_" + DATADIR)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3641.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com")

    # Wait until WhatsApp loads
    try:
        WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.CLASS_NAME, "_1MZWu")))
    except:
        print("Unable to login.")
        exit()
    
    return driver

# Sets up the MongoDB collection for use
def setupMongoDB():
    cluster = MongoClient('mongodb+srv://admin:Test2000%40%40%40%40@waauto.oivp5.mongodb.net/waAuto?retryWrites=true&w=majority')
    db = cluster['waAuto']
    collection = db['messages']
    return collection

# Sets up the contacts
def setupContacts(salesNamesFile, salesNumbersFile, contactsExcelFile):

    fileReader = FileReader
    preliminarySalesNames = fileReader.readTxt(salesNamesFile)
    preliminarySalesNumbers = fileReader.readTxt(salesNumbersFile)
    contactNames = fileReader.readExcel(contactsExcelFile, 'A')
    contactNumbers = fileReader.readExcel(contactsExcelFile, 'B')

    contacts = {}
    for index, i in enumerate(contactNames):
        contactNames[index] = i.replace(" ", "")
        contacts[i] = contactNumbers[index]

    salesDict = {}
    for index, i in enumerate(preliminarySalesNames):
        salesDict[i] = preliminarySalesNumbers[index]

    salesNames = [preliminarySalesNames[x: x + 5] for x in range(0, len(preliminarySalesNames), 5)]
    salesNumbers = [preliminarySalesNumbers[x: x + 5] for x in range(0, len(preliminarySalesNumbers), 5)]

    print(salesNames)
    print(salesNumbers)
    print(salesDict)
    print(contactNames)
    print(contactNumbers)
    print(contacts)

    return salesNames, salesNumbers, contacts, salesDict

if __name__ == "__main__":
    main()