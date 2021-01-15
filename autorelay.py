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

# TODO Implement handling of deleted messages
# TODO Implement downloading of images / videos / files on forward

CURRENT_NUMBER = "+62 812-9749-9150" # Insert your number here
DATADIR = "test" # To indicate which datadir WhatsApp uses
IGNORE_LIST = ["tpyramid", "uea", "universe", "papa"] + [CURRENT_NUMBER] # Contacts to ignore

INTERVAL = 7 # Seconds per cycle
WAIT = 300 # Wait for elements to show
NAME_BLOCKS_TO_SCAN = 10 # How many name blocks to scan per loop
MESSAGE_BLOCKS_TO_SCAN = 30 # How many message blocks to scan per chat
MESSAGE_LENGTH_LIMIT = 500 # TODO (Not implemented) How many characters to limit when entering message in database

# File Reader object
class FileReader:

    # Reads lines from a .txt file
    def read_txt(filename):
        results = []
        with open(filename, "r") as f:
            data = f.read().splitlines()
            for line in data:
                results.append(line)
        return results
    
    # Reads lines from an excel worksheet, from the specified column
    def read_excel(filename, column):
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

    # If there are no unread messages somehow, continue to the next unread chat

    def __init__(self, element):
        # The current element
        self.element = element

        # A name block (chat on the left) always has a name and time.
        self.name = self.element.find_element_by_xpath(".//*[contains(@class, '1hI5g')]").text
        self.time = self.element.find_element_by_xpath(".//*[contains(@class, '_2gsiG')]").text
        
        # Unread bubble may exist, if not then there are no unread messages.
        self.unread_bubble = self.element.find_elements_by_xpath(".//*[contains(@class, 'VOr2j')]")
        self.unread = True if len(self.unread_bubble) > 0 else False
        if self.unread: self.num_unread_messages = (int(self.unread_bubble[0].text) if self.unread_bubble[0].text != "" else 2)
        else: self.num_unread_messages = 0

# Message Block object
class MessagesBlock:

    name = None
    element = None
    time = None
    hour = None
    minute = None
    state = None
    text = None
    replied_message = None
    replied_to = None
    

    def __init__(self, name, element):
        self.name = name
        self.element = element

        # To check if the message block is indeed a message
        self.time_elements = element.find_elements_by_xpath('.//*[contains(@class, "_2JNr-")]')

        # If it is indeed a message block (it will have a time element)
        if len(self.time_elements):
            self.time = twelveToTwentyfour(self.time_elements[0].text)
            self.hour = int(self.time[:2])
            self.minute = int(self.time[3:])

            # Check if message is incoming or outgoing
            self.state = "incoming" if len(driver.find_elements_by_xpath('//*[contains(@class,"in")][@tabindex="0"]')) else "outgoing"

            # Check if the message has text
            self.text_exists = True if len(element.find_elements_by_xpath('.//*[contains(@class, "_1wlJG")]')) else False
            self.text = element.find_element_by_xpath('.//*[contains(@class, "_1wlJG")]').text if self.text_exists else "Image/Video/File"

            # Check if the message was a reply to another, and set that to self.replied_message
            self.replied_message_exists = True if len(element.find_elements_by_xpath('.//*[contains(@class, "i8New")]')) else False
            self.replied_message_is_text = True if len(element.find_elements_by_xpath('.//*[contains(@class, "_1Dook")]')) else False
            
            if self.replied_message_exists: 
                self.replied_message = element.find_element_by_xpath('.//*[contains(@class, "i8New")]').text if self.replied_message_is_text else "Image/Video/File"
                pattern = re.compile(r"\[(?:.*to|from) (.*)\]")
                try:
                    self.replied_to = pattern.match(''.join(self.replied_message.split('\n')[1:])).group(1)
                except:
                    self.replied_to = self.replied_message.split('\n')[0]

            else: 
                self.replied_message = None
                self.replied_to = None

    def print_message(self):
        print("name: " + self.name)
        print("time: " + self.time)
        print("text: " + self.text)
        print("state: " + self.state)
        if self.replied_message: print("replied_message: " + self.replied_message)
        if self.replied_to: print("Replied to: " + self.replied_to)
        print()


