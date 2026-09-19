n = int(input("Enter number: "))

while n >= 10:
    s = 0
    while n > 0:
        s += n % 10
        n //= 10
    n = s

print("Digital Root =", n)
