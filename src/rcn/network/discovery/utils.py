
import pandas as pd


def CSV2List(file):
    df = pd.read_csv(file)
    return df.to_dict("records")

def File2List(file):
    mylist = []
    file1 = open(file, 'r')
    Lines = file1.readlines()
    for line in Lines:
      mylist.append(line.strip())
    return mylist