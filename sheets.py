import pickle
import gspread
from google.auth.transport.requests import Request

SPREADSHEET_ID = "1fH37JBWykDAlYVu2rfzJc9MxIqmjI_74K7mM1LBgxE4"

def get_sheet():
    with open("token.pickle", "rb") as token:
        creds = pickle.load(token)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    gc = gspread.authorize(creds)

    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet("Notices")

    return worksheet