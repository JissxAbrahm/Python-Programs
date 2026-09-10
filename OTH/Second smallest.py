a = [25, 10, 45, 5, 30]

small = a[0]
second = None

for x in a:
    if x < small:
        second = small
        small = x
    elif x != small and (second is None or x < second):
        second = x

print("Second smallest:", second)
