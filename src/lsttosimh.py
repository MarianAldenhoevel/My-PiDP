import sys

print("""SET CPU 11/70,4M
;SET REALCONS=localhost
;SET REALCONS panel=11/70
;SET REALCONS interval=8
;SET REALCONS connected

""")

for line in sys.stdin:
    print('; ' + line, end='')
    
    lineno = line[:9]
    data = line[9:40].replace("'", '')
    code = line[40:]

    data = data.split()
    if data:
        addr = int(data[0], 8)  
        data = data[1:]
        for d in data:
            print('D ' + oct(addr)[2:] + ' ' + d)
            addr += 2
    
print("""

RESET ALL
SET CPU IDLE
D PSW 000340
D PC  000000
E PC
echo "RUN to start from PC"
""")