class MessagesBlock:

    def __init__(self, name, element):
        self.name = name
        self.element = element
    
    def getMessages(self, fromLeft):
        if fromLeft: return [i.text for i in self.element.find_elements_by_xpath \
            (".//*[contains(@class, 'message-in')]//*[contains(@class, '_1VzZY')]")]
        else: return [i.text for i in self.element.find_elements_by_xpath \
            (".//*[contains(@class, 'message-out')]//*[contains(@class, '_1VzZY')]")]
