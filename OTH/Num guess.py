import random

number = random.randint(1, 100)
attempts = 0

print("🎯 Number Guessing Game")
print("I have selected a number between 1 and 100.")

while True:
    guess = int(input("Enter your guess: "))
    attempts += 1

    if guess < number:
        print("Too low! Try again.")
    elif guess > number:
        print("Too high! Try again.")
    else:
        print("\n🎉 Correct!")
        print("The number was:", number)
        print("You found it in", attempts, "attempts.")
        break
