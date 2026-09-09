text = input("Enter sentence: ")

words = text.split()

longest = max(words, key=len)

print("Longest word =", longest)