# Main function
def main():

    if len(sys.argv) == 1: sys.exit("Please enter arguments")

    # Setup driver and contacts
    global driver, collection, sales_names, contacts, sales_dict
    driver = setup_driver()
    collection = setup_MongoDB()
    sales_names, sales_numbers, contacts, sales_dict = setup_contacts(sys.argv[1], sys.argv[2], sys.argv[3])
    
    # Start program (wait for blue double tick before starting)
    send_message(CURRENT_NUMBER, "starting")

    # How many messages to search through in the first loop (after the program starts,
    # there maybe tons of messages buried under other chats, so this searches a number
    # of chats down, based on a user-defined amount of chats to search through)
    try: first_loop_messages = int(input("Enter how many messages to get on first loop (also starts the program): "))
    except: first_loop_messages = NAME_BLOCKS_TO_SCAN
    first_loop = True
    
    # Sets up the program-stored variables for unread messages, and those to remove which will
    # be popped from the dict by the next iteration
    unread_name_blocks = {}
    names_to_remove = []

    # Loop to keep program on
    while True:
        try:
            # Removes the names to remove from the unread_name_blocks dict
            for i in names_to_remove: unread_name_blocks.pop(i)
            names_to_remove = []
            
            # Go to the number of the current whatsapp profile, on standby waiting for other
            # messages without reading them and erasing their unread bubble
            go_to_contact(CURRENT_NUMBER)
            if not first_loop: sleep(INTERVAL)

            # Get a large number of unread name blocks at first loop (perhaps after the program 
            # has not been running)
            new_unread_name_blocks = get_all_unread_name_blocks(NAME_BLOCKS_TO_SCAN) if not first_loop else get_all_unread_name_blocks(first_loop_messages)
            unread_name_blocks.update(new_unread_name_blocks)
            first_loop = False

            # If no unread bubble detected, search through a few of the top chats, to detect
            # if a message has been manually sent out by the person holding the hub phone
            if len(unread_name_blocks) == 0:

                # Gets the name blocks to scan for these manual messages
                name_blocks = get_all_name_blocks(NAME_BLOCKS_TO_SCAN) if first_loop else get_all_name_blocks(3)
                
                # Does not detect messages to a sales team member (as these are not
                # to be forwarded)
                name_blocks = [i for i in name_blocks if not any(i in j for j in sales_names)]

                # Starts iterating through the name blocks
                for name in name_blocks:

                    # Detects for unread messages within that chat (comparing the messages to the 
                    # MongoDB database to detect messages that are not already on the database, which
                    # means that those are unread))
                    unread_messages = []

                    # Detects 10 messages as this is a reasonable maximum number of messages that
                    # one would manually send to a customer
                    for message_block in get_all_messages_block(name, 10):
                        # On the first loop, simply just record all the messages it finds
                        if first_loop: record_message(name, message_block)
                        # If the detected messages are not in the database, add to unread_messages
                        if not message_in_database(name, message_block): unread_messages.append(message_block)
                    
                    # How many incoming and outgoing messages for this current chat
                    num_incoming = len([i for i in unread_messages if i.state == 'incoming'])
                    num_outgoing = len(unread_messages) - num_incoming
                    # Forward the messages accordingly
                    if num_incoming: forward_program_detected(name, num_incoming, True, sales_names)
                    if num_outgoing: forward_program_detected(name, num_outgoing, False, sales_names)

                continue

            # If an unread bubble detected, iterate over the unread_name_blocks dict to forward
            # the unread messages
            for name, nameBlock in unread_name_blocks.items():

                names_to_remove.append(name)

                # Get number of unread messages
                num_unread = nameBlock.num_unread_messages

                # If there are no unread messages somehow, continue to the next unread chat
                if not num_unread: continue

                if any(name in i for i in sales_names): # If incoming name found in salesList
                    forward_sales(name, num_unread, True, sales_names)
                else:
                    forward_customer(name, num_unread, True, sales_names)
                    
        except (KeyboardInterrupt, SystemExit):
            raise 
        except Exception as e:
            raise
            print(e)
            continue

    
    driver.close()

