def get_input_as_bool(prompt, error_on_bad_input=False):
    positive = {"yes", "y", "true", "1"}
    negative = {"no", "n", "false", "0"}

    while True:
        answer = input(prompt).strip().lower()
        if answer in positive:
            return True
        if answer in negative:
            return False
        if error_on_bad_input:
            raise ValueError("Input must be yes, y, true, no, n, or false")
        print("Please answer yes or no (y/n).")

def get_input_as_int(prompt):
    while True:
        s = input(prompt).strip()
        try:
            return int(s)
        except ValueError:
            print("Please enter an integer (e.g. 2).")

def get_input_as_float(prompt):
    while True:
        s = input(prompt).strip()
        try:
            return float(s)
        except ValueError:
            print("Please enter a number (e.g. 50 or -25).")
