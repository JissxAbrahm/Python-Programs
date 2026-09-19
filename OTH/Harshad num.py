n = int(input("Enter number: "))

temp = n
s = 0

while temp > 0:
    s += temp % 10
    temp //= 10

if n % s == 0:
    print("Harshad Number")
else:
    print("Not a Harshad Number")
