text = input("Enter string: ")

result = ""

for ch in text:
    if ch.lower() not in "aeiou":
        result += ch

print(result)
