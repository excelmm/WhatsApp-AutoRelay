import openpyxl as excel

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