# Send a message by typing
def send_message(name, message):
    go_to_contact(name)
    
    # Wait for input box at the bottom
    try: WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,"//footer//*[@contenteditable='true']")))
    except: return

    # Locate the input box, and send the message
    input_box = driver.find_element_by_xpath("//footer//*[@contenteditable='true']")
    input_box.send_keys(message)
    input_box.send_keys(Keys.RETURN)

    # Give the program some time to cool down as there are 
    # animations played after sending a message
    sleep(1) 

# Forward messages from sales team
def forward_sales(name, num_unread, fromLeft, numberSet):

    # TODO NOT COMPLETE
    # Using reversed indexes, so the earliest message sent is the one handled first
    for index in reversed(range(num_unread)):

        go_to_contact(name)

        # Check if sales team replied properly - if they do, there will be a "button" on
        # top of their reply that can be clicked to navigate to what was replied to
        replied_x_arg = '(//*[contains(@class,"in")][last()' + (str(-1 * (index)) if index != 0 else "") + '])//div[contains(@class, "i8New")]'
        
        # Get the button elements found by the xpath above
        replied = driver.find_elements_by_xpath(replied_x_arg)

        # If sales team did not reply properly, i.e. no button detected, they will be prompted
        # to reply properly.
        if len(replied) == 0:
            send_message(name, "Message not sent. Please reply to a message!")
            return
        
        # Get the last element found by the xpath
        replied[-1].click()

        # Asynchronous wait
        sleep(2)

        # Get the messages on the right side of the screen, so the program can crawl up and down
        # those messages to find the exact message being replied to (it will be highlighted for 
        # a short while and have a tabindex of 0 when the original button is clicked)
        messages = driver.find_elements_by_xpath('//div[contains(@data-id,"true")]')

        # Find the replied to message
        i = -1
        reply_text = ""
        reply_to_who = ""

        # Crawl up the messages trying to locate the chatbox referred to
        for _ in range(len(messages)):

            # Try to locate the chatbox that has a different color (meaning it was the 
            # one that was highlighted when original button is clicked)
            x_arg = '//div[contains(@data-id,"true")][@tabindex="0"][last()' + (str(i + 1) if i != -1 else "") + ']'
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH,x_arg)))
            reply_item = driver.find_elements_by_xpath(x_arg)

            # When located
            if len(reply_item) != 0:

                # If reply was in the corract format (will match the regex)
                try:
                    pattern = re.compile(r"\[(?:.*to|from) (.*)\]")
                    reply_to_who = pattern.match(reply_item[0].find_element_by_xpath('.//*[contains(@class,"_1wlJG")]').text).group(1)
                except: 
                    send_message(name, "Message not sent. Please reply to the from message!")
                    return
                break
            i -= 1

        # TODO Implement replied text to MongoDB database post
        print(reply_text := messages[i + 1].find_element_by_xpath('.//*[contains(@class,"_1wlJG")]').text)
    
        # To reset mysterious WhatsApp message targeting bug (explanation: WhatsApp targets
        # these messages in a weird fashion. An index of 0 - supposed to be the last message, targets
        # the element correctly (so [last()] on the xpath will actually get the last element), 
        # and no problems there. However, [last() - 1], supposed to get the second last element,
        # actually still gets the last element. This is the same for [last() - 2], etc..
        # So, we have to adjust the index in the forward_message function, and we adjust the 0 
        # index such that it beomes -1)
        if index == 0: index -= 1

        # Prepare to forward the message to the sales team and customer
        recipient_message = "[from " + name + " to " + reply_to_who + "]"
        recipient_message += "---" + contacts[reply_to_who] + "---" if reply_to_who in contacts else ""
        recipient_message += " Replying to:"
        
        # Send the preparation message to hub phone to prepare forwarding
        send_message(CURRENT_NUMBER, recipient_message)

        # Forward to sales team first
        for numbers in numberSet:
            # Forward the preparation message ([from ...])
            forward_message(CURRENT_NUMBER, 1, 0, False, numbers, record=False)

            # Try to get what message was replied to
            try: forward_message(reply_to_who, 1, 0, True, numbers, record=False)
            except:
                send_message(CURRENT_NUMBER, "*Couldn't find replied to message.*")
                forward_message(CURRENT_NUMBER, 1, 0, False, numbers, record=False)
            
            # Forward the actual message (adjusted the beginning index due to mystery 
            # described above)
            forward_message(name, 1, index + 1, fromLeft, numbers, record=False)

        # Forward to the customer (again, with adjusted beginning index)
        forward_message(name, 1, index + 1, fromLeft, [reply_to_who], record=True)
        
