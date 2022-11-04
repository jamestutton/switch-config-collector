def File2List(file):
    mylist = []
    file1 = open(file, 'r')
    Lines = file1.readlines()
    for line in Lines:
      mylist.append(line.strip())
    return mylist