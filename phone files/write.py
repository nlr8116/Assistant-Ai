import sys 
with open("inbox.txt", "w") as f:
    f.write(sys.argv[1])  