# Forward messages from customer
def forward_customer(name, num_unread, fromLeft, numberSet):
    
    # Prepare to forward the messages to the sales team
    recipient_message = "[from " + name + "]"
    recipient_message += "---" + contacts[name] + "---" if name in contacts else ""

    # Send the preparation message to hub phone to prepare forwarding
    send_message(CURRENT_NUMBER, recipient_message)
    for numbers in numberSet:
        # Forward preparation message
        forward_message(CURRENT_NUMBER, 1, 0, False, numbers, record=False)
        # Forward to sales team
        forward_message(name, num_unread, 0, fromLeft, numbers, record=True)
       
# Forward messages to customer, manually sent from the hub phone
def forward_program_detected(name, num_unread, fromLeft, numberSet):
    
    # If it is an incoming message, treat as normal
    if fromLeft:
        if any(name in i for i in sales_names): # If incoming name found in salesList
            forward_sales(name, num_unread, True, numberSet)
        else:
            forward_customer(name, num_unread, True, numberSet)

    # If it is an outgoing message, we need to first prepare the forwarding
    elif not any(name in i for i in sales_names) :

        # Prepare preparation message before forwarding
        recipient_message = "[from Program to " + name + "]"
        recipient_message += "---" + contacts[name] + "---" if name in contacts else ""

        # Send the preparation message to hub phone to perpare forwarding
        send_message(CURRENT_NUMBER, recipient_message)
        for numbers in numberSet:
            # Forward preparation message
            forward_message(CURRENT_NUMBER, 1, 0, False, numbers, record=False)
            # Forward to sales team
            forward_message(name, num_unread, 0, False, numbers, record=True)

