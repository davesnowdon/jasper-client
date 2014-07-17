import re


WORDS = ["POD", "BAY", "DOORS"]


def handle(text, mic, profile):
    """
        Reports the current time based on the user's timezone.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    name = "Dave"
    mic.say("I'm sorry %s I cannot do that" % name)


def isValid(text):
    """
        Returns True if input contains pod bay doors.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\bpod bay doors\b', text, re.IGNORECASE))
