a = list(map(int, input("Enter numbers: ").split()))

n = len(a) + 1

total = n * (n + 1) // 2
actual = sum(a)

print("Missing number:", total - actual)