# Main function for forwarding messages
def forward_message(name, num_unread, beginningIndex, fromLeft, numbers, record):

    go_to_contact(name)

    # If we record the messages
    if record:
        for message_block in get_all_messages_block(name, 10): record_message(name, message_block)

    # If message is incoming
    if fromLeft:
        print("Taking message from left...")
        x_arg = '(//div[@class="tSmQ1"]/div[contains(@class, "in")]/div/div/div/div)[last()' + (str(-1 * beginningIndex) if beginningIndex else "") + ']'
    
    else:
        print("Taking message from right...")
        x_arg = '(//div[@class="tSmQ1"]/div[contains(@class, "out")]/div/div/div/div)[last()' + (str(-1 * beginningIndex) if beginningIndex else "") + ']'
    print("forward x_arg: " + x_arg) # debug

    # Keep trying to forward the message by moving the mouse over the message,
    # finding the top-right arrow, and clicking it and then pressing "Forward message"
    while True:
        action = ActionChains(driver)
        action.move_to_element(driver.find_element_by_xpath(x_arg)).perform()
        
        sleep(0.25)
        # Find the top-right arrow and click it
        driver.find_element_by_xpath('//div[@data-js-context-icon="true"]').click()
        sleep(0.25)
    
        try:
            # If the message is an album
            driver.find_element_by_xpath('//*[@title="Forward all"]').click()
        except:
            try:
                # If click successful, break
                driver.find_element_by_xpath('//*[@title="Forward message"]').click()
                break
            except:
                # For document that cannot be forwarded yet, it must be an image / video / file that
                # first needs to be downloaded. This clicks on the image / video / file and allows
                # it to download first before forwarding it
                videos = driver.find_elements_by_xpath('//*[contains(@class,"_3i3h7")]')
                
                # Wait for the video to be available for forwarding
                if len(videos):
                    videos[-1].click()
                    forward_x_path = '//div[contains(@title, "Forward")]'
                    # When loaded up, exit out of the video window and continue forwarding process
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,forward_x_path)))
                    driver.find_element_by_xpath('//div[@title="Close"]').click()
                continue

    # Gets the checkboxes to forward multiple messages
    checkbox_css_selector = "div.message-" + ("in" if fromLeft else "out") + ".focusable-list-item"
    checkbox = [element.find_element_by_xpath(".//*[@class='_2K7JO']") for element in driver.find_elements_by_css_selector(checkbox_css_selector)]

    # Clicks up and up depending on the number of messages there are to be forwarded
    for i in range(num_unread - 1):
        num = -1 * (i + 2) - beginningIndex
        try: checkbox[num].click()
        except: break
    
    # If multiple messages
    try: driver.find_element_by_xpath('//button[@title="Forward messages"]').click()
    # If single message
    except:  driver.find_element_by_xpath('//button[@title="Forward message"]').click()

    # Start inputting the numbers to be forwarded to, asynchronous sleeps are to account
    # for the animation that whatsapp plays when selecting contacts for forwarding
    input_box = driver.find_element_by_xpath('//div[@contenteditable="true"][1]')
    for number in numbers:
        # number = sales_dict[number] if number in sales_dict else number
        input_box.clear()
        input_box.send_keys(number)
        sleep(0.5)
        input_box.send_keys(Keys.RETURN)
        sleep(0.4)

    # Forward messages. asynchronous sleep again to account for animation.
    driver.find_element_by_xpath('//div[@class="_3FwbN"]/div/div').click()
    sleep(1)

# Records a message in the MongoDB cluster
def record_message(name, message_block):
    # Gets current time ONLY for date (time is deduced from message block) as there
    # is no way to determine message date from whatsapp alone
    current = datetime.datetime.now()

    # BSON object for document posting on MongoDB
    message = {
        "from": name,
        "to": message_block.replied_to,
        "replyingToMessage": message_block.replied_message,
        "state": message_block.state,
        "content": message_block.text,
        "hour": message_block.hour,
        "minute": message_block.minute,
        "day": current.day,
        "month": current.month,
        "year": current.year
    }
    
    # Debug
    print(message)
    if not message_in_database(name, message_block): 
        collection.insert_one(message)
        print("entry recorded.\n")
    else:
        print("message already exists.\n")

# Finds a message in database
def message_in_database(name, message_block):

    # BSON object to query
    message = {
        "from": name,
        "to": message_block.replied_to,
        "replyingToMessage": message_block.replied_message,
        "state": message_block.state,
        "content": message_block.text,
        "hour": message_block.hour,
        "minute": message_block.minute
    }

    # If the message exists in the database, return True
    return bool(collection.count_documents(message))

# Gets all message blocks from a chat
def get_all_messages_block(name, blocks):
    result = []
    go_to_contact(name)

    # Wait for the input box at the bottom of the page
    try: WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.XPATH,"//footer//*[@contenteditable='true']")))
    except: return

    # Crawl up by simulating kepresses of the up button to get the message blocks
    input_box = driver.find_element_by_xpath("//footer//*[@contenteditable='true']")
    current_element = input_box
    for i in range(blocks):
        if not i: current_element.send_keys(Keys.TAB)
        else: current_element.send_keys(Keys.ARROW_UP)
        current_element = driver.switch_to_active_element()
        result.append(MessagesBlock(name, current_element))
    
    return result

