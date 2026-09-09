n = int(input("Enter number: "))

original = n
total = 0
digits = len(str(n))

while n > 0:
    digit = n % 10
    total += digit ** digits
    n //= 10

if total == original:
    print("Armstrong Number")
else:
    print("Not Armstrong")
