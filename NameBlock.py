class NameBlock:

    def __init__(self, element):
        self.element = element
        self.name = self.element.find_element_by_xpath(".//*[contains(@class, '1hI5g')]").text
        self.time = self.element.find_element_by_xpath(".//*[contains(@class, '_2gsiG')]").text
        self.unreadBubble = self.element.find_elements_by_xpath(".//*[contains(@class, 'VOr2j')]")
        self.unread = True if len(self.unreadBubble) > 0 else False
        if self.unread: self.numUnreadMessages = (int(self.unreadBubble[0].text) if self.unreadBubble[0].text != "" else 2)
        else: self.numUnreadMessages = 0