# Gets all name blocks, based on how many blocks are checked
def get_all_name_blocks(blocks):
    
    # Start by setting the active element to the search contacts button on the top let
    name_selector = driver.find_element_by_xpath("//*[@contenteditable='true']")
    name_selector.click()

    # Get the name blocks by simulating keypresses of the down button
    name_blocks = {}
    next_element = name_selector
    for _ in range(blocks):
        next_element.send_keys(Keys.ARROW_DOWN)
        next_element = driver.switch_to_active_element()

        try: nameBlock = NameBlock(next_element)
        except NoSuchElementException: continue
        
        # Ignore these contacts
        if any(i in nameBlock.name.lower() for i in IGNORE_LIST): continue

        name_blocks[nameBlock.name] = nameBlock
    return name_blocks

# Gets all unread name blocks, based on how many blocks that are, similar to get_all_name_blocks
def get_all_unread_name_blocks(blocks):
    name_selector = driver.find_element_by_xpath("//*[@contenteditable='true']")
    name_selector.click()

    name_blocks = {}
    next_element = name_selector
    for _ in range(blocks):
        next_element.send_keys(Keys.ARROW_DOWN)
        next_element = driver.switch_to_active_element()

        try: nameBlock = NameBlock(next_element)
        except NoSuchElementException: continue
        
        # Ignore these contacts
        if any(i in nameBlock.name.lower() for i in IGNORE_LIST): continue

        if nameBlock.unread:
            name_blocks[nameBlock.name] = nameBlock
            print(nameBlock.name)
    return name_blocks

# Go to unsaved contact (through the search phone number button)
def go_to_contact(number):
    name_selector = driver.find_element_by_xpath("//*[@contenteditable='true']")
    name_selector.send_keys(number)
    sleep(1)
    name_selector.send_keys(Keys.ENTER)

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
def setup_driver():

    # Default options to start chromedriver
    options = Options()
    options.add_argument("--chrome_driver_path='C:/bin/chromedriver.exe'") # Change accordingly
    options.add_argument("--user-data-dir=./User_Data_" + DATADIR)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3641.0 Safari/537.36")

    # Start the driver
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
def setup_MongoDB():
    cluster = MongoClient('mongodb+srv://admin:Test2000%40%40%40%40@waauto.oivp5.mongodb.net/waAuto?retryWrites=true&w=majority')
    db = cluster['waAuto']
    collection = db['messages']
    return collection

# Sets up the contacts
def setup_contacts(sales_names_file, sales_numbers_file, contacts_excel_file):

    file_reader = FileReader
    preliminary_sales_names = file_reader.read_txt(sales_names_file)
    preliminary_sales_numbers = file_reader.read_txt(sales_numbers_file)
    contact_names = file_reader.read_excel(contacts_excel_file, 'A')
    contact_numbers = file_reader.read_excel(contacts_excel_file, 'B')

    contacts = {}
    for index, i in enumerate(contact_names):
        contact_names[index] = i.replace(" ", "")
        contacts[i] = contact_numbers[index]

    sales_dict = {}
    for index, i in enumerate(preliminary_sales_names):
        sales_dict[i] = preliminary_sales_numbers[index]

    # Split the sales team into subgroups of 5, because of WhatsApp's forwarding limit
    sales_names = [preliminary_sales_names[x: x + 5] for x in range(0, len(preliminary_sales_names), 5)]
    sales_numbers = [preliminary_sales_numbers[x: x + 5] for x in range(0, len(preliminary_sales_numbers), 5)]

    # DEBUG
    print(sales_names)
    print(sales_numbers)
    print(sales_dict)
    print(contact_names)
    print(contact_numbers)
    print(contacts)

    return sales_names, sales_numbers, contacts, sales_dict

if __name__ == "__main__":
    main()